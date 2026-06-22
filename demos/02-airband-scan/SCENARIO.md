# Demo 02 — VHF aeronautical airband scan

## Scenario

A monitoring station exports a scanner memory bank covering the civil
aeronautical VHF band (118-137 MHz), where voice is AM with 8.33 kHz or
25 kHz channel spacing. The columns came out as `key=value` pairs. The
analyst wants a normalized catalog confirming every entry lands in the
aeronautical service window and is classified as VHF / AM.

This is **analysis only** — SIGMETA reads text and classifies it. It never
tunes a radio or transmits.

## Input

`airband.log` — 6 `key=value` lines, all in the 118-137 MHz AM band.

## Run it

```
python -m sigmeta classify demos/02-airband-scan/airband.log
```

## Expected

- 6 records parsed, all `band=VHF`, `modulation=AM`.
- Every row gets the `Aeronautical (AM voice / nav)` service hint.
- 0 warnings; exit code 0.

## How to act

Use this as a sanity gate after re-keying a scanner bank: if any row falls
outside VHF/AM or loses the aeronautical hint, a frequency was mistyped.
