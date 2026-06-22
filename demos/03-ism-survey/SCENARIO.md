# Demo 03 — ISM / unlicensed-band spectrum survey

## Scenario

A site survey at an industrial facility logs energy across the common
unlicensed ISM / U-NII bands to inventory what is using the spectrum:
433 MHz remotes, 868 MHz LoRa, 915 MHz FHSS telemetry, 2.4 GHz Wi-Fi and
Bluetooth LE, and a 5 GHz U-NII Wi-Fi channel. The capture tool wrote
positional rows (`label freq mod bw`).

This is **analysis only** — no transmit, no hardware control.

## Input

`ism.log` — 7 positional rows spanning UHF and SHF ISM/U-NII allocations.

## Run it

JSON for piping into an asset inventory:

```
python -m sigmeta --format json classify demos/03-ism-survey/ism.log | jq '.summary.by_band'
```

Table view:

```
python -m sigmeta classify demos/03-ism-survey/ism.log
```

## Expected

- 7 records parsed; bands span UHF (433/868/915 MHz, 2.4 GHz) and SHF (5 GHz).
- 2.4 GHz entries get the `ISM 2.4 GHz (Wi-Fi/BT)` hint; the 5.18 GHz entry
  gets `ISM/U-NII 5 GHz`.
- Modulations normalize: `ASK`, `GFSK`→`FSK`, `FHSS`, `OFDM`.

## How to act

The `by_band` / `by_modulation` rollup is your spectrum-occupancy baseline.
Re-run after a change and diff the summary to spot new emitters.
