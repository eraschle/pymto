"""Dimension extraction utilities for parsing dimension information from text.

This module provides functions to extract dimensional information from text strings,
supporting both round (circular) and rectangular dimensions with various formats
and unit specifications.
"""

from ...models import (
    AssignmentData,
    MediumConfig,
    ObjectData,
    Unit,
)
from . import dimension_extractor as dim
from .dimension_mapper import DimensionMapper


class ParameterUpdater:
    """Class to update dimensions in DXF entities."""

    def __init__(self, target_unit: Unit, dimension_mapper: DimensionMapper | None = None) -> None:
        self.target_unit = target_unit
        self.dim_mapper = dimension_mapper or DimensionMapper()
        self.do_convert_dimension: bool = True

    def update_elements(self, assignment: AssignmentData) -> None:
        """Update dimensions of all elements in the assignment data container.

        This method should iterate through all elements in the assignment
        and use the `update_dimension` method to update each element's

        Parameters
        ----------
        assignment : AssignmentData
            Assignment data containing elements and their assigned texts
        """
        for elements, config in assignment.assigned:
            for element in elements:
                self.update_parameters(element, config=config)
                self.update_dimension(element, config=config)

    def update_parameters(self, element: ObjectData, config: MediumConfig) -> None:
        """Update parameters in elements based on assigned text.

        This method is a placeholder for future parameter extraction logic.
        Currently, it does not perform any operations.

        Parameters
        ----------
        element : ObjectData
            Element to update parameters for
        config : MediumConfig
            Configuration containing default unit and other settings
        """
        if element.assigned_text is None:
            return

        text = element.assigned_text.content
        if not text or len(text.strip()) == 0:
            return

    def update_dimension(self, element: ObjectData, config: MediumConfig) -> None:
        """Update dimensions in elements based on assigned text with unit conversion.

        Default unit is used to interpret dimension values if no unit is specified in the text.

        Parameters
        ----------
        elements : list[ObjectData]
            List of elements to update dimensions for
        config : MediumConfig
            Configuration containing default unit and other settings
        """
        if element.assigned_text is None:
            return

        text = element.assigned_text.content
        if not text or len(text.strip()) == 0:
            return

        rect_result = dim.extract_rectangular(text)
        if rect_result is not None and not element.dimension.is_round:
            (width, depth), unit = rect_result

            if self.do_convert_dimension:
                if unit == Unit.UNKNOWN:
                    unit = config.default_unit
                width = dim.convert_to_unit(width, unit, self.target_unit)
                depth = dim.convert_to_unit(depth, unit, self.target_unit)

            width, depth = sorted([width, depth])
            element.dimension.width = self.dim_mapper.round_dimension(width, round_to=10)
            element.dimension.depth = self.dim_mapper.round_dimension(depth, round_to=10)
            element.dimension.dimensions_updated()

        round_result = dim.extract_round(text)
        if round_result is not None and not element.dimension.is_rectangular:
            diameter, unit = round_result

            # Convert to target unit
            if self.do_convert_dimension:
                if unit == Unit.UNKNOWN:
                    unit = config.default_unit
                diameter = self.dim_mapper.snap_dimension(diameter, element.object_type)
                diameter = dim.convert_to_unit(diameter, unit, self.target_unit)
            element.dimension.diameter = self.dim_mapper.round_dimension(diameter, round_to=5)
            element.dimension.dimensions_updated()
