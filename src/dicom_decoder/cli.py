import argparse
import json

from .batch import parse_many
from .parser import parse_dicom


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse DICOM or wrapped DICOM and emit normalized JSON."
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="Path to input file (single mode).",
    )
    parser.add_argument(
        "--batch",
        help="Directory to recursively parse for .dcm/.dicom/.dcm/.dcx files.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty print JSON output.",
    )
    args = parser.parse_args()

    if args.batch:
        result = parse_many(args.batch)
        indent = 2 if args.pretty else None
        print(json.dumps(result.to_dict(), indent=indent))
        return

    if not args.path:
        parser.error("Provide either a file path or --batch directory.")

    result = parse_dicom(args.path)
    indent = 2 if args.pretty else None
    print(json.dumps(result.to_dict(), indent=indent))


if __name__ == "__main__":
    main()
