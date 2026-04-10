# CBCT-decode-automizer

Starter implementation for a DICOM-first parser that can expand into proprietary
wrapper handling (for example `.dcx` style containers).

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Parse one file

```bash
dicom-parse /path/to/file.dcm
```

The parser first runs a byte-level sniffer, then:

1. Parses raw DICOM P10 directly.
2. Attempts registered wrapper decoders.
3. Falls back to extracting an embedded DICOM candidate when `DICM` appears
   later in the stream.

## Parse a folder (batch mode)

```bash
dicom-parse-batch /path/to/folder --glob "*.dcm" --output report.json
```

This writes a JSON report containing:

- per-file parse results
- summary counters (total, success, failed)
- list of files with validation errors

## Phase 2 extension points

- Add proprietary handlers in `src/dicom_decoder/plugins.py`.
- Register handlers in `default_decoders()`.
- Keep parser logic in `parser.py` unchanged; wrappers should only implement
  `match()` and `unwrap()`.
- Add/replace entries in `default_decoders()` with real vendor-specific
  unwrap logic as you collect `.dcx` samples.
