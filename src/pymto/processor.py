"""DXF processor orchestrating entity extraction and object creation.

This module provides the DXFProcessor class that coordinates between
DXF reading, entity extraction, and object creation following the
orchestrator pattern.
"""

import logging
from collections.abc import Iterable

from pymto.analyze import (
    PipelineAdjustment,
    PipelineGradientAdjuster,
)

from .config import ConfigurationHandler
from .models import Medium, ObjectData
from .protocols import (
    IAssignmentStrategy,
    IDimensionCalculator,
    IElevationUpdater,
    IExporter,
    IObjectCreator,
    IParameterUpdater,
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
            point_groups = extractor.create_objects(medium.config.point_based)
            medium.extracted_point.setup(name, point_groups)

            line_groups = extractor.create_objects(medium.config.line_based)
            medium.extracted_line.setup(name, line_groups)

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

    def update_parameters(self, updater: IParameterUpdater) -> None:
        """Update dimensions of elements and lines in mediums.

        Parameters
        ----------
        updater : IDimensionUpdater
            Dimension updater to apply to elements and lines
        """
        for medium in self.mediums:
            updater.update_elements(medium.point_data)
            updater.update_elements(medium.line_data)

    def adjustment_pipe_gradient(self, gradient: PipelineGradientAdjuster) -> list[PipelineAdjustment]:
        """Adjust elements in mediums based on compatibility strategy.

        Parameters
        ----------
        updater : MediumConfig
            Configuration for the medium to adjust elements"""
        elements = []
        for medium in self.mediums:
            elements.extend(medium.get_assignment_elements())

        asjustment_result = []
        reports = gradient.adjust_gradients_by(elements=elements)
        asjustment_result.extend(reports)
        return asjustment_result

    def calculate_dimensions(self, calculators: list[IDimensionCalculator]) -> None:
        """Add configuration parameters to all mediums.

        Parameters
        ----------
        updater : IRevitFamilyNameUpdater
            Revit family name updater to apply configuration parameters
        """
        all_elements = []
        for medium in self.mediums:
            all_elements.extend(medium.get_assignment_elements())
        for calculator in calculators:
            calculator.calculate_dimension(all_elements)

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

        Parameters
        ----------
        updater : IRevitFamilyNameUpdater
            Revit family name updater to apply to mediums
        """
        for medium in self.mediums:
            updater.update_elements(medium.point_data)
            updater.update_elements(medium.line_data)

    def add_config_parameters(self, updater: IRevitFamilyNameUpdater) -> None:
        """Add configuration parameters to all mediums.

        Parameters
        ----------
        updater : IRevitFamilyNameUpdater
            Revit family name updater to apply configuration parameters
        """
        for medium in self.mediums:
            updater.add_parameters(medium.point_data)
            updater.add_parameters(medium.line_data)

    def remove_duplicate_point_objects(
        self, updater: IRevitFamilyNameUpdater
    ) -> dict[str, tuple[list[ObjectData], list[ObjectData]]]:
        """Add configuration parameters to all mediums.

        Parameters
        ----------
        updater : IRevitFamilyNameUpdater
            Revit family name updater to apply configuration parameters
        """
        removed_objects = {}
        for medium in self.mediums:
            original, removed = updater.remove_duplicate_point_based(medium.point_data)
            if len(removed) == 0:
                continue
            removed_objects[medium.name] = (original, removed)
        return removed_objects

    def export_data(self, exporter: IExporter) -> None:
        """Export processed data using the provided exporter.

        Parameters
        ----------
        exporter : IExporter
            Exporter instance to use for exporting data
        """
        exporter.export_data(list(self.mediums))
