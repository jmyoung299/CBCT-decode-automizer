import argparse
import json
from pathlib import Path

from .golden import run_vendor_fixture_suite


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run vendor fixture golden suite and emit JSON summary."
    )
    parser.add_argument(
        "fixtures_root",
        help="Root directory containing vendor fixture case directories.",
    )
    parser.add_argument(
        "--output",
        help="Optional JSON artifact output path.",
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty print JSON output.",
    )
    args = parser.parse_args()

    summary = run_vendor_fixture_suite(args.fixtures_root)
    payload = json.dumps(summary.to_dict(), indent=2 if args.pretty else None)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(payload, encoding="utf-8")
        print(f"Wrote golden suite report: {output_path}")
        return

    print(payload)


if __name__ == "__main__":
    main()
