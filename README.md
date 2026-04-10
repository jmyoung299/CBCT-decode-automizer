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
dicom-parse-batch /path/to/folder
```

This prints a JSON report containing:

- per-file parse results
- summary counters (`scanned_files`, `parsed_files`, `failed_files`)

## Fixture-driven proprietary plugin development

You can build vendor handlers without touching parser internals:

1. Drop sample wrapped payloads in a fixtures folder.
2. Load them with `dicom_decoder.fixtures.iter_wrapped_samples`.
3. Implement/adjust a plugin in `plugins.py`.
4. Test using `tests/test_plugins_vendor_skeleton.py`.

Current scaffold includes `WsHealthImagingDcxPlugin` as a strict prefix-based
example (`WSDX` + byte strip). Replace that logic with real vendor decoding
steps as you map the proprietary format.

## Object-store style ingest adapter

The `dicom_decoder.ingest` module includes:

- `ObjectStoreClient` protocol (list/get interface)
- `parse_prefix()` to process files from a prefix without local temp files

This lets you connect S3-compatible stores while keeping decode logic in the
same parser pipeline.

## Phase 2 extension points

- Add proprietary handlers in `src/dicom_decoder/plugins.py`.
- Register handlers in `default_decoders()`.
- Keep parser logic in `parser.py` unchanged; wrappers should only implement
  `match()` and `unwrap()`.
- Add/replace entries in `default_decoders()` with real vendor-specific
  unwrap logic as you collect `.dcx` samples.
