from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .fixtures import FixturePluginConfig, VendorFixtureCase, load_vendor_fixture_cases
from .parser import parse_dicom
from .plugins import build_fixture_plugin, WrapperDecoder
from .models import ParseResult


@dataclass
class GoldenCaseResult:
    case_name: str
    input_file: str
    ok: bool
    errors: list[str]
    warnings: list[str]
    unwrap_plugin: str | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass
class GoldenRunSummary:
    total_cases: int
    passed_cases: int
    failed_cases: int
    cases: list[dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _build_decoder_for_case(case: VendorFixtureCase) -> WrapperDecoder:
    cfg: FixturePluginConfig = case.plugin
    return build_fixture_plugin(
        name=cfg.name,
        prefix=cfg.prefix_bytes,
        strip_prefix_bytes=cfg.strip_prefix_bytes,
        strip_suffix_bytes=cfg.strip_suffix_bytes,
        reverse_payload=cfg.reverse_payload,
    )


def _validate_expected(case: VendorFixtureCase, parsed: ParseResult) -> list[str]:
    errors = list(parsed.errors)

    for tag_key, expected_value in case.expected_tags.items():
        actual = parsed.tags.get(tag_key)
        if actual != expected_value:
            errors.append(
                f"Expected tag {tag_key}={expected_value!r}, got {actual!r}."
            )

    if case.expect_unwrap_plugin is not None and parsed.unwrap_plugin != case.expect_unwrap_plugin:
        errors.append(
            f"Expected unwrap_plugin={case.expect_unwrap_plugin!r}, got {parsed.unwrap_plugin!r}."
        )

    if case.expect_source_format is not None and parsed.source_format != case.expect_source_format:
        errors.append(
            f"Expected source_format={case.expect_source_format!r}, got {parsed.source_format!r}."
        )

    if case.expect_has_pixel_data is not None and parsed.has_pixel_data != case.expect_has_pixel_data:
        errors.append(
            f"Expected has_pixel_data={case.expect_has_pixel_data!r}, got {parsed.has_pixel_data!r}."
        )

    for fragment in case.expect_error_contains:
        if not any(fragment in msg for msg in parsed.errors):
            errors.append(f"Expected error containing {fragment!r} not found.")

    for fragment in case.expect_warning_contains:
        if not any(fragment in msg for msg in parsed.warnings):
            errors.append(f"Expected warning containing {fragment!r} not found.")

    return errors


@dataclass
class FixtureCaseRunResult:
    case: VendorFixtureCase
    parse_result: ParseResult


def run_fixture_case(case_dir: str | Path) -> FixtureCaseRunResult:
    case_path = Path(case_dir)
    cases = load_vendor_fixture_cases(case_path.parent)
    target = next((c for c in cases if c.case_name == case_path.name), None)
    if target is None:
        raise ValueError(f"No fixture metadata found for case directory: {case_dir}")
    decoder = _build_decoder_for_case(target)
    parsed = parse_dicom(str(target.wrapped_path), decoders=[decoder])
    return FixtureCaseRunResult(case=target, parse_result=parsed)


def run_vendor_fixture_suite(
    root: str | Path,
    *,
    plugin_map: dict[str, WrapperDecoder] | None = None,
) -> GoldenRunSummary:
    cases = load_vendor_fixture_cases(root)
    results: list[GoldenCaseResult] = []
    passed = 0

    for case in cases:
        cfg: FixturePluginConfig = case.plugin
        decoder = (
            plugin_map[cfg.name]
            if plugin_map and cfg.name in plugin_map
            else _build_decoder_for_case(case)
        )
        parsed = parse_dicom(str(case.wrapped_path), decoders=[decoder])
        case_errors = _validate_expected(case, parsed)
        ok = not case_errors
        if ok:
            passed += 1

        results.append(
            GoldenCaseResult(
                case_name=case.case_name,
                input_file=str(case.wrapped_path),
                ok=ok,
                errors=case_errors,
                warnings=list(parsed.warnings),
                unwrap_plugin=parsed.unwrap_plugin,
            )
        )

    return GoldenRunSummary(
        total_cases=len(results),
        passed_cases=passed,
        failed_cases=len(results) - passed,
        cases=[r.to_dict() for r in results],
    )


def run_golden_vendor_cases(root: str | Path) -> GoldenRunSummary:
    """Backward-compatible alias retained for package exports."""
    return run_vendor_fixture_suite(root)
