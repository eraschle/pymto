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

    def create_objects(self, configs: list[MediumConfig]) -> list[tuple[list[ObjectData], list[DxfText]]]:
        """Process a single assignment configuration.

        Parameters
        ----------
        config : AssignmentConfig
            Configuration for elements or lines

        Returns
        -------
        AssignmentData
            Processed assignment data with objects and texts
        """
        medium_entities = []
        for config in configs:
            group_assignment = self._process_assignment(config)
            medium_entities.append(group_assignment)
        return medium_entities

    def _process_assignment(self, config: MediumConfig) -> tuple[list[ObjectData], list[DxfText]]:
        if self.extractor is None or self.factory is None:
            raise RuntimeError("Processor components not initialized")

        geom_elem, text_elems = self.extractor.extract_entities(config)
        geometries = self._convert_to_objects(geom_elem, config)
        texts = self._convert_to_texts(text_elems, config)
        return geometries, texts

    def _convert_to_objects(self, entities: list[DXFEntity], config: MediumConfig) -> list[ObjectData]:
        if self.factory is None:
            raise RuntimeError("ObjectData factory not initialized")

        objects = []
        for entity in entities:
            obj_data = self.factory.create_from_entity(entity, config)
            if obj_data is not None:
                if not obj_data.dimension.has_valid_values():
                    obj_data.dimension.set_default_values(config=config)
                objects.append(obj_data)
            elif entity.dxftype() != "HATCH":
                log.warning(f"Failed to create ObjectData from {entity.dxftype()} entity")

        log.debug(f"Converted {len(objects)}/{len(entities)} entities to ObjectData")
        return objects

    def _convert_to_texts(self, entities: list[DXFEntity], config: MediumConfig) -> list[DxfText]:
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
        if not isinstance(entity, (Text | MText)):
            return None

        try:
            if isinstance(entity, MText):
                lines = entity.plain_text()
                text_content = "".join(lines)
            else:
                text_content = entity.dxf.text

            if not text_content:
                log.warning(f"Empty text content for {entity.dxftype()} entity")
                return None

            point = getattr(entity.dxf, "insert", (0, 0, 0))
            position = Point3D(east=point[0], north=point[1], altitude=0.0)

            return DxfText(
                uuid=str(entity.uuid),
                medium=config.medium,
                content=text_content,
                position=position,
                layer=getattr(entity.dxf, "layer", "0"),
            )

        except Exception as e:
            log.error(f"Failed to create DxfText from entity: {e}")
            return None
