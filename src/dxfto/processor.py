"""DXF processor orchestrating entity extraction and object creation.

This module provides the DXFProcessor class that coordinates between
DXF reading, entity extraction, and object creation following the
orchestrator pattern.
"""

import logging
from collections.abc import Iterable

from ezdxf.entities.dxfentity import DXFEntity
from ezdxf.entities.mtext import MText
from ezdxf.entities.text import Text

from .config import ConfigurationHandler
from .io import DXFEntityExtractor, DXFReader
from .models import AssingmentData, DxfText, Medium, MediumConfig, ObjectData, Point3D
from .process.objectdata_factory import ObjectDataFactory
from .protocols import (
    IAssignmentStrategy,
    IDimensionUpdater,
    IElevationUpdater,
    IExporter,
)

log = logging.getLogger(__name__)


class DXFProcessor:
    """Orchestrates DXF processing from file loading to object creation.

    This class coordinates the entire DXF processing pipeline:
    1. File loading (DXFReader)
    2. Entity extraction (DXFEntityExtractor)
    3. Object creation (ObjectDataFactory)
    """

    def __init__(self, config: ConfigurationHandler) -> None:
        """Initialize DXF processor with file path.

        Parameters
        ----------
        dxf_path : Path
            Path to the DXF file to process
        """
        self.config = config
        self.extractor: DXFEntityExtractor | None = None
        self.factory: ObjectDataFactory | None = None

    @property
    def mediums(self) -> Iterable[Medium]:
        """Get list of mediums from the configuration.

        Returns
        -------
        list[Medium]
            List of Medium objects defined in the configuration
        """
        return self.config.mediums.values()

    def element_count(self) -> tuple[int, int]:
        """Get total number of elements and texts of point based mediums.

        Returns
        -------
        tuple[int, int]
            Total number of elements and texts in the DXF file
        """
        element_count = 0
        text_count = 0
        for medium in self.mediums:
            element_count += len(medium.element_data.elements)
            text_count += len(medium.element_data.texts)
        return element_count, text_count

    def line_count(self) -> tuple[int, int]:
        """Get total number of elements and texts of line based mediums.

        Returns
        -------
        tuple[int, int]
            Total number of elements and texts in the DXF file
        """
        element_count = 0
        text_count = 0
        for medium in self.mediums:
            element_count += len(medium.line_data.elements)
            text_count += len(medium.line_data.texts)
        return element_count, text_count

    def extract_mediums(self, reader: DXFReader) -> None:
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
        if reader.document is None:
            raise RuntimeError("DXF document not loaded. Call load_file() first.")
        self.extractor = DXFEntityExtractor(reader)
        self.factory = ObjectDataFactory(reader.document)
        log.info("DXF processor initialized successfully")

        log.info(f"Processing {len(self.config.mediums)} mediums")

        for medium_name, medium in self.config.mediums.items():
            log.debug(f"Processing medium: {medium_name}")

            medium.element_data = self._process_assignment(medium.elements)
            medium.line_data = self._process_assignment(medium.lines)

            log.info(
                f"Medium '{medium_name}': {len(medium.element_data.elements)} elements, "
                f"{len(medium.line_data.elements)} lines, "
            )

    def _process_assignment(self, config: MediumConfig) -> AssingmentData:
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

        extracted = self.extractor.extract_entities(config)
        geometries = self._convert_entities_to_objects(extracted["geometries"], config)
        texts = self._convert_entities_to_texts(extracted["texts"])

        return AssingmentData(elements=geometries, texts=texts)

    def _convert_entities_to_objects(self, entities: list[DXFEntity], config: MediumConfig) -> list[ObjectData]:
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
            obj_data = self.factory.create_from_entity(entity, config.default_shape)
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

    def assign_texts_to_mediums(self, assigner: IAssignmentStrategy) -> None:
        """Assign extracted texts to mediums.

        Parameters
        ----------
        mediums : dict[str, Medium]
            Dictionary of mediums to assign texts to
        """
        for medium, medium_data in self.config.mediums.items():
            # Assign texts to elements
            log.info(f"Assigning texts to elements of medium: {medium}")
            element_data = medium_data.element_data
            assigned_elements = assigner.texts_to_point_based(
                element_data.elements,
                element_data.texts,
            )
            element_data.elements.clear()
            element_data.elements.extend(assigned_elements)

            # Assign texts to lines (pipes)
            line_data = medium_data.element_data
            assigned_lines = assigner.texts_to_line_based(line_data.elements, line_data.texts)
            line_data.elements.clear()
            line_data.elements.extend(assigned_lines)

    def update_dimensions(self, updater: IDimensionUpdater) -> None:
        """Update dimensions of elements and lines in mediums.

        Parameters
        ----------
        updater : IDimensionUpdater
            Dimension updater to apply to elements and lines
        """
        for medium in self.config.mediums.values():
            for element in medium.element_data.elements:
                updater.update_dimension(element, config=medium.elements)
            for line in medium.line_data.elements:
                updater.update_dimension(line, config=medium.lines)

    def update_points_elevation(self, updater: IElevationUpdater) -> None:
        """Assign extracted texts to mediums.

        Parameters
        ----------
        mediums : dict[str, Medium]
            Dictionary of mediums to assign texts to
        """
        for medium in self.config.mediums.values():
            # Update elements points/positions
            for element in medium.element_data.elements:
                if element.points:
                    element.points = updater.update_elevation(element.points)
                if element.positions:
                    element.positions = updater.update_elevation(element.positions)

            for element in medium.line_data.elements:
                if element.points:
                    element.points = updater.update_elevation(element.points)
                if element.positions:
                    element.positions = updater.update_elevation(element.positions)

            # Update text positions
            for text in medium.element_data.texts:
                text.position = updater.update_elevation([text.position])[0]

            for text in medium.line_data.texts:
                text.position = updater.update_elevation([text.position])[0]

    def export_data(self, exporter: IExporter) -> None:
        """Export processed data using the provided exporter.

        Parameters
        ----------
        exporter : IExporter
            Exporter instance to use for exporting data
        """
        exporter.export_data(list(self.mediums))
