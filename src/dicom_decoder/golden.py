from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path

from .fixtures import VendorFixtureCase, load_vendor_fixture_cases
from .parser import parse_dicom
from .plugins import VendorDcXHeaderPlugin, WrapperDecoder
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
    return VendorDcXHeaderPlugin(name=case.plugin_name, header=case.header_bytes)


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
        decoder = plugin_map[case.plugin_name] if plugin_map and case.plugin_name in plugin_map else _build_decoder_for_case(case)
        parsed = parse_dicom(str(case.wrapped_path), decoders=[decoder])
        case_errors = list(parsed.errors)
        if case.expected_patient_id is not None:
            patient_id = parsed.tags.get("PatientID")
            if patient_id != case.expected_patient_id:
                case_errors.append(
                    f"Expected PatientID={case.expected_patient_id!r}, got {patient_id!r}."
                )
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
