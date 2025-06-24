"""DXF entity extractor for separating entity extraction from object creation.

This module provides the DXFEntityExtractor class that handles the extraction
of raw DXF entities without creating ObjectData instances, following the
Single Responsibility Principle.
"""

import logging

from ezdxf.entities.dxfentity import DXFEntity

from ..models import AssignmentConfig
from ..process.entity_handler import is_element_entity

log = logging.getLogger(__name__)


class DXFEntityExtractor:
    """Extracts raw DXF entities without creating ObjectData instances.

    This class focuses solely on entity extraction and classification,
    delegating object creation to the ObjectDataFactory.
    """

    def __init__(self, dxf_reader):
        """Initialize extractor with DXF reader.

        Parameters
        ----------
        dxf_reader : DXFReader
            DXF reader instance for querying entities
        """
        self.reader = dxf_reader

    def extract_entities(self, config: AssignmentConfig) -> dict[str, list[DXFEntity]]:
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
        return {
            "elements": self._extract_element_entities(config),
            "lines": self._extract_line_entities(config),
            "texts": self._extract_text_entities(config),
        }

    def _extract_element_entities(self, config: AssignmentConfig) -> list[DXFEntity]:
        """Extract entities that should be processed as elements (shafts, etc.).

        Parameters
        ----------
        config : AssignmentConfig
            Configuration for geometry layers

        Returns
        -------
        list[DXFEntity]
            List of entities to be processed as elements
        """
        entities = []

        for entity in self.reader.query_entities(config.geometry):
            if is_element_entity(entity):
                entities.append(entity)

        log.debug(f"Extracted {len(entities)} element entities")
        return entities

    def _extract_line_entities(self, config: AssignmentConfig) -> list[DXFEntity]:
        """Extract entities that should be processed as lines (pipes, etc.).

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

        for entity in self.reader.query_entities(config.geometry):
            if not is_element_entity(entity):
                entities.append(entity)

        log.debug(f"Extracted {len(entities)} line entities")
        return entities

    def _extract_text_entities(self, config: AssignmentConfig) -> list[DXFEntity]:
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

        for entity in self.reader.query_entities(config.text):
            if entity.dxftype() in ("TEXT", "MTEXT"):
                entities.append(entity)

        log.debug(f"Extracted {len(entities)} text entities")
        return entities
