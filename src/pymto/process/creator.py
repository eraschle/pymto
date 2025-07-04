#!/usr/bin/env python

import logging
from pathlib import Path

from ezdxf.entities.dxfentity import DXFEntity
from ezdxf.entities.mtext import MText
from ezdxf.entities.text import Text

from ..config import MediumConfig
from ..io import DXFReader
from ..models import DxfText, ObjectData, Point3D
from ..protocols import IObjectCreator
from .entity_extractor import DXFEntityExtractor
from .factory import ObjectDataFactory

log = logging.getLogger(__name__)


class MediumObjectCreator(IObjectCreator):
    def __init__(self, dxf_path: Path) -> None:
        """Initialize DXF extractor with the path to the DXF file.

        Parameters
        ----------
        dxf_path : Path
            Path to the DXF file to be processed
        """
        self.reader = DXFReader(dxf_path)
        self.reader.load_file()
        self.extractor = DXFEntityExtractor(self.reader)
        self.factory = ObjectDataFactory(self.reader.document)

    def create_objects(self, configs: list[MediumConfig]) -> tuple[list[list[ObjectData]], list[list[DxfText]]]:
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
        geometry_entities = []
        text_entities = []
        for config in configs:
            geom_elems, text_elems = self._process_assignment(config)
            geometry_entities.append(geom_elems)
            text_entities.append(text_elems)
        return geometry_entities, text_entities

    def _process_assignment(self, config: MediumConfig) -> tuple[list[ObjectData], list[DxfText]]:
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

        geom_elems, text_elems = self.extractor.extract_entities(config)
        geometries = self._convert_to_objects(geom_elems, config)
        texts = self._convert_to_texts(text_elems, config)
        return geometries, texts

    def _convert_to_objects(self, entities: list[DXFEntity], config: MediumConfig) -> list[ObjectData]:
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
            obj_data = self.factory.create_from_entity(entity, config)
            if obj_data is not None:
                if not obj_data.has_valid_dimensions:
                    obj_data.set_default_values(config)
                objects.append(obj_data)
            else:
                log.warning(f"Failed to create ObjectData from {entity.dxftype()} entity")

        log.debug(f"Converted {len(objects)}/{len(entities)} entities to ObjectData")
        return objects

    def _convert_to_texts(self, entities: list[DXFEntity], config: MediumConfig) -> list[DxfText]:
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
            text_obj = self._create_text_from(entity, config)
            if text_obj is not None:
                texts.append(text_obj)
            else:
                log.warning(f"Failed to create DxfText from {entity.dxftype()} entity")

        log.debug(f"Converted {len(texts)}/{len(entities)} entities to DxfText")
        return texts

    def _create_text_from(self, entity: DXFEntity, config: MediumConfig) -> DxfText | None:
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

            return DxfText(
                medium=config.medium,
                content=text_content,
                position=position,
                layer=getattr(entity.dxf, "layer", "0"),
                color=self._get_entity_color(entity),
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
