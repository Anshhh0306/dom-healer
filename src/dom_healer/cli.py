"""Command-line interface: ``dom-healer repair | fingerprint | locate | mcp``.

Exit status: 0 = element found confidently (``valid``/``healed``),
1 = low confidence or not found, 2 = bad input (unreadable file, invalid
selector, selector matches nothing in the reference page).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TextIO

from dom_healer import __version__
from dom_healer.dom import DomHealerError, parse_html
from dom_healer.fingerprint import ElementFingerprint
from dom_healer.healer import (
    DEFAULT_MAX_CANDIDATES,
    DEFAULT_MIN_CONFIDENCE,
    Healer,
    HealResult,
    capture_fingerprint,
)

EXIT_OK, EXIT_UNHEALED, EXIT_INPUT = 0, 1, 2


def _read(path: str) -> bytes:
    if path == "-":
        return sys.stdin.buffer.read()
    return Path(path).read_bytes()


def _add_ranking_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--ranker", default="auto",
                        help="'auto'/'heuristic' (default, hand-weighted), 'linear' (bundled LogisticRegression), or a model .json")
    parser.add_argument("--top-k", type=int, default=3, help="number of candidates to report (default: 3)")
    parser.add_argument("--min-confidence", type=float, default=DEFAULT_MIN_CONFIDENCE,
                        help=f"confidence needed to report 'healed' (default: {DEFAULT_MIN_CONFIDENCE})")
    parser.add_argument("--max-candidates", type=int, default=DEFAULT_MAX_CANDIDATES,
                        help=f"candidates fully scored per query (default: {DEFAULT_MAX_CANDIDATES})")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dom-healer",
        description="Self-healing DOM selectors: repair CSS/XPath selectors after UI changes.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    repair = sub.add_parser("repair", help="repair a selector using the old and new page HTML")
    repair.add_argument("--old-html", required=True, help="page where the selector worked ('-' = stdin)")
    repair.add_argument("--new-html", required=True, help="page where the selector may be broken ('-' = stdin)")
    repair.add_argument("--selector", required=True, help="CSS or XPath selector (css=/xpath= prefixes allowed)")
    _add_ranking_options(repair)

    fingerprint = sub.add_parser("fingerprint", help="capture an element fingerprint as JSON")
    fingerprint.add_argument("--html", required=True, help="page HTML file ('-' = stdin)")
    fingerprint.add_argument("--selector", required=True, help="CSS or XPath selector of the element")
    fingerprint.add_argument("-o", "--output", help="write JSON to this file instead of stdout")

    locate = sub.add_parser("locate", help="find a stored fingerprint in a (new) page")
    locate.add_argument("--fingerprint", required=True, help="fingerprint JSON file ('-' = stdin)")
    locate.add_argument("--html", required=True, help="page HTML file ('-' = stdin)")
    _add_ranking_options(locate)

    sub.add_parser("mcp", help="run the Model Context Protocol server on stdio (needs dom-healer[mcp])")
    return parser


def format_result(result: HealResult, top_k: int) -> str:
    lines = [f"status:     {result.status}  (confidence {result.confidence:.3f}, margin {result.margin:.3f}, "
             f"ranker {result.ranker})"]
    lines.append(f"target:     {result.fingerprint.summary()}")
    if result.original_selector:
        lines.append(f"original:   {result.original_selector}  ({result.original_matches} match(es) in new page)")
    if result.selector:
        lines.append(f"css:        {result.selector}  [{result.strategy}]")
        note = "  (inside shadow DOM: browser XPath can't reach it, use the CSS)" if result.in_shadow_dom else ""
        lines.append(f"xpath:      {result.xpath}{note}")
    if result.candidates:
        lines.append("candidates:")
        for cand in result.candidates[:top_k]:
            lines.append(f"  {cand.rank}. {cand.score:.3f}  {cand.fingerprint.summary()}")
            lines.append(f"       css={cand.css}")
    timings = ", ".join(f"{k}={v:.2f}ms" for k, v in result.timings_ms.items())
    lines.append(f"timings:    {timings}")
    return "\n".join(lines)


def _emit(result: HealResult, args: argparse.Namespace, out: TextIO) -> int:
    if args.json:
        out.write(json.dumps(result.to_dict(top_k=args.top_k), indent=2, ensure_ascii=False) + "\n")
    else:
        out.write(format_result(result, args.top_k) + "\n")
    return EXIT_OK if result.ok else EXIT_UNHEALED


def _healer(html: bytes, args: argparse.Namespace) -> Healer:
    return Healer(parse_html(html), ranker=args.ranker, max_candidates=args.max_candidates,
                  min_confidence=args.min_confidence)


def run(argv: Sequence[str] | None = None, out: TextIO | None = None, err: TextIO | None = None) -> int:
    out = out or sys.stdout
    err = err or sys.stderr
    args = build_parser().parse_args(argv)
    try:
        if args.command == "repair":
            fingerprint = capture_fingerprint(parse_html(_read(args.old_html)), args.selector)
            healer = _healer(_read(args.new_html), args)
            return _emit(healer.locate(fingerprint, selector=args.selector), args, out)
        if args.command == "fingerprint":
            fingerprint = capture_fingerprint(parse_html(_read(args.html)), args.selector)
            payload = fingerprint.to_json(indent=2) + "\n"
            if args.output:
                Path(args.output).write_text(payload, encoding="utf-8")
            else:
                out.write(payload)
            return EXIT_OK
        if args.command == "locate":
            fingerprint = ElementFingerprint.from_json(_read(args.fingerprint).decode("utf-8"))
            healer = _healer(_read(args.html), args)
            return _emit(healer.locate(fingerprint), args, out)
        # args.command == "mcp"
        from dom_healer.mcp_server import main as mcp_main

        mcp_main()
        return EXIT_OK
    except (OSError, ValueError, DomHealerError) as exc:
        err.write(f"dom-healer: error: {exc}\n")
        return EXIT_INPUT
    except ImportError as exc:
        err.write(f"dom-healer: error: {exc}\n")
        return EXIT_INPUT


def main() -> None:  # pragma: no cover - thin wrapper around run()
    sys.exit(run())


if __name__ == "__main__":  # pragma: no cover
    main()
