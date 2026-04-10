from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


class UnwrapError(Exception):
    """Raised when a wrapper plugin cannot unwrap the provided bytes."""


class WrapperDecoder(Protocol):
    name: str
    version: str

    def match(self, blob: bytes) -> float:
        """Return confidence [0.0, 1.0] that this plugin can unwrap blob."""

    def unwrap(self, blob: bytes) -> bytes:
        """Return unwrapped bytes. Raise UnwrapError on decode failure."""


@dataclass
class PrefixBytesWrapperPlugin:
    """
    Example wrapper plugin for vendor formats that prepend a static prefix.
    This is a skeleton to copy when implementing real .dcx handlers.
    """

    name: str
    magic_prefix: bytes
    strip_bytes: int
    version: str = "0.1.0"

    def match(self, blob: bytes) -> float:
        if blob.startswith(self.magic_prefix):
            return 0.95
        return 0.0

    def unwrap(self, blob: bytes) -> bytes:
        if not blob.startswith(self.magic_prefix):
            raise UnwrapError("Prefix mismatch.")
        if len(blob) <= self.strip_bytes:
            raise UnwrapError("Payload too short after stripping prefix.")
        return blob[self.strip_bytes:]


@dataclass
class VendorDcXHeaderPlugin:
    """
    Skeleton vendor plugin for `.dcx` wrappers that prepend a fixed header.
    """

    name: str
    header: bytes
    version: str = "0.1.0"

    def match(self, blob: bytes) -> float:
        return 0.95 if blob.startswith(self.header) else 0.0

    def unwrap(self, blob: bytes) -> bytes:
        if not blob.startswith(self.header):
            raise UnwrapError("Header mismatch.")
        if len(blob) <= len(self.header):
            raise UnwrapError("Payload too short after stripping header.")
        return blob[len(self.header) :]

    @classmethod
    def from_fixture_file(cls, fixture_path: str | Path) -> "VendorDcXHeaderPlugin":
        """
        Build plugin settings from a simple key=value fixture config.
        Supported keys:
          - name
          - header_ascii
          - header_hex
        """
        path = Path(fixture_path)
        if not path.exists():
            raise ValueError(f"Fixture config not found: {fixture_path}")

        values: dict[str, str] = {}
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()

        if "header_hex" in values:
            header = bytes.fromhex(values["header_hex"])
        elif "header_ascii" in values:
            header = values["header_ascii"].encode("ascii")
        else:
            raise ValueError("Fixture config must define header_hex or header_ascii.")

        return cls(
            name=values.get("name", "vendor-dcx-skeleton"),
            header=header,
        )


@dataclass
class VendorFixtureWrapperPlugin:
    """
    Fixture-driven plugin for early reverse engineering loops.
    Configure it with expected prefix and strip bytes.
    """

    name: str
    fixture_prefix: bytes
    strip_prefix_bytes: int
    version: str = "0.1.0"

    def match(self, blob: bytes) -> float:
        return 0.9 if blob.startswith(self.fixture_prefix) else 0.0

    def unwrap(self, blob: bytes) -> bytes:
        if not blob.startswith(self.fixture_prefix):
            raise UnwrapError("Fixture prefix mismatch.")
        if len(blob) <= self.strip_prefix_bytes:
            raise UnwrapError("Payload too short after configured strip.")
        return blob[self.strip_prefix_bytes :]


def default_decoders() -> list[WrapperDecoder]:
    """
    Register default decoders here.
    """
    # Add real proprietary handlers here as they are implemented.
    # Example:
    # return [PrefixBytesWrapperPlugin(name="vendor-dcx", magic_prefix=b"DCX1", strip_bytes=4)]
    return []
