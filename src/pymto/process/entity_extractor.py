"""DXF entity extractor for separating entity extraction from object creation.

This module provides the DXFEntityExtractor class that handles the extraction
of raw DXF entities without creating ObjectData instances, following the
Single Responsibility Principle.
"""

import logging

from ezdxf.entities.dxfentity import DXFEntity

from ..io import DXFReader
from ..models import LayerData, MediumConfig
from ..process import entity_handler

log = logging.getLogger(__name__)


class DXFEntityExtractor:
    """Extracts raw DXF entities without creating ObjectData instances.

    This class focuses solely on entity extraction and classification,
    delegating object creation to the ObjectDataFactory.
    """

    def __init__(self, dxf_reader: DXFReader) -> None:
        """Initialize extractor with DXF reader.

        Parameters
        ----------
        dxf_reader : DXFReader
            DXF reader instance for querying entities
        """
        self.reader = dxf_reader

    def extract_entities(self, config: MediumConfig) -> tuple[list[DXFEntity], list[DXFEntity]]:
        """Extract entities categorized by type.

        Parameters
        ----------
        config : AssignmentConfig
            Configuration specifying which layers to process

        Returns
        -------
        dict[str, list[DXFEntity]]
            Dictionary with 'elements', 'lines', and 'texts' keys
        """
        geometries = self._extract_geometry_entities(config.layer_group.geometry)
        texts = self._extract_text_entities(config.layer_group.text)
        return geometries, texts

    def _extract_geometry_entities(self, geometry_layers: list[LayerData]) -> list[DXFEntity]:
        """Extract geometry entities from specified layers.

        Parameters
        ----------
        config : AssignmentConfig
            Configuration for geometry layers

        Returns
        -------
        list[DXFEntity]
            List of entities to be processed as lines
        """
        entities = []
        for layer_data in geometry_layers:
            for entity in self.reader.query_layer(layer_data):
                if entity_handler.is_text_entity(entity):
                    continue
                entities.append(entity)
        return entities

    def _extract_text_entities(self, text_layers: list[LayerData]) -> list[DXFEntity]:
        """Extract text entities from specified layers.

        Parameters
        ----------
        config : AssignmentConfig
            Configuration for text layers

        Returns
        -------
        list[DXFEntity]
            List of text entities
        """
        entities = []

        for layer_data in text_layers:
            for entity in self.reader.query_layer(layer_data):
                if not entity_handler.is_text_entity(entity):
                    continue
                entities.append(entity)
        return entities
