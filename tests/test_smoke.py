"""Smoke tests for SIGMETA. Pure stdlib, no network."""
import io
import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sigmeta import (  # noqa: E402
    TOOL_NAME,
    TOOL_VERSION,
    parse_line,
    parse_lines,
    classify_band,
    normalize_modulation,
    catalog_summary,
    ParseError,
)
from sigmeta.cli import main, render_csv, CSV_COLUMNS  # noqa: E402

DEMO = os.path.join(os.path.dirname(__file__), "..", "demos", "01-basic", "signals.log")
DEMOS_DIR = os.path.join(os.path.dirname(__file__), "..", "demos")


class TestExports(unittest.TestCase):
    def test_metadata(self):
        self.assertEqual(TOOL_NAME, "sigmeta")
        self.assertTrue(TOOL_VERSION)


class TestModulation(unittest.TestCase):
    def test_aliases(self):
        self.assertEqual(normalize_modulation("NFM"), "FM")
        self.assertEqual(normalize_modulation("wfm"), "FM")
        self.assertEqual(normalize_modulation("USB"), "SSB")
        self.assertEqual(normalize_modulation("QPSK"), "PSK")
        self.assertEqual(normalize_modulation("pulse"), "PULSE")

    def test_unknown(self):
        self.assertEqual(normalize_modulation("zorp"), "UNKNOWN")
        self.assertEqual(normalize_modulation(""), "UNKNOWN")


class TestBands(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(classify_band(145.5e6), "VHF")
        self.assertEqual(classify_band(2.412e9), "UHF")  # 300 MHz-3 GHz
        self.assertEqual(classify_band(5.5e9), "SHF")    # 3-30 GHz
        self.assertEqual(classify_band(14.23e6), "HF")
        self.assertEqual(classify_band(1010e3), "MF")
        self.assertEqual(classify_band(1.0), "UNKNOWN")


class TestParseLine(unittest.TestCase):
    def test_kv_units(self):
        r = parse_line("label=BCN freq=145.500MHz mod=NFM bw=12.5k")
        self.assertAlmostEqual(r.freq_hz, 145.5e6)
        self.assertEqual(r.modulation, "FM")
        self.assertAlmostEqual(r.bandwidth_hz, 12500.0)
        self.assertEqual(r.band, "VHF")
        self.assertEqual(r.label, "BCN")

    def test_positional(self):
        r = parse_line("HF-NET 14.230MHz USB 2.8kHz")
        self.assertAlmostEqual(r.freq_hz, 14.23e6)
        self.assertEqual(r.modulation, "SSB")
        self.assertEqual(r.band, "HF")

    def test_service_hint(self):
        r = parse_line("freq=101.1MHz mod=WFM bw=200kHz")
        self.assertEqual(r.service_hint, "FM broadcast")
        r2 = parse_line("f=2.412GHz mod=OFDM bw=20MHz")
        self.assertIn("ISM", r2.service_hint)

    def test_no_freq_raises(self):
        with self.assertRaises(ParseError):
            parse_line("just some words here")

    def test_comment_raises(self):
        with self.assertRaises(ParseError):
            parse_line("# a comment")


class TestParseLines(unittest.TestCase):
    def test_skips_bad_in_non_strict(self):
        lines = ["freq=100MHz mod=FM", "no freq here", "freq=200MHz mod=AM"]
        recs = list(parse_lines(lines, strict=False))
        self.assertEqual(len(recs), 2)

    def test_strict_raises(self):
        lines = ["freq=100MHz mod=FM", "no freq here"]
        with self.assertRaises(ParseError):
            list(parse_lines(lines, strict=True))


class TestSummary(unittest.TestCase):
    def test_summary(self):
        recs = list(parse_lines([
            "freq=100MHz mod=FM",
            "freq=14MHz mod=USB",
        ]))
        s = catalog_summary(recs)
        self.assertEqual(s["count"], 2)
        self.assertIn("VHF", s["by_band"])
        self.assertIn("HF", s["by_band"])


class TestCLI(unittest.TestCase):
    def test_demo_table(self):
        rc = main(["classify", os.path.abspath(DEMO)])
        self.assertEqual(rc, 0)

    def test_demo_json(self):
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            rc = main(["--format", "json", "classify", os.path.abspath(DEMO)])
        finally:
            sys.stdout = old
        self.assertEqual(rc, 0)
        payload = json.loads(buf.getvalue())
        self.assertEqual(payload["tool"], "sigmeta")
        self.assertEqual(payload["summary"]["count"], 8)
        self.assertTrue(len(payload["records"]) == 8)

    def test_empty_input_fails(self):
        # stdin with no parseable content -> exit 1
        old = sys.stdin
        sys.stdin = io.StringIO("# only a comment\n\n")
        try:
            rc = main(["classify", "-"])
        finally:
            sys.stdin = old
        self.assertEqual(rc, 1)


class TestVersion(unittest.TestCase):
    def test_version_matches_version_file(self):
        # --version (via TOOL_VERSION) must match the published VERSION file,
        # not a stale stub. Regression guard for the 0.1.0 mismatch.
        vf = os.path.join(os.path.dirname(__file__), "..", "sigmeta", "VERSION")
        with open(vf, "r", encoding="utf-8") as fh:
            expected = fh.read().strip()
        self.assertEqual(TOOL_VERSION, expected)
        self.assertNotEqual(TOOL_VERSION, "0.1.0")


class TestCSV(unittest.TestCase):
    def test_render_csv_header_and_rows(self):
        recs = list(parse_lines([
            "label=A freq=145.5MHz mod=NFM bw=12.5k",
            "freq=14.23MHz mod=USB bw=2.8kHz",
        ]))
        out = render_csv(recs)
        lines = out.strip().splitlines()
        self.assertEqual(lines[0], ",".join(CSV_COLUMNS))
        self.assertEqual(len(lines), 3)  # header + 2 records
        self.assertIn("145500000", lines[1])
        self.assertIn("VHF", lines[1])

    def test_render_csv_empty_still_has_header(self):
        out = render_csv([])
        self.assertEqual(out.strip(), ",".join(CSV_COLUMNS))

    def test_render_csv_warning_column(self):
        recs = list(parse_lines(["freq=446MHz mod=wibble bw=12.5k"]))
        out = render_csv(recs)
        self.assertIn("unrecognized modulation token", out)

    def test_cli_csv_format(self):
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            rc = main(["--format", "csv", "classify", os.path.abspath(DEMO)])
        finally:
            sys.stdout = old
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertTrue(out.startswith(",".join(CSV_COLUMNS)))
        # 1 header + 8 demo records
        self.assertEqual(len(out.strip().splitlines()), 9)

    def test_cli_csv_summary_only(self):
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            rc = main(["--format", "csv", "classify", os.path.abspath(DEMO),
                       "--summary-only"])
        finally:
            sys.stdout = old
        self.assertEqual(rc, 0)
        lines = buf.getvalue().strip().splitlines()
        self.assertEqual(lines[0], "count,freq_min_hz,freq_max_hz,warnings")
        self.assertEqual(len(lines), 2)


class TestDemos(unittest.TestCase):
    """Every shipped demo must actually parse into records (except the
    deliberately-empty exit-code demo)."""

    def test_all_demos_fire(self):
        expect_empty = {"05-empty-strict"}
        import glob
        logs = glob.glob(os.path.join(DEMOS_DIR, "*", "*.log"))
        self.assertGreaterEqual(len(logs), 8)
        for path in logs:
            with open(path, "r", encoding="utf-8") as fh:
                recs = list(parse_lines(fh.read().splitlines()))
            demo = os.path.basename(os.path.dirname(path))
            if demo in expect_empty:
                self.assertEqual(len(recs), 0, f"{demo} should be empty")
            else:
                self.assertGreater(len(recs), 0, f"{demo} parsed nothing")


if __name__ == "__main__":
    unittest.main()
