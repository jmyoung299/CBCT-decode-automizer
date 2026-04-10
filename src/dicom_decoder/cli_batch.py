import argparse
import json

from .batch import parse_batch


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch parse DICOM/wrapped DICOM files and emit JSON."
    )
    parser.add_argument("input_path", help="File or directory path")
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Recursively walk directories.",
    )
    args = parser.parse_args()

    result = parse_batch(args.input_path, recursive=args.recursive)
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
