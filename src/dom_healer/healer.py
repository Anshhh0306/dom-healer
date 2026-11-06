"""High-level API: capture fingerprints, locate them in a new DOM, and repair broken selectors."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

from dom_healer.dom import Document, DomHealerError, Element, SelectorError, ensure_document
from dom_healer.features import feature_matrix
from dom_healer.fingerprint import ElementFingerprint
from dom_healer.index import PageIndex
from dom_healer.rankers import Ranker, get_ranker
from dom_healer.synthesis import SelectorSuggestion, suggest_selectors

DEFAULT_MAX_CANDIDATES = 32
DEFAULT_MIN_CONFIDENCE = 0.5

STATUS_VALID = "valid"  # the original selector still finds the best-matching element
STATUS_HEALED = "healed"  # selector broke; a confident replacement was found
STATUS_LOW_CONFIDENCE = "low_confidence"  # best guess returned, but below the confidence threshold
STATUS_NOT_FOUND = "not_found"  # no candidate element at all


class ElementNotFoundError(DomHealerError, LookupError):
    """The selector used to capture a fingerprint matched nothing."""


def get_index(doc: Document) -> PageIndex:
    """Return the (cached) :class:`PageIndex` of ``doc``.

    The index is built on first use; do not mutate the tree afterwards.
    """
    index = doc._index
    if index is None:
        index = doc._index = PageIndex(doc)
    return index


def _ms(start: float) -> float:
    return (time.perf_counter() - start) * 1000.0


@dataclass
class Candidate:
    """A scored candidate element in the new document."""

    element: Element
    score: float
    rank: int
    fingerprint: ElementFingerprint
    document: Document = field(repr=False)
    _selectors: SelectorSuggestion | None = field(default=None, repr=False)

    @property
    def selectors(self) -> SelectorSuggestion:
        if self._selectors is None:
            self._selectors = suggest_selectors(self.document, self.element)
        return self._selectors

    @property
    def css(self) -> str:
        return self.selectors.css

    @property
    def xpath(self) -> str:
        return self.selectors.xpath

    def to_dict(self, with_selectors: bool = True) -> dict[str, Any]:
        out: dict[str, Any] = {
            "rank": self.rank,
            "score": round(float(self.score), 4),
            "tag": self.element.tag,
            "summary": self.fingerprint.summary(),
            "absolute_xpath": self.document.absolute_xpath(self.element),
        }
        if with_selectors:
            out.update(self.selectors.to_dict())
        return out


@dataclass
class HealResult:
    """Outcome of locating a fingerprint (and optionally repairing a selector) in a document."""

    status: str
    fingerprint: ElementFingerprint
    candidates: list[Candidate]
    original_selector: str | None = None
    selector: str | None = None
    xpath: str | None = None
    strategy: str = ""
    confidence: float = 0.0
    margin: float = 0.0
    ranker: str = ""
    original_matches: int = 0
    timings_ms: dict[str, float] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        """True when the element was found confidently (status ``valid`` or ``healed``)."""
        return self.status in (STATUS_VALID, STATUS_HEALED)

    @property
    def best(self) -> Candidate | None:
        return self.candidates[0] if self.candidates else None

    @property
    def element(self) -> Element | None:
        return self.candidates[0].element if self.candidates else None

    def to_dict(self, top_k: int | None = None, with_fingerprint: bool = False) -> dict[str, Any]:
        cands = self.candidates if top_k is None else self.candidates[:top_k]
        out: dict[str, Any] = {
            "status": self.status,
            "ok": self.ok,
            "original_selector": self.original_selector,
            "original_matches": self.original_matches,
            "selector": self.selector,
            "xpath": self.xpath,
            "strategy": self.strategy,
            "confidence": round(float(self.confidence), 4),
            "margin": round(float(self.margin), 4),
            "ranker": self.ranker,
            "target": self.fingerprint.summary(),
            "candidates": [c.to_dict() for c in cands],
            "timings_ms": {k: round(v, 3) for k, v in self.timings_ms.items()},
        }
        if with_fingerprint:
            out["fingerprint"] = self.fingerprint.to_dict()
        return out


class Healer:
    """Locate fingerprinted elements in one document.

    Build a ``Healer`` once per page (it indexes the document) and call
    :meth:`locate` / :meth:`repair` for as many selectors as needed.
    """

    def __init__(
        self,
        document: Any,
        *,
        ranker: str | Ranker | None = "auto",
        max_candidates: int = DEFAULT_MAX_CANDIDATES,
        min_confidence: float = DEFAULT_MIN_CONFIDENCE,
    ) -> None:
        if max_candidates < 1:
            raise ValueError("max_candidates must be >= 1")
        start = time.perf_counter()
        self.doc = ensure_document(document)
        self.index = get_index(self.doc)
        self.index_ms = _ms(start)
        self.ranker = get_ranker(ranker)
        self.max_candidates = max_candidates
        self.min_confidence = float(min_confidence)

    def rank(self, fingerprint: ElementFingerprint, extra: list[Element] | tuple[Element, ...] = (),
             timings: dict[str, float] | None = None) -> list[Candidate]:
        """Score candidate elements for ``fingerprint``; best first."""
        t0 = time.perf_counter()
        pool = self.index.candidates(fingerprint, self.max_candidates, extra)
        t1 = time.perf_counter()
        if not pool:
            if timings is not None:
                timings.update(retrieval=(t1 - t0) * 1000.0, features=0.0, ranking=0.0)
            return []
        cand_fps = [self.index.fingerprint(el) for el, _ in pool]
        X = feature_matrix(fingerprint, cand_fps, [s for _, s in pool])
        t2 = time.perf_counter()
        scores = self.ranker.score(X)
        order = sorted(range(len(pool)), key=lambda i: (-scores[i], i))
        t3 = time.perf_counter()
        if timings is not None:
            timings.update(retrieval=(t1 - t0) * 1000.0, features=(t2 - t1) * 1000.0, ranking=(t3 - t2) * 1000.0)
        return [
            Candidate(element=pool[i][0], score=float(scores[i]), rank=r + 1, fingerprint=cand_fps[i], document=self.doc)
            for r, i in enumerate(order)
        ]

    def locate(
        self,
        fingerprint: ElementFingerprint,
        *,
        selector: str | None = None,
        synthesize: bool = True,
    ) -> HealResult:
        """Find the element described by ``fingerprint``; optionally check/repair ``selector``."""
        timings: dict[str, float] = {}
        selector = selector or fingerprint.selector or None
        matches: list[Element] = []
        if selector:
            try:
                matches = self.doc.select(selector)
            except SelectorError:
                matches = []
        candidates = self.rank(fingerprint, extra=tuple(matches[:5]), timings=timings)
        result = HealResult(
            status=STATUS_NOT_FOUND,
            fingerprint=fingerprint,
            candidates=candidates,
            original_selector=selector,
            ranker=self.ranker.name,
            original_matches=len(matches),
            timings_ms=timings,
        )
        if not candidates:
            return result
        best = candidates[0]
        result.confidence = best.score
        result.margin = best.score - (candidates[1].score if len(candidates) > 1 else 0.0)
        if matches and matches[0] is best.element:
            result.status = STATUS_VALID
        elif best.score >= self.min_confidence:
            result.status = STATUS_HEALED
        else:
            result.status = STATUS_LOW_CONFIDENCE
        if synthesize:
            t0 = time.perf_counter()
            if result.status == STATUS_VALID and len(matches) == 1:
                result.selector, result.strategy = selector, "original"
                result.xpath = best.selectors.xpath
            else:
                result.selector, result.strategy = best.selectors.css, best.selectors.css_strategy
                result.xpath = best.selectors.xpath
            timings["synthesis"] = _ms(t0)
        timings["total"] = sum(v for k, v in timings.items() if k != "total")
        return result

    def repair(self, selector: str, old: Any) -> HealResult:
        """Repair ``selector`` given the old page (HTML/Document) or a stored fingerprint."""
        fingerprint = old if isinstance(old, ElementFingerprint) else capture_fingerprint(old, selector)
        return self.locate(fingerprint, selector=selector)


# ---------------------------------------------------------------------------------------
# Functional API
# ---------------------------------------------------------------------------------------


def capture_fingerprint(document: Any, selector: str) -> ElementFingerprint:
    """Fingerprint the first element matched by ``selector`` in ``document``."""
    doc = ensure_document(document)
    matches = doc.select(selector)
    if not matches:
        raise ElementNotFoundError(f"selector {selector!r} matched no element in the reference document")
    return get_index(doc).fingerprint(matches[0], selector)


def capture_element(document: Any, element: Element, selector: str = "") -> ElementFingerprint:
    """Fingerprint a specific ``element`` that belongs to ``document``."""
    doc = ensure_document(document)
    return get_index(doc).fingerprint(element, selector)


def locate(
    fingerprint: ElementFingerprint | dict | str,
    document: Any,
    *,
    ranker: str | Ranker | None = "auto",
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
) -> HealResult:
    """Find the element described by a (stored) fingerprint in ``document``."""
    if isinstance(fingerprint, str):
        fingerprint = ElementFingerprint.from_json(fingerprint)
    elif isinstance(fingerprint, dict):
        fingerprint = ElementFingerprint.from_dict(fingerprint)
    healer = Healer(document, ranker=ranker, max_candidates=max_candidates, min_confidence=min_confidence)
    return healer.locate(fingerprint)


def heal(
    old_document: Any,
    new_document: Any,
    selector: str,
    *,
    ranker: str | Ranker | None = "auto",
    max_candidates: int = DEFAULT_MAX_CANDIDATES,
    min_confidence: float = DEFAULT_MIN_CONFIDENCE,
) -> HealResult:
    """Repair ``selector`` (which worked on ``old_document``) against ``new_document``."""
    fingerprint = capture_fingerprint(old_document, selector)
    healer = Healer(new_document, ranker=ranker, max_candidates=max_candidates, min_confidence=min_confidence)
    return healer.locate(fingerprint, selector=selector)
