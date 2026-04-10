import argparse
import json

from .batch import parse_directory


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch parse DICOM/wrapped DICOM files and emit JSON."
    )
    parser.add_argument("input_path", help="File or directory path")
    parser.add_argument("--output", help="Optional JSON output file path.")
    args = parser.parse_args()

    result = parse_directory(args.input_path)
    payload = json.dumps(result.to_dict(), indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as handle:
            handle.write(payload)
        print(f"Wrote batch parse report: {args.output}")
        return

    print(payload)


if __name__ == "__main__":
    main()
