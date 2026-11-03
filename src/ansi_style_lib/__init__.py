"""Terminal colour and style helpers that detect a dumb terminal.

Public API re-exported from :mod:`ansi_style_lib.core`.
"""

from .core import (
    ANSI_RE,
    Style,
    colorize,
    is_dumb_terminal,
    strip_ansi,
)

__all__ = [
    "ANSI_RE",
    "Style",
    "colorize",
    "is_dumb_terminal",
    "strip_ansi",
]

__version__ = "1.0.0"
