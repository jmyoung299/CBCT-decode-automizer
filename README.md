# CBCT-decode-automizer

Starter implementation for a DICOM-first parser that can expand into proprietary
wrapper handling (for example `.dcx` style containers).

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
```

## Web demo (upload dashboard)

Run a local API + dashboard page:

```bash
dicom-web-demo
```

Then open:

```text
http://127.0.0.1:8000
```

You can upload `.dcm`/`.dcx` files in the browser and view parsed metadata and
warnings/errors immediately.

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
dicom-parse-batch /path/to/folder
```

This prints a JSON report containing:

- per-file parse results
- summary counters (`scanned_files`, `parsed_files`, `failed_files`)

## Fixture-driven proprietary plugin development

You can build vendor handlers without touching parser internals:

1. Drop sample wrapped payloads under `tests/fixtures/vendor-cases/<case>/`.
2. Add `plugin.env` and/or `expected.json` for plugin header and expected tags.
3. Implement/adjust a plugin in `plugins.py`.
4. Run fixture checks:

```bash
dicom-golden tests/fixtures/vendor-cases --pretty
```

Current scaffold includes `VendorDcXHeaderPlugin` as a strict fixed-header
example. Replace that logic with real vendor decoding steps as you map the
proprietary format.

## Object-store style ingest adapter

The `dicom_decoder.ingest` module includes:

- `parse_s3_objects()` for in-memory object tuples
- `Boto3S3Reader` for direct S3 reads
- `parse_s3_prefix()` to parse S3 keys without local temp files

Example:

```python
from dicom_decoder.ingest import parse_s3_prefix

summary = parse_s3_prefix(
    bucket="my-bucket",
    prefix="incoming/cbct/",
)
print(summary.to_dict())
```

## Phase 2 extension points

- Add proprietary handlers in `src/dicom_decoder/plugins.py`.
- Register handlers in `default_decoders()`.
- Keep parser logic in `parser.py` unchanged; wrappers should only implement
  `match()` and `unwrap()`.
- Add/replace entries in `default_decoders()` with real vendor-specific
  unwrap logic as you collect `.dcx` samples.
