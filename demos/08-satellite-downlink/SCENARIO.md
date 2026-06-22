# Demo 08 — Satellite / weather downlink tracking

## Scenario

A ground station logs the downlinks it tracks across the day: VHF
weather-satellite APT/LRPT (137 MHz), a NOAA weather-radio channel, an
amateur 2 m satellite pass, and L-band / S-band telemetry downlinks. The
log mixes `key=value` and positional styles and spans VHF up to SHF.

This is **analysis only** — it classifies downlink metadata, it does not
command or track any spacecraft.

## Input

`sat.log` — 6 mixed-style rows spanning VHF (137-162 MHz) and UHF (1.69 /
2.25 GHz).

## Run it

```
python -m sigmeta classify demos/08-satellite-downlink/sat.log
```

JSON for a pass-tracking dashboard:

```
python -m sigmeta --format json classify demos/08-satellite-downlink/sat.log | jq '.records[].service_hint'
```

## Expected

- 6 records parsed; bands include VHF and UHF.
- The 137.x MHz rows get the `Satellite / weather downlink` hint.
- The 146.0 MHz row classifies as `Amateur 2m`.
- L-band (1.6925 GHz) and S-band (2.25 GHz) rows classify as UHF with
  `OFDM` / `PSK` modulation.

## How to act

Group by `service_hint` to build a per-band pass schedule; the catalog tells
you which receiver/antenna each downlink needs.
