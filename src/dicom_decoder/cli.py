import argparse
import json

from .parser import parse_dicom


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Parse DICOM or wrapped DICOM and emit normalized JSON."
    )
    parser.add_argument("path", help="Path to input file")
    args = parser.parse_args()

    result = parse_dicom(args.path)
    print(json.dumps(result.to_dict(), indent=2))


if __name__ == "__main__":
    main()
