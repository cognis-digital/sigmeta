"""Hardening tests for SIGMETA: edge cases, bad input, and error paths."""
from __future__ import annotations

import math
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sigmeta.core import (
    ParseError,
    _parse_quantity,
    _FREQ_UNITS,
    catalog_summary,
    normalize_modulation,
    parse_line,
    parse_lines,
    TOOL_NAME,
    TOOL_VERSION,
)
from sigmeta.cli import main


class TestCoreConstants(unittest.TestCase):
    """TOOL_NAME and TOOL_VERSION must be importable from core directly."""

    def test_tool_name(self):
        self.assertEqual(TOOL_NAME, "sigmeta")

    def test_tool_version(self):
        self.assertTrue(TOOL_VERSION)


class TestNormalizeModulationEdgeCases(unittest.TestCase):
    """normalize_modulation must not crash on non-string input."""

    def test_none_returns_unknown(self):
        self.assertEqual(normalize_modulation(None), "UNKNOWN")

    def test_integer_returns_unknown(self):
        self.assertEqual(normalize_modulation(42), "UNKNOWN")

    def test_empty_bytes_returns_unknown(self):
        # bytes is not str
        self.assertEqual(normalize_modulation(b"FM"), "UNKNOWN")


class TestParseQuantityGuards(unittest.TestCase):
    """_parse_quantity must raise ParseError on non-finite values."""

    def test_unknown_unit_raises(self):
        with self.assertRaises(ParseError) as ctx:
            _parse_quantity("100xyz", _FREQ_UNITS, "frequency")
        self.assertIn("unknown", str(ctx.exception))

    def test_non_numeric_raises(self):
        with self.assertRaises(ParseError):
            _parse_quantity("notanumber", _FREQ_UNITS, "frequency")

    def test_valid_value_finite(self):
        val = _parse_quantity("145.5MHz", _FREQ_UNITS, "frequency")
        self.assertTrue(math.isfinite(val))
        self.assertAlmostEqual(val, 145.5e6)

    def test_bare_number_returns_as_hz(self):
        val = _parse_quantity("1000", _FREQ_UNITS, "frequency")
        self.assertAlmostEqual(val, 1000.0)


class TestParseLineEdgeCases(unittest.TestCase):
    """parse_line must raise ParseError cleanly for edge-case bad input."""

    def test_blank_line_raises(self):
        with self.assertRaises(ParseError):
            parse_line("")

    def test_whitespace_only_raises(self):
        with self.assertRaises(ParseError):
            parse_line("   \t  ")

    def test_negative_frequency_raises(self):
        with self.assertRaises(ParseError):
            parse_line("freq=-100MHz mod=FM")

    def test_zero_frequency_raises(self):
        # zero freq is non-positive
        with self.assertRaises(ParseError):
            parse_line("freq=0Hz mod=FM")

    def test_non_positive_bandwidth_is_ignored(self):
        # Negative BW in kv should produce a warning, not raise
        r = parse_line("freq=100MHz mod=FM bw=-5kHz")
        self.assertIsNone(r.bandwidth_hz)
        self.assertTrue(any("non-positive bandwidth" in w for w in r.warnings))

    def test_unrecognized_modulation_produces_warning(self):
        r = parse_line("freq=100MHz mod=ZORKMODULATION")
        self.assertEqual(r.modulation, "UNKNOWN")
        self.assertTrue(any("unrecognized modulation" in w for w in r.warnings))

    def test_out_of_band_frequency_produces_warning(self):
        # 1 Hz is below VLF (3 kHz)
        r = parse_line("freq=1Hz mod=FM")
        self.assertEqual(r.band, "UNKNOWN")
        self.assertTrue(any("outside catalogued bands" in w for w in r.warnings))


class TestParseLinesEmptyInput(unittest.TestCase):
    """parse_lines on empty or all-comment input yields nothing."""

    def test_empty_list(self):
        records = list(parse_lines([]))
        self.assertEqual(records, [])

    def test_all_comments(self):
        records = list(parse_lines(["# comment", "# another comment", ""]))
        self.assertEqual(records, [])


class TestCatalogSummaryEdgeCases(unittest.TestCase):
    """catalog_summary must handle zero records gracefully."""

    def test_empty_records(self):
        s = catalog_summary([])
        self.assertEqual(s["count"], 0)
        self.assertIsNone(s["freq_min_hz"])
        self.assertIsNone(s["freq_max_hz"])
        self.assertEqual(s["by_band"], {})
        self.assertEqual(s["by_modulation"], {})
        self.assertEqual(s["warnings"], 0)


class TestCLIMissingFile(unittest.TestCase):
    """CLI must return exit code 2 for a missing input file."""

    def test_missing_file_exits_2(self):
        rc = main(["classify", "/no/such/file/sigmeta_test_xyz.log"])
        self.assertEqual(rc, 2)

    def test_missing_file_is_not_a_traceback(self):
        # Verify no unhandled exception — the function returns cleanly
        try:
            rc = main(["classify", "/totally/missing/path.log"])
        except Exception as exc:
            self.fail(f"main() raised {type(exc).__name__} instead of returning 2")
        self.assertEqual(rc, 2)


class TestCLIAllCommentFile(unittest.TestCase):
    """CLI returns exit code 1 when no records are parsed from a real file."""

    def test_all_comment_file_exits_1(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".log", delete=False, encoding="utf-8"
        ) as fh:
            fh.write("# only comments\n\n# nothing here\n")
            tmp = fh.name
        try:
            rc = main(["classify", tmp])
            self.assertEqual(rc, 1)
        finally:
            os.unlink(tmp)


class TestCLIMalformedInput(unittest.TestCase):
    """CLI in strict mode exits 1 on an unparseable line."""

    def test_strict_mode_unparseable_exits_1(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".log", delete=False, encoding="utf-8"
        ) as fh:
            fh.write("freq=100MHz mod=FM\n")
            fh.write("this line has no frequency\n")
            tmp = fh.name
        try:
            rc = main(["classify", "--strict", tmp])
            self.assertEqual(rc, 1)
        finally:
            os.unlink(tmp)


class TestMcpServerModule(unittest.TestCase):
    """mcp_server._scan must be importable and work without the mcp package."""

    def test_scan_function_importable(self):
        from sigmeta.mcp_server import _scan  # noqa: F401

    def test_scan_parses_valid_input(self):
        from sigmeta.mcp_server import _scan
        result = _scan("freq=145.5MHz mod=NFM bw=12.5k\nfreq=14.230MHz mod=USB")
        self.assertEqual(result["summary"]["count"], 2)
        self.assertEqual(len(result["records"]), 2)

    def test_scan_empty_input(self):
        from sigmeta.mcp_server import _scan
        result = _scan("")
        self.assertEqual(result["summary"]["count"], 0)
        self.assertEqual(result["records"], [])

    def test_scan_all_garbage(self):
        from sigmeta.mcp_server import _scan
        result = _scan("# comment\nno freq here either\n   ")
        self.assertEqual(result["summary"]["count"], 0)


if __name__ == "__main__":
    unittest.main()
