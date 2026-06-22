"""SIGMETA core engine.

Parses heterogeneous signal metadata log lines into normalized SignalRecord
objects. Handles assorted frequency units (Hz/kHz/MHz/GHz), bandwidth units,
free-form modulation tokens, and a leading optional label/source. Everything
is pure-stdlib and deterministic.

This module is analysis-only: it reads and classifies textual metadata. It
does not tune radios, transmit, or control any hardware.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field, asdict
from typing import Iterable, Iterator, Optional


# --- Tool identity ---------------------------------------------------------

TOOL_NAME = "sigmeta"


def _read_version() -> str:
    """Resolve the tool version from the repo VERSION file, falling back to a
    sane default. Keeping this in core (not just __init__) ensures the CLI
    --version output matches the published VERSION rather than a stale stub."""
    here = os.path.dirname(os.path.abspath(__file__))
    for candidate in (
        os.path.join(here, "VERSION"),
        os.path.join(os.path.dirname(here), "VERSION"),
    ):
        try:
            with open(candidate, "r", encoding="utf-8") as fh:
                v = fh.read().strip()
            if v:
                return v
        except OSError:
            continue
    return "0.6.6"


TOOL_VERSION = _read_version()


class ParseError(ValueError):
    """Raised when a log line cannot be parsed into a signal record."""


# --- Unit tables -----------------------------------------------------------

_FREQ_UNITS = {
    "hz": 1.0,
    "khz": 1e3,
    "mhz": 1e6,
    "ghz": 1e9,
    "thz": 1e12,
}

_BW_UNITS = {
    "hz": 1.0,
    "khz": 1e3,
    "mhz": 1e6,
    "ghz": 1e9,
    "k": 1e3,   # shorthand often seen in logs (e.g. "12.5k")
    "m": 1e6,
}

# ITU-ish band classification by frequency in Hz: (low_inclusive, high_exclusive, name)
_BANDS = [
    (3e3, 3e4, "VLF"),
    (3e4, 3e5, "LF"),
    (3e5, 3e6, "MF"),
    (3e6, 3e7, "HF"),
    (3e7, 3e8, "VHF"),
    (3e8, 3e9, "UHF"),
    (3e9, 3e10, "SHF"),
    (3e10, 3e11, "EHF"),
]

# Canonical modulation families. Maps common aliases -> canonical token.
_MOD_ALIASES = {
    "fm": "FM",
    "nfm": "FM",
    "wfm": "FM",
    "n-fm": "FM",
    "narrowfm": "FM",
    "am": "AM",
    "usb": "SSB",
    "lsb": "SSB",
    "ssb": "SSB",
    "cw": "CW",
    "morse": "CW",
    "fsk": "FSK",
    "gfsk": "FSK",
    "2fsk": "FSK",
    "4fsk": "FSK",
    "msk": "FSK",
    "gmsk": "FSK",
    "psk": "PSK",
    "bpsk": "PSK",
    "qpsk": "PSK",
    "8psk": "PSK",
    "dpsk": "PSK",
    "qam": "QAM",
    "16qam": "QAM",
    "64qam": "QAM",
    "256qam": "QAM",
    "ofdm": "OFDM",
    "dsss": "DSSS",
    "fhss": "FHSS",
    "ask": "ASK",
    "ook": "ASK",
    "pulse": "PULSE",
    "radar": "PULSE",
}

# Rough service hints by (band, modulation, frequency window). Advisory only.
_SERVICE_RULES = [
    # (predicate, hint)
    (lambda f, b, m: 88e6 <= f < 108e6 and m == "FM", "FM broadcast"),
    (lambda f, b, m: 108e6 <= f < 137e6, "Aeronautical (AM voice / nav)"),
    (lambda f, b, m: 137e6 <= f < 144e6, "Satellite / weather downlink"),
    (lambda f, b, m: 144e6 <= f < 148e6, "Amateur 2m"),
    (lambda f, b, m: 420e6 <= f < 450e6, "Amateur 70cm"),
    (lambda f, b, m: 462e6 <= f < 468e6, "FRS/GMRS land mobile"),
    (lambda f, b, m: 2.4e9 <= f < 2.5e9, "ISM 2.4 GHz (Wi-Fi/BT)"),
    (lambda f, b, m: 5.15e9 <= f < 5.9e9, "ISM/U-NII 5 GHz"),
    (lambda f, b, m: b == "HF" and m == "SSB", "HF voice/utility"),
    (lambda f, b, m: m == "PULSE", "Radar (pulsed)"),
    (lambda f, b, m: m == "AM" and 0.5e6 <= f < 1.7e6, "AM broadcast"),
]


@dataclass
class SignalRecord:
    """A normalized signal metadata record."""

    freq_hz: float
    modulation: str
    bandwidth_hz: Optional[float] = None
    band: str = "UNKNOWN"
    service_hint: str = ""
    label: str = ""
    raw: str = ""
    warnings: list = field(default_factory=list)

    @property
    def freq_mhz(self) -> float:
        return self.freq_hz / 1e6

    def to_dict(self) -> dict:
        d = asdict(self)
        d["freq_mhz"] = round(self.freq_mhz, 6)
        return d


# --- Helpers ---------------------------------------------------------------

def normalize_modulation(token: str) -> str:
    """Map a free-form modulation token to a canonical family.

    Returns "UNKNOWN" for tokens that don't resemble a known scheme.
    """
    if not token:
        return "UNKNOWN"
    key = re.sub(r"[\s_]+", "", token.strip().lower())
    if key in _MOD_ALIASES:
        return _MOD_ALIASES[key]
    # Strip trailing digits/qualifiers (e.g. "qpsk-1/2" -> "qpsk")
    base = re.sub(r"[^a-z]", "", key)
    if base in _MOD_ALIASES:
        return _MOD_ALIASES[base]
    return "UNKNOWN"


def classify_band(freq_hz: float) -> str:
    """Classify a frequency (Hz) into an ITU band name."""
    for low, high, name in _BANDS:
        if low <= freq_hz < high:
            return name
    return "UNKNOWN"


def service_hint(freq_hz: float, band: str, modulation: str) -> str:
    """Best-effort advisory service hint. Empty string if none matches."""
    for pred, hint in _SERVICE_RULES:
        try:
            if pred(freq_hz, band, modulation):
                return hint
        except Exception:
            continue
    return ""


def _parse_quantity(text: str, units: dict, what: str) -> float:
    """Parse a number with an optional unit suffix into a base value."""
    text = text.strip()
    m = re.fullmatch(r"([+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)\s*([a-zA-Z]+)?", text)
    if not m:
        raise ParseError(f"cannot parse {what}: {text!r}")
    value = float(m.group(1))
    unit = (m.group(2) or "").lower()
    if unit == "":
        # Bare number: assume Hz for freq, Hz for bandwidth.
        return value
    if unit not in units:
        raise ParseError(f"unknown {what} unit: {unit!r} in {text!r}")
    return value * units[unit]


# Recognized key tokens for key=value style logs.
_FREQ_KEYS = ("freq", "frequency", "f", "center", "cf", "fc")
_BW_KEYS = ("bw", "bandwidth", "band", "width")
_MOD_KEYS = ("mod", "modulation", "scheme", "type")
_LABEL_KEYS = ("label", "name", "id", "src", "source", "tag")


def _parse_kv(line: str) -> Optional[dict]:
    """Parse a key=value / key:value style line. Returns dict or None."""
    # Value runs until a comma/semicolon, or the next "key=" / "key:" token,
    # or end of line. This keeps space-separated key=value logs from swallowing
    # the rest of the line into the first value.
    pairs = re.findall(
        r"(\w+)\s*[=:]\s*([^,;\s]+(?:\s+(?!\w+\s*[=:])[^,;\s]+)*)",
        line,
    )
    if not pairs:
        return None
    out = {}
    for k, v in pairs:
        out[k.strip().lower()] = v.strip()
    return out


def parse_line(line: str) -> SignalRecord:
    """Parse a single log line into a SignalRecord.

    Supports two broad styles:
      1. key=value:  "label=BCN freq=145.500MHz mod=FM bw=12.5k"
      2. positional: "BCN 145.500MHz FM 12.5k"  (label optional)

    Raises ParseError if no frequency can be found.
    """
    raw = line.rstrip("\n")
    stripped = raw.strip()
    if not stripped or stripped.startswith("#"):
        raise ParseError("blank or comment line")

    warnings: list = []
    label = ""
    freq_hz: Optional[float] = None
    bw_hz: Optional[float] = None
    mod_token = ""

    kv = _parse_kv(stripped)
    if kv:
        for k in _FREQ_KEYS:
            if k in kv:
                freq_hz = _parse_quantity(kv[k], _FREQ_UNITS, "frequency")
                break
        for k in _BW_KEYS:
            if k in kv and k not in _FREQ_KEYS:
                try:
                    bw_hz = _parse_quantity(kv[k], _BW_UNITS, "bandwidth")
                except ParseError as e:
                    warnings.append(str(e))
                break
        for k in _MOD_KEYS:
            if k in kv:
                mod_token = kv[k]
                break
        for k in _LABEL_KEYS:
            if k in kv:
                label = kv[k]
                break

    if freq_hz is None:
        # Positional / free-form parse.
        tokens = re.split(r"[\s,]+", stripped)
        freq_re = re.compile(
            r"^[+-]?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?(?:hz|khz|mhz|ghz|thz)?$",
            re.IGNORECASE,
        )
        remaining = []
        for tok in tokens:
            if freq_hz is None and freq_re.match(tok) and re.search(r"\d", tok):
                # Require a unit OR a value that looks plausibly like a freq.
                if re.search(r"[a-zA-Z]", tok) or "." in tok:
                    try:
                        freq_hz = _parse_quantity(tok, _FREQ_UNITS, "frequency")
                        continue
                    except ParseError:
                        pass
            remaining.append(tok)

        # First leftover non-numeric token before freq becomes label;
        # try to find a modulation and bandwidth among the rest.
        for tok in remaining:
            low = tok.lower()
            base = re.sub(r"[^a-z]", "", low)
            if not mod_token and (low in _MOD_ALIASES or base in _MOD_ALIASES):
                mod_token = tok
            elif bw_hz is None and re.match(
                r"^[+-]?\d+(?:\.\d+)?(?:hz|khz|mhz|ghz|k|m)?$", low
            ) and re.search(r"\d", low):
                try:
                    bw_hz = _parse_quantity(tok, _BW_UNITS, "bandwidth")
                except ParseError:
                    pass
            elif not label and re.search(r"[A-Za-z]", tok):
                label = tok

    if freq_hz is None:
        raise ParseError(f"no frequency found in line: {stripped!r}")
    if freq_hz <= 0:
        raise ParseError(f"non-positive frequency: {freq_hz}")

    modulation = normalize_modulation(mod_token)
    if mod_token and modulation == "UNKNOWN":
        warnings.append(f"unrecognized modulation token: {mod_token!r}")

    band = classify_band(freq_hz)
    if band == "UNKNOWN":
        warnings.append(f"frequency {freq_hz} Hz outside catalogued bands")

    hint = service_hint(freq_hz, band, modulation)

    if bw_hz is not None and bw_hz <= 0:
        warnings.append(f"non-positive bandwidth ignored: {bw_hz}")
        bw_hz = None

    return SignalRecord(
        freq_hz=freq_hz,
        modulation=modulation,
        bandwidth_hz=bw_hz,
        band=band,
        service_hint=hint,
        label=label,
        raw=stripped,
        warnings=warnings,
    )


def parse_lines(lines: Iterable[str], strict: bool = False) -> Iterator[SignalRecord]:
    """Parse an iterable of lines.

    Blank/comment lines are skipped. Unparseable lines raise in strict mode,
    otherwise they are skipped.
    """
    for line in lines:
        try:
            yield parse_line(line)
        except ParseError:
            if strict:
                raise
            continue


def catalog_summary(records: list) -> dict:
    """Aggregate a list of SignalRecord into a summary catalog."""
    by_band: dict = {}
    by_mod: dict = {}
    total_warnings = 0
    for r in records:
        by_band[r.band] = by_band.get(r.band, 0) + 1
        by_mod[r.modulation] = by_mod.get(r.modulation, 0) + 1
        total_warnings += len(r.warnings)
    freqs = [r.freq_hz for r in records]
    return {
        "count": len(records),
        "by_band": dict(sorted(by_band.items())),
        "by_modulation": dict(sorted(by_mod.items())),
        "freq_min_hz": min(freqs) if freqs else None,
        "freq_max_hz": max(freqs) if freqs else None,
        "warnings": total_warnings,
    }
