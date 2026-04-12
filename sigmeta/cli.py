"""SIGMETA command-line interface.

Subcommands:
  classify   Parse a signal-metadata log file (or stdin) into a normalized
             catalog and print a table or JSON.

Analysis-only: reads textual logs, emits a normalized catalog. No transmit
or hardware control.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Optional

from . import TOOL_NAME, TOOL_VERSION
from .core import parse_lines, catalog_summary, ParseError


def _read_input(path: str):
    if path == "-":
        return sys.stdin.read().splitlines()
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read().splitlines()


def _fmt_hz(hz):
    if hz is None:
        return "-"
    if hz >= 1e9:
        return f"{hz / 1e9:.6g} GHz"
    if hz >= 1e6:
        return f"{hz / 1e6:.6g} MHz"
    if hz >= 1e3:
        return f"{hz / 1e3:.6g} kHz"
    return f"{hz:.6g} Hz"


def _print_table(records, summary, stream=sys.stdout):
    if not records:
        print("(no records parsed)", file=stream)
        return
    cols = ["LABEL", "FREQ", "BAND", "MOD", "BW", "SERVICE HINT"]
    rows = []
    for r in records:
        rows.append([
            r.label or "-",
            _fmt_hz(r.freq_hz),
            r.band,
            r.modulation,
            _fmt_hz(r.bandwidth_hz),
            r.service_hint or "-",
        ])
    widths = [len(c) for c in cols]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    line = "  ".join(c.ljust(widths[i]) for i, c in enumerate(cols))
    print(line, file=stream)
    print("  ".join("-" * widths[i] for i in range(len(cols))), file=stream)
    for row in rows:
        print("  ".join(cell.ljust(widths[i]) for i, cell in enumerate(row)),
              file=stream)
    print("", file=stream)
    print(
        f"records={summary['count']}  "
        f"bands={summary['by_band']}  "
        f"mods={summary['by_modulation']}  "
        f"warnings={summary['warnings']}",
        file=stream,
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog=TOOL_NAME,
        description="Parse and classify signal metadata into a normalized catalog.",
    )
    p.add_argument("--version", action="version",
                   version=f"{TOOL_NAME} {TOOL_VERSION}")
    p.add_argument("--format", choices=["table", "json"], default="table",
                   help="output format (default: table)")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("classify",
                       help="parse a signal log into a normalized catalog")
    c.add_argument("input", nargs="?", default="-",
                   help="input log file path, or '-' for stdin (default)")
    c.add_argument("--strict", action="store_true",
                   help="fail on the first unparseable line")
    c.add_argument("--summary-only", action="store_true",
                   help="emit only the aggregate summary")
    return p


def main(argv: Optional[list] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "classify":
        try:
            lines = _read_input(args.input)
        except OSError as e:
            print(f"{TOOL_NAME}: error: {e}", file=sys.stderr)
            return 2

        try:
            records = list(parse_lines(lines, strict=args.strict))
        except ParseError as e:
            print(f"{TOOL_NAME}: parse error: {e}", file=sys.stderr)
            return 1

        summary = catalog_summary(records)

        if args.format == "json":
            payload = {
                "tool": TOOL_NAME,
                "version": TOOL_VERSION,
                "summary": summary,
            }
            if not args.summary_only:
                payload["records"] = [r.to_dict() for r in records]
            print(json.dumps(payload, indent=2))
        else:
            if args.summary_only:
                print(
                    f"records={summary['count']}  "
                    f"bands={summary['by_band']}  "
                    f"mods={summary['by_modulation']}  "
                    f"warnings={summary['warnings']}"
                )
            else:
                _print_table(records, summary)

        # Tool's notion of failure: no usable records extracted.
        if summary["count"] == 0:
            print(f"{TOOL_NAME}: no signal records parsed", file=sys.stderr)
            return 1
        return 0

    parser.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
