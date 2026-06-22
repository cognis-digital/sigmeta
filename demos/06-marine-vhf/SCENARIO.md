# Demo 06 — Marine VHF channel plan

## Scenario

A harbor operations team documents its marine VHF channel plan (156-162
MHz, FM voice, plus the Channel 70 DSC data channel and a NOAA weather
channel). They want a normalized catalog to attach to the SOP and to verify
each channel's frequency before programming handhelds.

This is **analysis only** — no transmit, no radio control.

## Input

`marine.log` — 6 `key=value` rows in the marine VHF band.

## Run it

```
python -m sigmeta classify demos/06-marine-vhf/marine.log
```

CSV to drop into the SOP spreadsheet:

```
python -m sigmeta --format csv classify demos/06-marine-vhf/marine.log
```

## Expected

- 6 records parsed, all `band=VHF`.
- Five voice channels classify as `FM`; Channel 70 (DSC) classifies as `FSK`.
- Channel 16 (156.800 MHz) and the NOAA weather channel are clearly visible
  in the catalog for quick reference.

## How to act

Diff this catalog against the official channel plan; any frequency mismatch
means a handheld would be programmed to the wrong channel.
