"""Tests for matuwrap.core.theme module."""

import unittest
from io import StringIO

from rich.console import Console
from rich.table import Table
from rich.theme import Theme

from matuwrap.core.theme import (
    THEME,
    console,
    fmt,
    create_table,
    fix_emoji_width,
    print_header,
    print_kv,
    print_success,
    print_error,
    print_warning,
    print_info,
    print_panel,
)


class TestThemeConstants(unittest.TestCase):
    """Tests for theme constants and initialization."""

    def test_theme_is_rich_theme(self):
        """THEME should be a Rich Theme instance."""
        self.assertIsInstance(THEME, Theme)

    def test_console_is_rich_console(self):
        """console should be a Rich Console instance."""
        self.assertIsInstance(console, Console)

    def test_theme_has_required_styles(self):
        """THEME should have all required style names."""
        required_styles = [
            "title", "label", "value", "success", "warning", "error",
            "muted", "accent", "info", "surface", "str", "num",
            "bool_on", "bool_off", "unit",
        ]
        for style_name in required_styles:
            self.assertIn(style_name, THEME.styles, f"Missing style: {style_name}")


class TestFmt(unittest.TestCase):
    """Tests for fmt() formatting function."""

    def test_fmt_bool_true(self):
        """fmt(True) should return ON with bool_on style."""
        result = fmt(True)
        self.assertIn("bool_on", result)
        self.assertIn("ON", result)

    def test_fmt_bool_false(self):
        """fmt(False) should return OFF with bool_off style."""
        result = fmt(False)
        self.assertIn("bool_off", result)
        self.assertIn("OFF", result)

    def test_fmt_integer(self):
        """fmt(int) should return number with num style."""
        result = fmt(42)
        self.assertIn("num", result)
        self.assertIn("42", result)

    def test_fmt_float(self):
        """fmt(float) should return number with num style."""
        result = fmt(3.14)
        self.assertIn("num", result)
        self.assertIn("3.14", result)

    def test_fmt_integer_with_unit(self):
        """fmt(int, unit) should include unit with unit style."""
        result = fmt(100, "%")
        self.assertIn("num", result)
        self.assertIn("100", result)
        self.assertIn("unit", result)
        self.assertIn("%", result)

    def test_fmt_float_with_unit(self):
        """fmt(float, unit) should include unit with unit style."""
        result = fmt(1.5, "x")
        self.assertIn("num", result)
        self.assertIn("1.5", result)
        self.assertIn("unit", result)
        self.assertIn("x", result)

    def test_fmt_string(self):
        """fmt(str) should return string with str style."""
        result = fmt("hello")
        self.assertIn("str", result)
        self.assertIn("hello", result)

    def test_fmt_string_on(self):
        """fmt('on') should be styled as bool_on."""
        for value in ["on", "ON", "On"]:
            result = fmt(value)
            self.assertIn("bool_on", result, f"'{value}' should use bool_on style")

    def test_fmt_string_off(self):
        """fmt('off') should be styled as bool_off."""
        for value in ["off", "OFF", "Off"]:
            result = fmt(value)
            self.assertIn("bool_off", result, f"'{value}' should use bool_off style")

    def test_fmt_string_true(self):
        """fmt('true') should be styled as bool_on."""
        for value in ["true", "TRUE", "True"]:
            result = fmt(value)
            self.assertIn("bool_on", result, f"'{value}' should use bool_on style")

    def test_fmt_string_false(self):
        """fmt('false') should be styled as bool_off."""
        for value in ["false", "FALSE", "False"]:
            result = fmt(value)
            self.assertIn("bool_off", result, f"'{value}' should use bool_off style")

    def test_fmt_string_yes(self):
        """fmt('yes') should be styled as bool_on."""
        result = fmt("yes")
        self.assertIn("bool_on", result)

    def test_fmt_string_no(self):
        """fmt('no') should be styled as bool_off."""
        result = fmt("no")
        self.assertIn("bool_off", result)

    def test_fmt_string_enabled(self):
        """fmt('enabled') should be styled as bool_on."""
        result = fmt("enabled")
        self.assertIn("bool_on", result)

    def test_fmt_string_disabled(self):
        """fmt('disabled') should be styled as bool_off."""
        result = fmt("disabled")
        self.assertIn("bool_off", result)

    def test_fmt_zero(self):
        """fmt(0) should format as number, not bool."""
        result = fmt(0)
        self.assertIn("num", result)
        self.assertIn("0", result)
        self.assertNotIn("bool", result)

    def test_fmt_negative_number(self):
        """fmt(-5) should format negative numbers correctly."""
        result = fmt(-5)
        self.assertIn("num", result)
        self.assertIn("-5", result)


class TestCreateTable(unittest.TestCase):
    """Tests for create_table() function."""

    def test_create_table_returns_table(self):
        """create_table() should return a Rich Table instance."""
        table = create_table("A", "B", "C")
        self.assertIsInstance(table, Table)

    def test_create_table_has_columns(self):
        """create_table() should create columns for each argument."""
        table = create_table("Name", "Value", "Status")
        self.assertEqual(len(table.columns), 3)

    def test_create_table_with_title(self):
        """create_table() should accept optional title."""
        table = create_table("Col1", title="My Table")
        self.assertEqual(table.title, "My Table")

    def test_create_table_without_title(self):
        """create_table() without title should have None title."""
        table = create_table("Col1")
        self.assertIsNone(table.title)

    def test_create_table_empty(self):
        """create_table() with no columns should work."""
        table = create_table()
        self.assertEqual(len(table.columns), 0)

    def test_create_table_single_column(self):
        """create_table() with single column should work."""
        table = create_table("Only")
        self.assertEqual(len(table.columns), 1)


class TestFixEmojiWidth(unittest.TestCase):
    """Tests for fix_emoji_width() function."""

    def test_removes_variation_selector(self):
        """fix_emoji_width() should remove U+FE0F variation selector."""
        # U+FE0F is the variation selector-16 that makes emoji colorful
        text_with_vs = "Hello\uFE0FWorld"
        result = fix_emoji_width(text_with_vs)
        self.assertEqual(result, "HelloWorld")

    def test_preserves_text_without_selector(self):
        """fix_emoji_width() should not modify text without variation selector."""
        text = "Hello World"
        result = fix_emoji_width(text)
        self.assertEqual(result, text)

    def test_removes_multiple_selectors(self):
        """fix_emoji_width() should remove all variation selectors."""
        text = "A\uFE0FB\uFE0FC\uFE0F"
        result = fix_emoji_width(text)
        self.assertEqual(result, "ABC")

    def test_empty_string(self):
        """fix_emoji_width() should handle empty string."""
        result = fix_emoji_width("")
        self.assertEqual(result, "")

    def test_only_selector(self):
        """fix_emoji_width() should handle string of only selectors."""
        result = fix_emoji_width("\uFE0F\uFE0F")
        self.assertEqual(result, "")


class TestPrintFunctions(unittest.TestCase):
    """Tests for print_* output functions.

    These tests verify that functions execute without error and produce output.
    We capture output using a StringIO buffer.
    """

    def _capture_output(self, func, *args, **kwargs):
        """Helper to capture console output."""
        buffer = StringIO()
        console = Console(file=buffer, theme=THEME, force_terminal=True)
        # Temporarily replace console's file
        original_file = console.file
        console._file = buffer
        try:
            func(*args, **kwargs)
            return buffer.getvalue()
        finally:
            console._file = original_file

    def test_print_header_executes(self):
        """print_header() should execute without error."""
        output = self._capture_output(print_header, "Test Header")
        self.assertIn("Test Header", output)

    def test_print_kv_executes(self):
        """print_kv() should execute without error."""
        output = self._capture_output(print_kv, "Key", "Value")
        self.assertIn("Key", output)
        self.assertIn("Value", output)

    def test_print_kv_custom_width(self):
        """print_kv() should accept custom label width."""
        output = self._capture_output(print_kv, "K", "V", label_width=20)
        self.assertIn("K", output)
        self.assertIn("V", output)

    def test_print_success_executes(self):
        """print_success() should execute without error."""
        output = self._capture_output(print_success, "Success message")
        self.assertIn("Success message", output)

    def test_print_error_executes(self):
        """print_error() should execute without error."""
        output = self._capture_output(print_error, "Error message")
        self.assertIn("Error message", output)

    def test_print_warning_executes(self):
        """print_warning() should execute without error."""
        output = self._capture_output(print_warning, "Warning message")
        self.assertIn("Warning message", output)

    def test_print_info_executes(self):
        """print_info() should execute without error."""
        output = self._capture_output(print_info, "Info message")
        self.assertIn("Info message", output)

    def test_print_panel_executes(self):
        """print_panel() should execute without error."""
        output = self._capture_output(print_panel, "Panel content")
        self.assertIn("Panel content", output)

    def test_print_panel_with_title(self):
        """print_panel() should accept optional title."""
        output = self._capture_output(print_panel, "Content", title="Panel Title")
        self.assertIn("Content", output)


class TestFmtEdgeCases(unittest.TestCase):
    """Edge case tests for fmt() function."""

    def test_fmt_empty_string(self):
        """fmt('') should handle empty string."""
        result = fmt("")
        self.assertIn("str", result)

    def test_fmt_whitespace_string(self):
        """fmt() should handle whitespace-only string."""
        result = fmt("   ")
        self.assertIn("str", result)

    def test_fmt_special_characters(self):
        """fmt() should handle special characters."""
        result = fmt("hello@world#123")
        self.assertIn("str", result)
        self.assertIn("hello@world#123", result)

    def test_fmt_unicode(self):
        """fmt() should handle unicode characters."""
        result = fmt("Hello \u4e16\u754c")  # "Hello 世界"
        self.assertIn("str", result)

    def test_fmt_large_number(self):
        """fmt() should handle large numbers."""
        result = fmt(999999999999)
        self.assertIn("num", result)
        self.assertIn("999999999999", result)

    def test_fmt_small_float(self):
        """fmt() should handle small floats."""
        result = fmt(0.000001)
        self.assertIn("num", result)


if __name__ == "__main__":
    unittest.main()
