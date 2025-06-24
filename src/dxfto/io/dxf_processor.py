"""DXF processor orchestrating entity extraction and object creation.

This module provides the DXFProcessor class that coordinates between
DXF reading, entity extraction, and object creation following the
orchestrator pattern.
"""

import logging
from pathlib import Path
from typing import Any

from ezdxf.entities.dxfentity import DXFEntity
from ezdxf.entities.mtext import MText
from ezdxf.entities.text import Text

from ..models import (
    AssignmentConfig,
    AssingmentData,
    DxfText,
    Medium,
    ObjectData,
    Point3D,
)
from ..process.objectdata_factory import ObjectDataFactory
from .dxf_reader_clean import DXFReader
from .entity_extractor import DXFEntityExtractor

log = logging.getLogger(__name__)


class DXFProcessor:
    """Orchestrates DXF processing from file loading to object creation.

    This class coordinates the entire DXF processing pipeline:
    1. File loading (DXFReader)
    2. Entity extraction (DXFEntityExtractor)
    3. Object creation (ObjectDataFactory)
    """

    def __init__(self, dxf_path: Path) -> None:
        """Initialize DXF processor with file path.

        Parameters
        ----------
        dxf_path : Path
            Path to the DXF file to process
        """
        self.dxf_path = dxf_path
        self.reader = DXFReader(dxf_path)
        self.extractor: DXFEntityExtractor | None = None
        self.factory: ObjectDataFactory | None = None

    def load_file(self) -> None:
        """Load DXF file and initialize processing components.

        Raises
        ------
        FileNotFoundError
            If DXF file does not exist
        DXFError
            If DXF file cannot be parsed
        """
        self.reader.load_file()
        self.extractor = DXFEntityExtractor(self.reader)

        # Initialize factory with loaded document
        if self.reader.document is not None:
            self.factory = ObjectDataFactory(self.reader.document)
            log.info("DXF processor initialized successfully")
        else:
            raise RuntimeError("Failed to load DXF document")

    def process_mediums(self, mediums: dict[str, Medium]) -> None:
        """Process all mediums by extracting and creating objects.

        Parameters
        ----------
        mediums : dict[str, Medium]
            Dictionary of mediums to process

        Raises
        ------
        RuntimeError
            If processor is not initialized
        """
        if not self.is_initialized():
            raise RuntimeError("DXF processor not initialized. Call load_file() first.")

        log.info(f"Processing {len(mediums)} mediums")

        for medium_name, medium in mediums.items():
            log.debug(f"Processing medium: {medium_name}")

            # Process elements
            medium.element_data = self._process_assignment(medium.elements)

            # Process lines
            medium.line_data = self._process_assignment(medium.lines)

            log.info(
                f"Medium '{medium_name}': {len(medium.element_data.elements)} elements, "
                f"{len(medium.line_data.elements)} lines, "
                f"{len(medium.element_data.texts)} texts"
            )

    def _process_assignment(self, config: AssignmentConfig) -> AssingmentData:
        """Process a single assignment configuration.

        Parameters
        ----------
        config : AssignmentConfig
            Configuration for elements or lines

        Returns
        -------
        AssingmentData
            Processed assignment data with objects and texts
        """
        if self.extractor is None or self.factory is None:
            raise RuntimeError("Processor components not initialized")

        # Extract raw entities
        extracted = self.extractor.extract_entities(config)

        # Convert entities to objects
        elements = self._convert_entities_to_objects(
            extracted["elements"] + extracted["lines"]  # Combine both types
        )

        # Convert text entities to DxfText objects
        texts = self._convert_entities_to_texts(extracted["texts"])

        return AssingmentData(elements=elements, texts=texts)

    def _convert_entities_to_objects(self, entities: list[DXFEntity]) -> list[ObjectData]:
        """Convert DXF entities to ObjectData using the factory.

        Parameters
        ----------
        entities : list[DXFEntity]
            List of DXF entities to convert

        Returns
        -------
        list[ObjectData]
            List of created ObjectData instances
        """
        if self.factory is None:
            raise RuntimeError("ObjectData factory not initialized")

        objects = []
        for entity in entities:
            obj_data = self.factory.create_from_entity(entity)
            if obj_data is not None:
                objects.append(obj_data)
            else:
                log.warning(f"Failed to create ObjectData from {entity.dxftype()} entity")

        log.debug(f"Converted {len(objects)}/{len(entities)} entities to ObjectData")
        return objects

    def _convert_entities_to_texts(self, entities: list[DXFEntity]) -> list[DxfText]:
        """Convert DXF text entities to DxfText objects.

        Parameters
        ----------
        entities : list[DXFEntity]
            List of text entities to convert

        Returns
        -------
        list[DxfText]
            List of created DxfText instances
        """
        texts = []
        for entity in entities:
            text_obj = self._create_text_from_entity(entity)
            if text_obj is not None:
                texts.append(text_obj)
            else:
                log.warning(f"Failed to create DxfText from {entity.dxftype()} entity")

        log.debug(f"Converted {len(texts)}/{len(entities)} entities to DxfText")
        return texts

    def _create_text_from_entity(self, entity: DXFEntity) -> DxfText | None:
        """Create a DxfText object from a DXF text entity.

        Parameters
        ----------
        entity : DXFEntity
            Text entity to convert

        Returns
        -------
        DxfText | None
            Created DxfText object or None if conversion failed
        """
        if not isinstance(entity, (Text | MText)):
            return None

        try:
            # Extract text content
            if isinstance(entity, MText):
                lines = entity.plain_text()
                text_content = "".join(lines)
            else:
                text_content = entity.dxf.text

            if not text_content:
                log.warning(f"Empty text content for {entity.dxftype()} entity")
                return None

            # Extract position
            point = getattr(entity.dxf, "insert", (0, 0, 0))
            position = Point3D(east=point[0], north=point[1], altitude=0.0)

            # Extract layer and color
            layer = getattr(entity.dxf, "layer", "0")
            color = self._get_entity_color(entity)

            return DxfText(content=text_content, position=position, layer=layer, color=color)

        except Exception as e:
            log.error(f"Failed to create DxfText from entity: {e}")
            return None

    def _get_entity_color(self, entity: DXFEntity) -> tuple[int, int, int]:
        """Get RGB color of a DXF entity.

        Parameters
        ----------
        entity : DXFEntity
            Entity to get color from

        Returns
        -------
        tuple[int, int, int]
            RGB color values
        """
        try:
            color_index = getattr(entity.dxf, "color", 7)

            # Simple AutoCAD color index to RGB mapping
            color_map = {
                1: (255, 0, 0),  # Red
                2: (255, 255, 0),  # Yellow
                3: (0, 255, 0),  # Green
                4: (0, 255, 255),  # Cyan
                5: (0, 0, 255),  # Blue
                6: (255, 0, 255),  # Magenta
                7: (0, 0, 0),  # Black/White
            }

            return color_map.get(color_index, (0, 0, 0))

        except Exception:
            return (0, 0, 0)

    def is_initialized(self) -> bool:
        """Check if processor is fully initialized.

        Returns
        -------
        bool
            True if all components are initialized
        """
        return self.reader.is_loaded() and self.extractor is not None and self.factory is not None

    def get_statistics(self) -> dict[str, Any]:
        """Get processing statistics.

        Returns
        -------
        dict[str, int]
            Dictionary with processing statistics

        Raises
        ------
        RuntimeError
            If processor is not initialized
        """
        if not self.reader.is_loaded():
            raise RuntimeError("DXF file not loaded")

        return {
            "total_entities": self.reader.get_entity_count(),
            "available_layers": len(self.reader.get_layer_names()),
            "layer_names": self.reader.get_layer_names(),
        }
