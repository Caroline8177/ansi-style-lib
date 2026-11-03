import os
import unittest
from unittest import mock

from ansi_style_lib import (
    ANSI_RE,
    Style,
    colorize,
    is_dumb_terminal,
    strip_ansi,
)


class IsDumbTerminalTests(unittest.TestCase):
    def test_unset_term_is_dumb(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertTrue(is_dumb_terminal())

    def test_dumb_term_is_dumb(self):
        with mock.patch.dict(os.environ, {"TERM": "dumb"}, clear=True):
            self.assertTrue(is_dumb_terminal())

    def test_dumb_term_is_case_insensitive(self):
        with mock.patch.dict(os.environ, {"TERM": "DUMB"}, clear=True):
            self.assertTrue(is_dumb_terminal())

    def test_xterm_is_not_dumb(self):
        with mock.patch.dict(os.environ, {"TERM": "xterm-256color"}, clear=True):
            self.assertFalse(is_dumb_terminal())

    def test_no_color_forces_dumb(self):
        env = {"TERM": "xterm-256color", "NO_COLOR": "1"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertTrue(is_dumb_terminal())

    def test_empty_no_color_does_not_force_dumb(self):
        # An empty NO_COLOR is explicitly allowed by the spec to mean "unset".
        env = {"TERM": "xterm-256color", "NO_COLOR": ""}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertFalse(is_dumb_terminal())

    def test_force_color_overrides_no_color(self):
        env = {"TERM": "dumb", "NO_COLOR": "1", "FORCE_COLOR": "1"}
        with mock.patch.dict(os.environ, env, clear=True):
            self.assertFalse(is_dumb_terminal())

    def test_explicit_term_argument_is_used(self):
        with mock.patch.dict(os.environ, {"TERM": "xterm"}, clear=True):
            self.assertTrue(is_dumb_terminal(term="dumb"))


class StyleTests(unittest.TestCase):
    def test_empty_style_is_falsy(self):
        self.assertFalse(Style())

    def test_empty_style_apply_is_identity(self):
        self.assertEqual(Style().apply("hi"), "hi")

    def test_empty_style_prefix_is_empty(self):
        self.assertEqual(Style().prefix(), "")

    def test_prefix_orders_codes(self):
        style = Style(fg="red", bg="blue", attrs=["bold"])
        self.assertEqual(style.prefix(), "\x1b[31;44;1m")

    def test_duplicate_codes_are_collapsed(self):
        style = Style(attrs=["bold", "bold"])
        self.assertEqual(style.codes, (1,))

    def test_equality_and_hash(self):
        a = Style(fg="red", attrs=["bold"])
        b = Style(fg="red", attrs=["bold"])
        self.assertEqual(a, b)
        self.assertEqual(hash(a), hash(b))
        self.assertEqual(len({a, b}), 1)

    def test_unknown_foreground_raises(self):
        with self.assertRaises(ValueError):
            Style(fg="chartreuse")

    def test_unknown_background_raises(self):
        with self.assertRaises(ValueError):
            Style(bg="chartreuse")

    def test_unknown_attribute_raises(self):
        with self.assertRaises(ValueError):
            Style(attrs=["sparkle"])

    def test_apply_disabled_returns_text(self):
        style = Style(fg="red")
        self.assertEqual(style.apply("hi", enabled=False), "hi")

    def test_apply_enabled_wraps_and_resets(self):
        style = Style(fg="red")
        self.assertEqual(style.apply("hi"), "\x1b[31mhi\x1b[0m")

    def test_repr_is_stable(self):
        self.assertEqual(repr(Style(fg="red")), "Style(codes=(31,))")


class ColorizeTests(unittest.TestCase):
    def test_explicit_enabled_true(self):
        self.assertEqual(
            colorize("hi", fg="green", enabled=True),
            "\x1b[32mhi\x1b[0m",
        )

    def test_explicit_enabled_false(self):
        self.assertEqual(colorize("hi", fg="green", enabled=False), "hi")

    def test_enabled_none_uses_environment(self):
        with mock.patch.dict(os.environ, {"TERM": "dumb"}, clear=True):
            self.assertEqual(colorize("hi", fg="green"), "hi")

    def test_enabled_none_colours_on_real_term(self):
        with mock.patch.dict(os.environ, {"TERM": "xterm"}, clear=True):
            self.assertEqual(colorize("hi", fg="green"), "\x1b[32mhi\x1b[0m")

    def test_empty_style_with_enabled_true_is_identity(self):
        self.assertEqual(colorize("hi", enabled=True), "hi")


class StripAnsiTests(unittest.TestCase):
    def test_strip_single_sequence(self):
        self.assertEqual(strip_ansi("\x1b[31mhi\x1b[0m"), "hi")

    def test_strip_multiple_sequences(self):
        text = "\x1b[1m\x1b[31mhi\x1b[0m there\x1b[0m"
        self.assertEqual(strip_ansi(text), "hi there")

    def test_strip_leaves_other_escapes(self):
        # A cursor-movement sequence is not SGR and must survive.
        text = "\x1b[2Jhello"
        self.assertEqual(strip_ansi(text), text)

    def test_strip_plain_text_is_identity(self):
        self.assertEqual(strip_ansi("plain"), "plain")

    def test_round_trip(self):
        original = "hello, world"
        styled = colorize(original, fg="red", attrs=["bold"], enabled=True)
        self.assertEqual(strip_ansi(styled), original)

    def test_ansi_re_is_exported_and_usable(self):
        self.assertEqual(ANSI_RE.sub("", "\x1b[31mx\x1b[0m"), "x")


if __name__ == "__main__":
    unittest.main()
