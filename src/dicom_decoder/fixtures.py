from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


def _parse_metadata_file(path: Path) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data


def _bool_from_string(value: str, default: bool) -> bool:
    if value == "":
        return default
    lowered = value.strip().lower()
    return lowered in {"1", "true", "yes", "on"}


def _int_from_string(value: str, default: int) -> int:
    if value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


@dataclass
class FixturePluginConfig:
    plugin_type: str
    name: str
    prefix_bytes: bytes
    strip_prefix_bytes: int
    strip_suffix_bytes: int
    reverse_payload: bool


@dataclass
class VendorFixtureCase:
    case_name: str
    case_dir: Path
    wrapped_path: Path
    plugin: FixturePluginConfig
    expected_tags: dict[str, str]
    expect_warning_contains: list[str]
    expect_error_contains: list[str]
    expect_unwrap_plugin: str | None
    expect_source_format: str | None
    expect_has_pixel_data: bool | None
    expected_tags: dict[str, str]
    enabled: bool = True


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


def _parse_expected_json(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def _get_prefix_bytes(config: dict[str, str], expected_json: dict[str, object]) -> bytes:
    plugin_json = expected_json.get("plugin", {}) if isinstance(expected_json, dict) else {}
    if isinstance(plugin_json, dict):
        header_hex = plugin_json.get("header_hex")
        if isinstance(header_hex, str) and header_hex.strip():
            return bytes.fromhex(header_hex.strip())
        header_ascii = plugin_json.get("header_ascii")
        if isinstance(header_ascii, str) and header_ascii:
            return header_ascii.encode("ascii")

    if "header_hex" in config and config["header_hex"]:
        return bytes.fromhex(config["header_hex"])
    if "header_ascii" in config and config["header_ascii"]:
        return config["header_ascii"].encode("ascii")
    if "magic_prefix" in config and config["magic_prefix"]:
        return config["magic_prefix"].encode("ascii")
    # Default used by scaffold tests.
    return b"VEND\x01\x00\x00\x00"


def _get_plugin_name(config: dict[str, str], expected_json: dict[str, object]) -> str:
    plugin_json = expected_json.get("plugin", {}) if isinstance(expected_json, dict) else {}
    if isinstance(plugin_json, dict):
        name = plugin_json.get("name")
        if isinstance(name, str) and name:
            return name
    if "name" in config and config["name"]:
        return config["name"]
    return "fixture-vendor-header"


def _get_plugin_type(config: dict[str, str], expected_json: dict[str, object]) -> str:
    plugin_json = expected_json.get("plugin", {}) if isinstance(expected_json, dict) else {}
    if isinstance(plugin_json, dict):
        plugin_type = plugin_json.get("type")
        if isinstance(plugin_type, str) and plugin_type:
            return plugin_type
    plugin_type = config.get("plugin_type", "")
    if plugin_type:
        return plugin_type
    return "header"


def _get_expected_patient_id(config: dict[str, str], expected_json: dict[str, object]) -> str | None:
    expected_patient_id = config.get("expected_patient_id")
    if expected_patient_id:
        return expected_patient_id

    if isinstance(expected_json, dict):
        direct = expected_json.get("expected_patient_id")
        if isinstance(direct, str) and direct:
            return direct
        expected_obj = expected_json.get("expected", {})
        if isinstance(expected_obj, dict):
            patient_id = expected_obj.get("PatientID")
            if isinstance(patient_id, str) and patient_id:
                return patient_id
    return None


def _get_expected_tags(expected_json: dict[str, object]) -> dict[str, str]:
    tags: dict[str, str] = {}
    if not isinstance(expected_json, dict):
        return tags

    expected_obj = expected_json.get("expected", {})
    if not isinstance(expected_obj, dict):
        return tags

    for key, value in expected_obj.items():
        if isinstance(value, str):
            tags[key] = value
    return tags


def _get_expected_contains(expected_json: dict[str, object], key: str) -> list[str]:
    if not isinstance(expected_json, dict):
        return []
    values = expected_json.get(key, [])
    if not isinstance(values, list):
        return []
    return [v for v in values if isinstance(v, str) and v]


def _get_expected_bool(expected_json: dict[str, object], key: str) -> bool | None:
    if not isinstance(expected_json, dict):
        return None
    value = expected_json.get(key)
    if isinstance(value, bool):
        return value
    return None


def load_vendor_fixture_case(case_dir: str | Path) -> VendorFixtureCase | None:
    case_path = Path(case_dir)
    wrapped_path = case_path / "wrapped.dcx"
    if not wrapped_path.exists():
        return None

    plugin_env = case_path / "plugin.env"
    expected_json_path = case_path / "expected.json"
    metadata_path = case_path / "metadata.txt"

    config: dict[str, str] = {}
    for candidate in (plugin_env, metadata_path):
        if candidate.exists():
            config.update(_parse_metadata_file(candidate))

    expected_json = _parse_expected_json(expected_json_path)
    enabled = _bool_from_string(config.get("enabled", ""), True)
    if _int_from_string(config.get("skip", ""), 0) > 0:
        return None
    if not enabled:
        return None

    prefix = _get_prefix_bytes(config, expected_json)
    strip_prefix = _int_from_string(config.get("strip_prefix_bytes", ""), len(prefix))
    strip_suffix = _int_from_string(config.get("strip_suffix_bytes", ""), 0)
    reverse_payload = _bool_from_string(config.get("reverse_payload", ""), False)
    plugin_cfg = FixturePluginConfig(
        plugin_type=_get_plugin_type(config, expected_json),
        name=_get_plugin_name(config, expected_json),
        prefix_bytes=prefix,
        strip_prefix_bytes=strip_prefix,
        strip_suffix_bytes=strip_suffix,
        reverse_payload=reverse_payload,
    )

    expected_tags = _get_expected_tags(expected_json)
    patient_id = _get_expected_patient_id(config, expected_json)
    if patient_id is not None:
        expected_tags.setdefault("PatientID", patient_id)

    return VendorFixtureCase(
        case_name=case_path.name,
        case_dir=case_path,
        wrapped_path=wrapped_path,
        plugin=plugin_cfg,
        expected_tags=expected_tags,
        expect_warning_contains=_get_expected_contains(expected_json, "expect_warnings_contains"),
        expect_error_contains=_get_expected_contains(expected_json, "expect_errors_contains"),
        expect_unwrap_plugin=_get_expected_tags(expected_json).get("unwrap_plugin"),
        expect_source_format=_get_expected_tags(expected_json).get("source_format"),
        expect_has_pixel_data=_get_expected_bool(expected_json, "expect_has_pixel_data"),
        enabled=True,
    )


def load_vendor_fixture_cases(root: str | Path) -> list[VendorFixtureCase]:
    root_path = Path(root)
    if not root_path.exists():
        return []

    loaded: list[VendorFixtureCase] = []
    for case_dir in discover_vendor_fixture_cases(root_path):
        case = load_vendor_fixture_case(case_dir)
        if case is not None:
            loaded.append(case)
    return loaded
