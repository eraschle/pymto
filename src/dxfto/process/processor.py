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

from ..config import ConfigurationHandler
from ..io import DXFEntityExtractor, DXFReader
from ..models import (
    AssingmentData,
    DxfText,
    Medium,
    MediumConfig,
    ObjectData,
    ObjectType,
    Point3D,
)
from ..protocols import (
    IAssignmentStrategy,
    IDimensionUpdater,
    IElevationUpdater,
    IExporter,
)
from .objectdata_factory import ObjectDataFactory

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

    def extract_mediums(self, reader: DXFReader) -> None:
        """Process all mediums by extracting and creating objects.

        Parameters
        ----------
        reader : DXFReader
            Reader instance to load and query DXF entities

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
            geom_elems, text_elems = self._get_assignment_data(
                medium_name, medium.config.point_based
            )
            medium.element_data.setup(medium_name, geom_elems, text_elems)
            geom_elems, text_elems = self._get_assignment_data(
                medium_name, medium.config.line_based
            )
            medium.line_data.setup(medium_name, geom_elems, text_elems)

    def _get_assignment_data(
        self, medium: str, configs: list[MediumConfig]
    ) -> tuple[list[list[ObjectData]], list[list[DxfText]]]:
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
        geometries: list[list[ObjectData]] = []
        texts: list[list[DxfText]] = []
        for config in configs:
            geom_elems, text_elems = self._process_assignment(medium, config)
            geometries.append(geom_elems)
            texts.append(text_elems)
        return geometries, texts

    def _process_assignment(
        self, medium: str, config: MediumConfig
    ) -> tuple[list[ObjectData], list[DxfText]]:
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
        geometries = self._convert_to_objects(
            medium, extracted["geometries"], config.object_type
        )
        texts = self._convert_to_texts(medium, extracted["texts"])
        return geometries, texts

    def _convert_to_objects(
        self, medium: str, entities: list[DXFEntity], object_type: ObjectType
    ) -> list[ObjectData]:
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
            obj_data = self.factory.create_from_entity(medium, entity, object_type)
            if obj_data is not None:
                objects.append(obj_data)
            else:
                log.warning(
                    f"Failed to create ObjectData from {entity.dxftype()} entity"
                )

        log.debug(f"Converted {len(objects)}/{len(entities)} entities to ObjectData")
        return objects

    def _convert_to_texts(
        self, medium: str, entities: list[DXFEntity]
    ) -> list[DxfText]:
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
            text_obj = self._create_text_from(medium, entity)
            if text_obj is not None:
                texts.append(text_obj)
            else:
                log.warning(f"Failed to create DxfText from {entity.dxftype()} entity")

        log.debug(f"Converted {len(texts)}/{len(entities)} entities to DxfText")
        return texts

    def _create_text_from(self, medium: str, entity: DXFEntity) -> DxfText | None:
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

            return DxfText(
                medium=medium,
                content=text_content,
                position=position,
                layer=layer,
                color=color,
            )

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

    def assign_texts_to(
        self,
        assigner: IAssignmentStrategy,
        handler: AssingmentData,
        configs: list[MediumConfig],
    ) -> None:
        for (elems, texts), config in zip(handler.data, configs, strict=True):
            assigned = assigner.texts_to_point_based(elems, texts)
            handler.add_assignment(config, assigned)

    def assign_texts_to_mediums(self, assigner: IAssignmentStrategy) -> None:
        """Assign extracted texts to mediums.

        Parameters
        ----------
        mediums : dict[str, Medium]
            Dictionary of mediums to assign texts to
        """
        for medium in self.mediums:
            # Assign texts to elements
            log.info(f"Assigning elements of {medium.name}")
            log.info("- Assigning texts to POINT BASED elements")
            self.assign_texts_to(
                assigner, medium.element_data, medium.config.point_based
            )

            log.info("- Assigning texts to LINE BASED elements")
            self.assign_texts_to(assigner, medium.line_data, medium.config.line_based)

    def update_dimensions(self, updater: IDimensionUpdater) -> None:
        """Update dimensions of elements and lines in mediums.

        Parameters
        ----------
        updater : IDimensionUpdater
            Dimension updater to apply to elements and lines
        """
        for medium in self.config.mediums.values():
            updater.update_elements(medium.element_data)
            updater.update_elements(medium.line_data)

    def _update_elevation(
        self, updater: IElevationUpdater, assigment: AssingmentData
    ) -> None:
        # Texts are assigned to elemtents and onbly the elements data are exported, which
        # means that texts are not updated here.
        for elements, _ in assigment.data:
            for element in elements:
                if element.points:
                    element.points = updater.update_elevation(element.points)
                if element.positions:
                    positions = updater.update_elevation(element.positions)
                    element.positions = tuple(positions)

    def update_points_elevation(self, updater: IElevationUpdater) -> None:
        """Assign extracted texts to mediums.

        Parameters
        ----------
        mediums : dict[str, Medium]
            Dictionary of mediums to assign texts to
        """
        for medium in self.mediums:
            self._update_elevation(updater, medium.element_data)
            self._update_elevation(updater, medium.line_data)

    def export_data(self, exporter: IExporter) -> None:
        """Export processed data using the provided exporter.

        Parameters
        ----------
        exporter : IExporter
            Exporter instance to use for exporting data
        """
        exporter.export_data(list(self.mediums))
