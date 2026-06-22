# Demo 04 — HF utility / shortwave monitoring

## Scenario

A shortwave listener consolidates notes from several evenings of HF
monitoring (3-30 MHz): the WWV time station, HF voice nets, an RTTY/FSK
data net, a CW beacon, and a couple of AM utility signals. The notes mix
`key=value` and positional styles and use kHz/MHz freely. SIGMETA folds
them into one HF catalog.

This is **analysis only** — it classifies text, nothing more.

## Input

`hf.log` — 7 mixed-style rows, all in the HF band.

## Run it

```
python -m sigmeta classify demos/04-hf-utility/hf.log
```

Summary only:

```
python -m sigmeta classify demos/04-hf-utility/hf.log --summary-only
```

## Expected

- 7 records parsed, all `band=HF`.
- `USB`→`SSB`, `fsk`→`FSK`, `cw`→`CW`; the SSB rows get the
  `HF voice/utility` hint.
- The bare `250` and `100` parse as bandwidth (Hz) in the positional rows.

## How to act

A clean all-HF catalog confirms your monitoring log is internally
consistent. Any row that classifies outside HF flags a units typo
(e.g. MHz written as GHz).
