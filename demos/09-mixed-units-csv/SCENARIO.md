# Demo 09 — Heterogeneous capture → CSV export

## Scenario

A capture from a mixed toolchain arrives with every unit and style the
tools could throw at it: bare-Hz, kHz, MHz, GHz, scientific notation
(`10e9`), `k`/`M` bandwidth shorthand, lowercase modulation tokens, and one
deliberately unrecognized modulation (`wibble`). The analyst wants it all
normalized and dumped to CSV to import into a spreadsheet or SIEM.

This exercises the `--format csv` export added in this release.

This is **analysis only**.

## Input

`capture.log` — 7 rows mixing every supported unit and both line styles,
including one row with an unknown modulation that should warn.

## Run it

```
python -m sigmeta --format csv classify demos/09-mixed-units-csv/capture.log
```

Save it:

```
python -m sigmeta --format csv classify demos/09-mixed-units-csv/capture.log \
  > catalog.csv
```

Summary as CSV:

```
python -m sigmeta --format csv classify demos/09-mixed-units-csv/capture.log --summary-only
```

## Expected

- A header row `label,freq_hz,freq_mhz,band,modulation,bandwidth_hz,service_hint,warnings`
  followed by 7 data rows.
- Bands span VHF / UHF / HF / SHF; `10e9` resolves to 10 GHz (SHF).
- The `wibble` row classifies as `modulation=UNKNOWN` and carries the
  warning `unrecognized modulation token: 'wibble'` in the `warnings` column.

## How to act

`catalog.csv` is your portable artifact — open it in a spreadsheet, sort by
`band`, or load it into a SIEM. Filter the `warnings` column to find rows
that need a human look.
