from __future__ import annotations

from dataclasses import dataclass
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


def default_decoders() -> list[WrapperDecoder]:
    """
    Register default decoders here.
    """
    # Add real proprietary handlers here as they are implemented.
    # Example:
    # return [PrefixBytesWrapperPlugin(name="vendor-dcx", magic_prefix=b"DCX1", strip_bytes=4)]
    return []
