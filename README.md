# ansi-style-lib

Small, dependency-free helpers for colouring terminal output and for deciding whether colour should be emitted at all.

```python
from ansi_style_lib import Style, colorize, is_dumb_terminal, strip_ansi

# One-shot helper: consults the environment unless you say otherwise.
print(colorize("warning", fg="yellow", attrs=["bold"]))

# Reusable style object.
header = Style(fg="white", bg="blue", attrs=["bold"])
print(header.apply("title"))

# Decide once, then be explicit.
enabled = not is_dumb_terminal()
print(colorize("quiet", fg="cyan", enabled=enabled))

# Styling never changes the content.
assert strip_ansi(colorize("plain", fg="red", enabled=True)) == "plain"
```

Exported names: `ANSI_RE`, `Style`, `colorize`, `is_dumb_terminal`, `strip_ansi`.

## Why this exists

Most "just wrap it in `\x1b[31m`" helpers assume a terminal. When output is redirected to a file, captured by a CI runner, or run under `cron`, the escape codes end up as literal garbage in the log. The usual fix is to check `sys.stdout.isatty()`, but that is wrong in two common cases: a pager or `less -R` is a tty but still wants codes, and a subprocess that inherited `TERM` but lost the tty does not. This library keys off `TERM`/`NO_COLOR`/`FORCE_COLOR` instead, which is what the surrounding tooling actually respects.

The trade-off is that an unset `TERM` is treated as dumb. That is deliberately conservative: losing colour in an unusual environment is a cosmetic problem, while leaking escape codes into a log file is a correctness problem for anything that parses that log.

## The edge you will hit

`NO_COLOR` is honoured only when it is non-empty, matching the convention documented at no-color.org. `NO_COLOR=` (empty) means "not set" and colour is kept. If you want to force colour off regardless, use `colorize(..., enabled=False)` or set `NO_COLOR=1`.

Only SGR sequences (`ESC [ ... m`) are stripped by `strip_ansi`. Cursor movement, screen clearing and OSC sequences are left alone, so you can pass mixed content through without mangling it.

## API

- `is_dumb_terminal(term=None) -> bool` — `True` when colour should be suppressed. `term` overrides `$TERM`; `FORCE_COLOR` wins over everything, `NO_COLOR` (non-empty) and `TERM=dumb` lose.
- `Style(fg=None, bg=None, attrs=())` — immutable bundle of SGR codes. Unknown names raise `ValueError`. `Style()` is falsy and `apply` is the identity on it.
  - `.codes` — tuple of SGR parameters, deduplicated, in insertion order.
  - `.prefix()` — the opening escape sequence, or `""` for an empty style.
  - `.apply(text, enabled=True)` — wrap `text` in the style plus a reset, or return it unchanged.
- `colorize(text, fg=None, bg=None, attrs=(), enabled=None)` — build a `Style` and apply it. `enabled=None` consults `is_dumb_terminal()`.
- `strip_ansi(text) -> str` — remove SGR sequences.
- `ANSI_RE` — the compiled pattern used by `strip_ansi`.

Colours: `black`, `red`, `green`, `yellow`, `blue`, `magenta`, `cyan`, `white`. Attributes: `bold`, `dim`, `italic`, `underline`, `blink`, `reverse`, `hidden`, `strike`.

## Tests

```
PYTHONPATH=src python -m unittest discover -s tests
```
