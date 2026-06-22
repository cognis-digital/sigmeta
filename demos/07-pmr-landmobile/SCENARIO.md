# Demo 07 — UHF land-mobile / PMR site inventory

## Scenario

A facilities radio coordinator inventories the UHF land-mobile radios on
site: a few FRS/GMRS channels, two licensed business-band pairs, and a
DMR (4FSK) talkgroup. The export is positional with `NFM`/`4fsk` modulation
labels and `12.5k`/`20k` bandwidths. SIGMETA normalizes the modulation
families and confirms the UHF / FRS-GMRS service window.

This is **analysis only**.

## Input

`landmobile.log` — 6 positional rows in the 451-468 MHz UHF land-mobile range.

## Run it

```
python -m sigmeta classify demos/07-pmr-landmobile/landmobile.log
```

## Expected

- 6 records parsed, all `band=UHF`.
- `NFM`→`FM`; `4fsk`→`FSK`.
- The 462-468 MHz rows get the `FRS/GMRS land mobile` service hint.
- Bandwidths normalize: `12.5k`→12500 Hz, `20k`→20000 Hz.

## How to act

Use the catalog to confirm narrowband compliance (12.5 kHz where required)
and that no entry strayed outside the licensed UHF range.
