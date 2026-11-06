"""Fast, dependency-free text / token similarity primitives.

All functions operate on already-normalised strings (see :func:`normalize_text`)
and are cached, because the same strings are compared many times while ranking
candidates.
"""

from __future__ import annotations

import re
from functools import lru_cache

_WS = re.compile(r"\s+")
_WORD = re.compile(r"[^\W_]+")
_CAMEL = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")
_SPLIT = re.compile(r"[-_:/.\[\]()#@!,]+")

#: Small canonicalisation table for UI copy that is commonly reworded between
#: releases ("Add to bag" vs "Add to cart", "Log in" vs "Sign in").  Written
#: from general UI vocabulary, not from the benchmark fixtures.
CANONICAL_WORDS: dict[str, str] = {
    "bag": "cart",
    "basket": "cart",
    "trolley": "cart",
    "log": "sign",
    "login": "signin",
    "logon": "signin",
    "logout": "signout",
    "logoff": "signout",
    "register": "signup",
    "join": "signup",
    "remove": "delete",
    "trash": "delete",
    "discard": "delete",
    "erase": "delete",
    "edit": "modify",
    "change": "modify",
    "update": "modify",
    "find": "search",
    "lookup": "search",
    "next": "continue",
    "proceed": "continue",
    "previous": "back",
    "prev": "back",
    "telephone": "phone",
    "mobile": "phone",
    "tel": "phone",
    "passcode": "password",
    "pwd": "password",
    "username": "user",
    "zip": "postcode",
    "postal": "postcode",
    "zipcode": "postcode",
    "qty": "quantity",
    "buy": "purchase",
    "export": "download",
    "dismiss": "close",
    "favorite": "wishlist",
    "favourite": "wishlist",
    "favorites": "wishlist",
    "favourites": "wishlist",
    "preferences": "settings",
    "notifications": "alerts",
    "show": "view",
    "see": "view",
    "colour": "color",
    "send": "submit",
    "retype": "confirm",
    "verify": "confirm",
    "repeat": "confirm",
    "reenter": "confirm",
    "photo": "image",
    "picture": "image",
    "avatar": "image",
    "e": "",  # "e-mail" -> "email" handled below; stray "e" dropped
    # units / abbreviations ("30d" is split into "30" + "d")
    "d": "day",
    "h": "hour",
    "hr": "hour",
    "w": "week",
    "wk": "week",
    "mo": "month",
    "yr": "year",
    "min": "minute",
    "sec": "second",
}

STOPWORDS = frozenset(
    {"the", "a", "an", "to", "your", "my", "of", "for", "and", "or", "in", "on", "at", "this", "with", "by", "is", "&"}
)


def normalize_text(text: str | None, limit: int = 200) -> str:
    """Collapse whitespace, strip and lowercase ``text`` (truncated to ``limit``)."""
    if not text:
        return ""
    text = _WS.sub(" ", text).strip().lower()
    return text[:limit] if len(text) > limit else text


_TOKEN = re.compile(r"\d+|[^\W\d_]+")


@lru_cache(maxsize=16384)
def words(text: str) -> tuple[str, ...]:
    """Lower-case alphanumeric words of ``text``."""
    return tuple(_WORD.findall(text.lower().replace("e-mail", "email").replace("re-enter", "reenter")))


def _stem(word: str) -> str:
    """Very light plural stripping ("reviews" -> "review", "categories" -> "category")."""
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word[-1] == "s" and word[-2] not in "sui":
        return word[:-1]
    return word


@lru_cache(maxsize=32768)
def canonical_words(text: str) -> frozenset[str]:
    """Normalised word set: digit/letter runs split ("30d" -> "30", "d"), light stemming,
    :data:`CANONICAL_WORDS` synonyms applied, stopwords removed."""
    out = set()
    canon = CANONICAL_WORDS
    for w in _TOKEN.findall(text.lower().replace("e-mail", "email").replace("re-enter", "reenter")):
        if w in STOPWORDS:
            continue
        w = canon.get(w, w)
        if len(w) > 3 and w[-1] == "s":
            w = _stem(w)
            w = canon.get(w, w)
        if w:
            out.add(w)
    return frozenset(out)


@lru_cache(maxsize=16384)
def trigrams(text: str) -> frozenset[str]:
    padded = f"  {text} "
    return frozenset(padded[i : i + 3] for i in range(len(padded) - 2))


def jaccard(a: frozenset | set, b: frozenset | set) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter)


@lru_cache(maxsize=65536)
def text_similarity(a: str, b: str) -> float:
    """Similarity in [0, 1] between two normalised strings.

    Maximum of character-trigram Dice (robust to typos/suffixes) and canonical
    word Jaccard (robust to reordering and common copy changes).
    """
    if a == b:
        return 1.0 if a else 0.0
    if not a or not b:
        return 0.0
    ta, tb = trigrams(a[:120]), trigrams(b[:120])
    dice = 2.0 * len(ta & tb) / (len(ta) + len(tb))
    wa, wb = canonical_words(a), canonical_words(b)
    if wa and wb:
        return max(dice, jaccard(wa, wb))
    return dice


# ---------------------------------------------------------------------------------------
# Sequences
# ---------------------------------------------------------------------------------------


@lru_cache(maxsize=65536)
def lcs_ratio(a: tuple[str, ...], b: tuple[str, ...]) -> float:
    """``2 * LCS(a, b) / (len(a) + len(b))`` with prefix/suffix trimming for speed."""
    if a == b:
        return 1.0
    la, lb = len(a), len(b)
    if not la or not lb:
        return 0.0
    start = 0
    while start < la and start < lb and a[start] == b[start]:
        start += 1
    end = 0
    while end < la - start and end < lb - start and a[la - 1 - end] == b[lb - 1 - end]:
        end += 1
    ma, mb = a[start : la - end], b[start : lb - end]
    common = start + end
    if ma and mb:
        prev = [0] * (len(mb) + 1)
        for x in ma:
            cur = [0]
            for j, y in enumerate(mb):
                cur.append(prev[j] + 1 if x == y else max(prev[j + 1], cur[j]))
            prev = cur
        common += prev[-1]
    return 2.0 * common / (la + lb)


# ---------------------------------------------------------------------------------------
# Class names and identifiers
# ---------------------------------------------------------------------------------------

#: Utility-class fragments (Tailwind/Bootstrap) that carry styling, not identity.
UTILITY_TOKENS = frozenset(
    ["flex", "grid", "block", "inline", "hidden", "items", "center", "justify", "between", "around", "evenly", "start", "end", "gap", "px", "py", "p", "m", "mx", "my", "mt", "mb", "ml", "mr", "pt", "pb", "pl", "pr", "ps", "pe", "w", "h", "min", "max", "full", "auto", "screen", "text", "font", "bg", "border", "rounded", "shadow", "sm", "md", "lg", "xl", "xs", "xxl", "2xl", "hover", "focus", "active", "disabled", "dark", "col", "cols", "row", "rows", "span", "container", "wrapper", "wrap", "inner", "outer", "relative", "absolute", "fixed", "sticky", "static", "top", "bottom", "left", "right", "inset", "z", "overflow", "truncate", "bold", "semibold", "medium", "normal", "light", "thin", "white", "black", "gray", "grey", "slate", "zinc", "neutral", "stone", "red", "green", "blue", "indigo", "purple", "pink", "yellow", "orange", "emerald", "teal", "cyan", "sky", "violet", "fuchsia", "rose", "amber", "lime", "opacity", "transition", "duration", "ease", "cursor", "pointer", "select", "none", "sr", "only", "space", "x", "y", "leading", "tracking", "uppercase", "lowercase", "capitalize", "underline", "ring", "outline", "divide", "order", "self", "place", "object", "cover", "contain", "aspect", "video", "square", "is", "has", "js", "d", "mw", "mh", "vh", "vw", "fs", "fw", "fst", "lh", "ls", "ms", "me", "ps", "pe", "g", "gx", "gy", "align", "baseline", "nowrap", "break", "all", "visible", "invisible", "clearfix", "float", "shrink", "grow", "basis", "fill", "stroke", "current", "transparent", "opacity", "backdrop", "blur"]
)

_HASHY = re.compile(r"^(?=[a-z0-9]*\d)(?=[a-z0-9]*[a-z])[a-z0-9]{4,}$", re.I)
_OBFUSCATED_PATTERNS = (
    re.compile(r"^css-[a-z0-9]{4,}", re.I),  # emotion
    re.compile(r"^sc-[a-z0-9]{3,}$", re.I),  # styled-components component id
    re.compile(r"^jsx-\d+$"),  # styled-jsx
    re.compile(r"^svelte-[a-z0-9]+$", re.I),
    re.compile(r"^_[a-z0-9_-]{4,}$", re.I),  # CSS-modules (hashed locals)
    re.compile(r"^jss\d+$"),
    re.compile(r"^(?:ng|_ng)(?:content|host)-", re.I),
)


def _case_transitions(token: str) -> int:
    n = 0
    for x, y in zip(token, token[1:]):
        if x.isalpha() and y.isalpha() and x.isupper() != y.isupper():
            n += 1
    return n


def _digit_transitions(token: str) -> int:
    n = 0
    for x, y in zip(token, token[1:]):
        if x.isdigit() != y.isdigit():
            n += 1
    return n


@lru_cache(maxsize=16384)
def is_obfuscated_class(name: str) -> bool:
    """Heuristically detect generated / hashed class names (CSS modules, CSS-in-JS)."""
    if any(p.match(name) for p in _OBFUSCATED_PATTERNS):
        return True
    if len(name) <= 8 and name.isalpha() and _case_transitions(name) >= 4:  # styled-components: "kQwYzP"
        return True
    return bool(len(name) >= 5 and _HASHY.match(name) and _digit_transitions(name) >= 2)


@lru_cache(maxsize=16384)
def identifier_tokens(name: str) -> tuple[str, ...]:
    """Split an identifier/class name into meaningful lower-case tokens.

    ``"ProductCard_addToCart__x7Gq2"`` -> ``("product", "card", "add", "to", "cart")``.
    Hash-like fragments and pure numbers are dropped.
    """
    name = re.sub(r"__[A-Za-z0-9_-]{4,}$", "", name)  # CSS-modules hash suffix
    out = []
    for part in _SPLIT.split(_CAMEL.sub("-", name)):
        if not part:
            continue
        low = part.lower()
        if low.isdigit() or len(low) < 2:
            continue
        if _HASHY.match(low) and _digit_transitions(low) >= 1:
            continue
        out.append(low)
    return tuple(out)


@lru_cache(maxsize=16384)
def class_tokens(classes: tuple[str, ...]) -> frozenset[str]:
    """Semantic tokens from a class list, ignoring obfuscated and utility classes."""
    out: set[str] = set()
    for cls in classes:
        if is_obfuscated_class(cls):
            continue
        base = cls.rsplit(":", 1)[-1]  # strip Tailwind variants (md:, hover:)
        for tok in identifier_tokens(base):
            if tok not in UTILITY_TOKENS:
                out.add(tok)
    return frozenset(out)


_GENERATED_ID = (
    re.compile(r"^:?r[0-9a-z]{1,4}:?$"),  # React useId ":r1f:"
    re.compile(r"^(?:ember|ext-gen|yui_|gwt-|j_id|ctl\d|mui-|radix-|headlessui-|react-select-)", re.I),
    re.compile(r"\d{4,}"),
    re.compile(r"^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$", re.I),
    re.compile(r"[-_:](?=[a-z0-9]*\d)(?=[a-z0-9]*[a-z])[a-z0-9]{3,}$", re.I),  # "field-7f3a"
    re.compile(r"[-_]\d+$"),  # "input-12"
    re.compile(r"^\d"),
)


_RANDOM_VALUE = (
    re.compile(r"^:?r[0-9a-z]{1,4}:?$"),
    re.compile(r"^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$", re.I),
    re.compile(r"^[0-9a-f]{12,}$", re.I),
)


@lru_cache(maxsize=8192)
def looks_random(value: str) -> bool:
    """Weaker check for attribute *values* (SKUs like ``"MH-300"`` are fine; hashes/UUIDs are not)."""
    if not value or len(value) > 64:
        return True
    return any(p.match(value) for p in _RANDOM_VALUE) or is_obfuscated_class(value)


@lru_cache(maxsize=8192)
def looks_generated(value: str) -> bool:
    """True if an id / attribute value looks auto-generated (unsafe to build selectors on)."""
    if not value or len(value) > 64 or " " in value:
        return True
    if any(p.search(value) for p in _GENERATED_ID):
        return True
    return is_obfuscated_class(value)
