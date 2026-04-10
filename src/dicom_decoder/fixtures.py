from __future__ import annotations

from pathlib import Path
from typing import Iterable


def load_fixture_bytes(path: str | Path) -> bytes:
    return Path(path).read_bytes()


def list_fixture_files(root: str | Path, suffixes: Iterable[str]) -> list[Path]:
    root_path = Path(root)
    suffix_set = {s.lower() for s in suffixes}
    matches: list[Path] = []
    for candidate in sorted(root_path.rglob("*")):
        if candidate.is_file() and candidate.suffix.lower() in suffix_set:
            matches.append(candidate)
    return matches


def discover_vendor_fixture_cases(root: str | Path) -> list[Path]:
    """
    Return fixture case directories under the given root.
    A case directory contains at least one *.dcx file.
    """
    root_path = Path(root)
    if not root_path.exists():
        return []

    cases: list[Path] = []
    for directory in sorted(p for p in root_path.rglob("*") if p.is_dir()):
        if any(candidate.suffix.lower() == ".dcx" for candidate in directory.iterdir() if candidate.is_file()):
            cases.append(directory)
    return cases
