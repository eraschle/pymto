"""DXF processor orchestrating entity extraction and object creation.

This module provides the DXFProcessor class that coordinates between
DXF reading, entity extraction, and object creation following the
orchestrator pattern.
"""

import logging
from collections.abc import Iterable

from .config import ConfigurationHandler
from .models import Medium
from .protocols import (
    IAssignmentStrategy,
    IDimensionUpdater,
    IElevationUpdater,
    IExporter,
    IObjectCreator,
    IRevitFamilyNameUpdater,
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

    @property
    def mediums(self) -> Iterable[Medium]:
        """Get list of mediums from the configuration.

        Returns
        -------
        list[Medium]
            List of Medium objects defined in the configuration
        """
        return self.config.mediums.values()

    def extract_mediums(self, extractor: IObjectCreator) -> None:
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
        log.info(f"Processing {len(self.config.mediums)} mediums")
        for name, medium in self.config.mediums.items():
            log.debug(f"Processing medium: {name}")
            geom_elems, text_elems = extractor.create_objects(medium.config.point_based)
            medium.extracted_point.setup(name, geom_elems, text_elems)
            geom_elems, text_elems = extractor.create_objects(medium.config.line_based)
            medium.extracted_line.setup(name, geom_elems, text_elems)

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
            point_data = medium.extracted_point.extracted
            assigner.texts_to_point_based(medium, point_data)

            log.info("- Assigning texts to LINE BASED elements")
            line_data = medium.extracted_line.extracted
            assigner.texts_to_line_based(medium, line_data)

    def update_dimensions(self, updater: IDimensionUpdater) -> None:
        """Update dimensions of elements and lines in mediums.

        Parameters
        ----------
        updater : IDimensionUpdater
            Dimension updater to apply to elements and lines
        """
        for medium in self.config.mediums.values():
            updater.update_elements(medium.point_data)
            updater.update_elements(medium.line_data)

    def update_points_elevation(self, updater: IElevationUpdater) -> None:
        """Assign extracted texts to mediums.

        Parameters
        ----------
        updater : IElevationUpdater
            Elevation updater to apply to points in mediums
        """
        for medium in self.mediums:
            updater.update_elements(medium.point_data)
            updater.update_elements(medium.line_data)

    def update_family_and_types(self, updater: IRevitFamilyNameUpdater) -> None:
        """Update family and family types for all mediums.

        This method iterates through all mediums and updates their
        family and family types using the configured updater.
        """
        for medium in self.mediums:
            updater.update_elements(medium.point_data)
            updater.update_elements(medium.line_data)

    def export_data(self, exporter: IExporter) -> None:
        """Export processed data using the provided exporter.

        Parameters
        ----------
        exporter : IExporter
            Exporter instance to use for exporting data
        """
        exporter.export_data(list(self.mediums))
