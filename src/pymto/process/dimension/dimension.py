"""Dimension extraction utilities for parsing dimension information from text.

This module provides functions to extract dimensional information from text strings,
supporting both round (circular) and rectangular dimensions with various formats
and unit specifications.
"""

from ...models import (
    AssingmentData,
    MediumConfig,
    ObjectData,
    RectangularDimensions,
    RoundDimensions,
)
from . import dimension_extractor as dim
from .dimension_mapper import DimensionMapper


class DimensionUpdater:
    """Class to update dimensions in DXF entities."""

    def __init__(self, target_unit: str, dimension_mapper: DimensionMapper) -> None:
        self.target_unit = target_unit
        self.dim_mapper = dimension_mapper
        self.do_convert_dimension: bool = True

    def update_elements(self, assigment: AssingmentData) -> None:
        """Update dimensions of all elements in the assignment data container.

        This method should iterate through all elements in the assignment
        and use the `update_dimension` method to update each element's

        Parameters
        ----------
        assignment : AssingmentData
            Assignment data containing elements and their assigned texts
        """
        for elements, config in assigment.assigned:
            for element in elements:
                self.update_dimension(element, config=config)
                self.update_parameters(element)

    def round_parameter_values(self, assigment: AssingmentData) -> None:
        """Round parameters of all dimensions of a single element.

        Parameters
        ----------
        assignment : AssingmentData
            Assignment data containing elements and their assigned texts
        """
        for elements, _ in assigment.assigned:
            for element in elements:
                self.update_parameters(element)

    def update_dimension(self, element: ObjectData, config: MediumConfig) -> None:
        """Update dimensions in elements based on assigned text with unit conversion.

        Default unit is used to interpret dimension values if no unit is specified in the text.

        Parameters
        ----------
        elements : list[ObjectData]
            List of elements to update dimensions for
        default_unit : str
            Default unit for dimension values ('mm', 'cm', 'm')
        """
        if element.assigned_text is None:
            return

        text = element.assigned_text.content
        if not text or len(text.strip()) == 0:
            return

        if isinstance(element.dimensions, RectangularDimensions):
            rect_result = dim.extract_rectangular(text)
            if rect_result is None:
                return
            (length, width), unit = rect_result

            if self.do_convert_dimension:
                if unit is None:
                    unit = config.default_unit
                length = dim.convert_to_unit(length, unit, self.target_unit)
                width = dim.convert_to_unit(width, unit, self.target_unit)

            length, width = sorted([length, width])
            element.dimensions.length = self.dim_mapper.round_dimension(length)
            element.dimensions.width = self.dim_mapper.round_dimension(width)

        elif isinstance(element.dimensions, RoundDimensions):
            round_result = dim.extract_round(text)
            if round_result is None:
                return
            diameter, unit = round_result

            # Convert to target unit
            if self.do_convert_dimension:
                if unit is None:
                    unit = config.default_unit
                diameter = self.dim_mapper.snap_dimension(diameter, element.object_type)
                diameter = dim.convert_to_unit(diameter, unit, self.target_unit)
            element.dimensions.diameter = self.dim_mapper.round_dimension(diameter)

    def update_parameters(self, element: ObjectData) -> None:
        """Update prameters of the element by rounding the values.

        Parameters
        ----------
        element : ObjectData
            The element whose parameters are to be updated
        """
        for param in element.get_parameters():
            if not isinstance(param.value, (float | int)):
                continue
            param.value = self.dim_mapper.round_dimension(param.value)
