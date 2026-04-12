# Demo 01 — Basic signal-log normalization

## Scenario

An analyst has collected a `signals.log` from several disparate sources: a
ham-radio scanner, a weather-satellite receiver, a spectrum-monitor export,
and a couple of hand-typed notes. Every source uses its own formatting and
units — some `key=value`, some positional; frequencies in kHz/MHz/GHz;
bandwidths in `k`/`kHz`/`MHz`; modulation written as `NFM`, `WFM`, `USB`,
`pulse`, etc.

SIGMETA normalizes all of this into a single catalog: a canonical frequency
in Hz, an ITU band, a canonical modulation family, a normalized bandwidth,
and an advisory service hint. This is **analysis only** — SIGMETA never tunes,
transmits, or controls any hardware. It just reads text and classifies it.

## Input

`signals.log` — 9 data lines plus a comment and one deliberately malformed
line (no frequency) that should be skipped in the default non-strict mode.

## Run it

Table view:

```
python -m sigmeta classify demos/01-basic/signals.log
```

JSON view (for piping into other tooling):

```
python -m sigmeta --format json classify demos/01-basic/signals.log
```

Summary only:

```
python -m sigmeta classify demos/01-basic/signals.log --summary-only
```

Strict mode (non-zero exit on the malformed line):

```
python -m sigmeta classify demos/01-basic/signals.log --strict
```

## Expected

- 8 records parsed (the no-frequency line is skipped).
- Bands populate as VHF / UHF / SHF / HF / MF as appropriate.
- `NFM`/`WFM` collapse to `FM`, `USB` to `SSB`, `pulse` to `PULSE`.
- The 101.1 MHz FM entry gets the "FM broadcast" service hint; 2.412 GHz
  OFDM gets "ISM 2.4 GHz (Wi-Fi/BT)"; 1010 kHz AM gets "AM broadcast".
- Exit code 0 (records were parsed). With no parseable records, exit 1.
