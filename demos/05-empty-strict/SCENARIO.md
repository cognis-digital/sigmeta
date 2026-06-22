# Demo 05 — No usable records (exit-code / CI gate)

## Scenario

An automated pipeline drops a log file into SIGMETA every shift. Sometimes
the receiver was offline and the file is just handover prose with no signal
data. The pipeline needs to detect that case reliably via the exit code,
not by scraping stdout.

This is **analysis only**.

## Input

`notes.log` — comments and free text, zero parseable frequencies.

## Run it

```
python -m sigmeta classify demos/05-empty-strict/notes.log; echo "exit=$?"
```

Or as a CI gate:

```
python -m sigmeta classify demos/05-empty-strict/notes.log \
  || echo "no usable signal records this shift"
```

Strict mode fails on the first unparseable data line:

```
python -m sigmeta classify demos/05-empty-strict/notes.log --strict; echo "exit=$?"
```

## Expected

- `(no records parsed)` on stdout, `sigmeta: no signal records parsed` on
  stderr, and **exit code 1**.
- The non-zero exit is the contract automation should branch on.

## How to act

Treat exit 1 as "no signal this shift" — page only if it persists across
multiple shifts (likely a dead receiver), not on a single empty file.
