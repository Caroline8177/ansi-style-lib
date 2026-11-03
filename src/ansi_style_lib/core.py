"""Core ANSI styling primitives.

Everything here is standard library only. The design goal is that styling
never changes the *content* of a string: :func:`strip_ansi` round-trips any
string produced by :func:`colorize` back to its original text.
"""

from __future__ import annotations

import os
import re
from typing import Iterable, Optional, Tuple

# Matches CSI SGR sequences only: ESC [ ... m. We deliberately do not try to
# match every ANSI escape (cursor movement, OSC titles, ...) because stripping
# those would silently change unrelated output a caller piped through us.
ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")

# The colour names we accept. Kept as a plain dict so callers can introspect it
# and so that unknown names fail fast with a clear KeyError.
_FOREGROUND: dict[str, int] = {
    "black": 30,
    "red": 31,
    "green": 32,
    "yellow": 33,
    "blue": 34,
    "magenta": 35,
    "cyan": 36,
    "white": 37,
}

_BACKGROUND: dict[str, int] = {
    "black": 40,
    "red": 41,
    "green": 42,
    "yellow": 43,
    "blue": 44,
    "magenta": 45,
    "cyan": 46,
    "white": 47,
}

_ATTRIBUTES: dict[str, int] = {
    "bold": 1,
    "dim": 2,
    "italic": 3,
    "underline": 4,
    "blink": 5,
    "reverse": 7,
    "hidden": 8,
    "strike": 9,
}

_RESET = "\x1b[0m"


def is_dumb_terminal(term: Optional[str] = None) -> bool:
    """Return ``True`` when colour output should be suppressed.

    The decision is intentionally conservative: we only claim a terminal is
    *not* dumb when we have positive evidence. That means an unset ``TERM``
    (common in cron jobs, CI runners and subprocesses that forgot to forward
    the environment) counts as dumb, which is the safe default — emitting raw
    escape codes into a log file is worse than losing colour.

    ``NO_COLOR`` (any non-empty value) and ``TERM=dumb`` are honoured, as is
    ``FORCE_COLOR`` which overrides everything so users can opt back in.
    """
    if os.environ.get("FORCE_COLOR"):
        return False
    if os.environ.get("NO_COLOR"):
        return True
    if term is None:
        term = os.environ.get("TERM")
    if not term:
        return True
    return term.lower() == "dumb"


class Style:
    """An immutable bundle of ANSI attributes.

    Instances are cheap and hashable, so they can be cached or used as dict
    keys. ``Style()`` is the empty style: :meth:`apply` returns its input
    unchanged rather than wrapping it in a pointless reset pair.
    """

    __slots__ = ("_codes",)

    def __init__(
        self,
        fg: Optional[str] = None,
        bg: Optional[str] = None,
        attrs: Iterable[str] = (),
    ) -> None:
        codes: list[int] = []
        if fg is not None:
            try:
                codes.append(_FOREGROUND[fg])
            except KeyError:
                raise ValueError(f"unknown foreground colour: {fg!r}") from None
        if bg is not None:
            try:
                codes.append(_BACKGROUND[bg])
            except KeyError:
                raise ValueError(f"unknown background colour: {bg!r}") from None
        for attr in attrs:
            try:
                codes.append(_ATTRIBUTES[attr])
            except KeyError:
                raise ValueError(f"unknown attribute: {attr!r}") from None
        # Deduplicate while preserving order: repeating SGR codes is legal but
        # noisy, and it makes equality of styles less obvious to a reader.
        seen: set[int] = set()
        unique: list[int] = []
        for code in codes:
            if code not in seen:
                seen.add(code)
                unique.append(code)
        self._codes: Tuple[int, ...] = tuple(unique)

    @property
    def codes(self) -> Tuple[int, ...]:
        """The SGR parameters, in insertion order, without duplicates."""
        return self._codes

    def __bool__(self) -> bool:
        return bool(self._codes)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Style):
            return NotImplemented
        return self._codes == other._codes

    def __hash__(self) -> int:
        return hash(self._codes)

    def __repr__(self) -> str:
        return f"Style(codes={self._codes!r})"

    def prefix(self) -> str:
        """The escape sequence that turns this style on (empty if no codes)."""
        if not self._codes:
            return ""
        return "\x1b[" + ";".join(str(c) for c in self._codes) + "m"

    def apply(self, text: str, enabled: bool = True) -> str:
        """Wrap *text* in this style.

        When *enabled* is false, or the style is empty, *text* is returned
        verbatim. We do not reset styles we never set, so nested ``apply``
        calls compose the way a caller would expect: the inner reset ends the
        inner style, and the outer reset (if any) is still in effect.
        """
        if not enabled or not self._codes:
            return text
        return self.prefix() + text + _RESET


def colorize(
    text: str,
    fg: Optional[str] = None,
    bg: Optional[str] = None,
    attrs: Iterable[str] = (),
    enabled: Optional[bool] = None,
) -> str:
    """Convenience wrapper around :class:`Style`.

    When *enabled* is ``None`` the environment is consulted via
    :func:`is_dumb_terminal`, which is the behaviour most callers want. Pass
    an explicit boolean to override, e.g. in tests or when writing to a file
    the user explicitly asked to be coloured.
    """
    if enabled is None:
        enabled = not is_dumb_terminal()
    return Style(fg=fg, bg=bg, attrs=attrs).apply(text, enabled=enabled)


def strip_ansi(text: str) -> str:
    """Remove SGR sequences from *text*.

    Only ``ESC[...m`` sequences are removed; other escape sequences are left
    alone so this can be applied to mixed content without mangling it.
    """
    return ANSI_RE.sub("", text)
