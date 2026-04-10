"""DICOM decoder package."""

from .parser import parse_dicom
from .batch import parse_many

__all__ = ["parse_dicom", "parse_many"]

