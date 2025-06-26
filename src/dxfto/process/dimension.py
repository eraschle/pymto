"""Dimension extraction utilities for parsing dimension information from text.

This module provides functions to extract dimensional information from text strings,
supporting both round (circular) and rectangular dimensions with various formats
and unit specifications.
"""

from ..models import (
    MediumConfig,
    ObjectData,
    RectangularDimensions,
    RoundDimensions,
)
from . import dimension_extractor as dim


class DimensionUpdater:
    """Class to update dimensions in DXF entities."""

    def __init__(self, target_unit: str) -> None:
        self.target_unit = target_unit
        self.do_convert_dimension: bool = True

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
            (width, height), unit = rect_result

            if self.do_convert_dimension:
                # Convert to target unit
                if unit is None:
                    unit = config.default_unit
                width = dim.convert_to_unit(width, unit, self.target_unit)
                height = dim.convert_to_unit(height, unit, self.target_unit)

            length, width = sorted([width, height])
            element.dimensions.length = length
            element.dimensions.width = width

        elif isinstance(element.dimensions, RoundDimensions):
            round_result = dim.extract_round(text)
            if round_result is None:
                return
            diameter, unit = round_result

            # Convert to target unit
            if self.do_convert_dimension:
                if unit is None:
                    unit = config.default_unit
                diameter = dim.convert_to_unit(diameter, unit, self.target_unit)
            element.dimensions.diameter = diameter
