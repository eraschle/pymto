"""DXF I/O package with clean separation of concerns.

This package provides:
- DXFReader: File I/O and entity querying
- DXFEntityExtractor: Raw entity extraction
- ObjectDataFactory: Object creation from entities
- DXFProcessor: Orchestrator for the complete pipeline
"""

from .dxf_processor import DXFProcessor
from .dxf_reader import DXFReader as LegacyDXFReader
from .dxf_reader_clean import DXFReader
from .entity_extractor import DXFEntityExtractor

__all__ = [
    "DXFProcessor",
    "DXFReader",
    "DXFEntityExtractor",
    "LegacyDXFReader",
]
