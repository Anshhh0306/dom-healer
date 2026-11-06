"""dom-healer: self-healing DOM selectors via structural element fingerprints.

Quick start::

    from dom_healer import heal

    result = heal(old_html, new_html, "button.add-to-cart")
    result.status      # "valid" | "healed" | "low_confidence" | "not_found"
    result.selector    # verified-unique CSS selector for the healed element
    result.xpath       # verified-unique XPath
    result.confidence  # ranker score of the best candidate (0..1)
"""

__version__ = "0.1.0"

from dom_healer.dom import (  # noqa: E402
    Document,
    DomHealerError,
    ParseError,
    SelectorError,
    ensure_document,
    parse_html,
    select,
)
from dom_healer.fingerprint import ElementFingerprint  # noqa: E402
from dom_healer.healer import (  # noqa: E402
    STATUS_HEALED,
    STATUS_LOW_CONFIDENCE,
    STATUS_NOT_FOUND,
    STATUS_VALID,
    Candidate,
    ElementNotFoundError,
    Healer,
    HealResult,
    capture_element,
    capture_fingerprint,
    heal,
    locate,
)
from dom_healer.rankers import HeuristicRanker, LinearRanker, SklearnRanker, get_ranker  # noqa: E402
from dom_healer.synthesis import SelectorSuggestion, suggest_selectors  # noqa: E402

__all__ = [
    "Candidate",
    "Document",
    "DomHealerError",
    "ElementFingerprint",
    "ElementNotFoundError",
    "HealResult",
    "Healer",
    "HeuristicRanker",
    "LinearRanker",
    "ParseError",
    "STATUS_HEALED",
    "STATUS_LOW_CONFIDENCE",
    "STATUS_NOT_FOUND",
    "STATUS_VALID",
    "SelectorError",
    "SelectorSuggestion",
    "SklearnRanker",
    "__version__",
    "capture_element",
    "capture_fingerprint",
    "ensure_document",
    "get_ranker",
    "heal",
    "locate",
    "parse_html",
    "select",
    "suggest_selectors",
]
