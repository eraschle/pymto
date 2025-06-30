import re

from dxfto.models import AssingmentData, ObjectData, RoundDimensions
from dxfto.protocols import IRevitFamilyNameUpdater


class RevitFamilyNameUpdater(IRevitFamilyNameUpdater):
    placeholder_pattern = re.compile(r"(\{.*?\})")

    def update_elements(self, assigment: AssingmentData) -> None:
        for elements, _ in assigment.assigned:
            self._update_dimensions(elements)

    def _update_dimensions(self, elements: list[ObjectData]) -> None:
        for element in elements:
            self._update_family_dimensions(element)
            self._update_family_type_dimensions(element)

    def _update_family_dimensions(self, element: ObjectData) -> None:
        placeholder = self.get_placeholder(element.family)
        if placeholder is None:
            return
        current = placeholder.group(0)
        dim_value = self._get_dimension_value(element)
        element.family = element.family.replace(current, dim_value)

    def _update_family_type_dimensions(self, element: ObjectData) -> None:
        placeholder = self.get_placeholder(element.family_type)
        if placeholder is None:
            return
        current = placeholder.group(0)
        dim_value = self._get_dimension_value(element)
        element.family_type = element.family_type.replace(current, dim_value)

    def _get_dimension_value(self, element: ObjectData) -> str:
        dimensions = element.dimensions
        if isinstance(dimensions, RoundDimensions):
            diameter = dimensions.diameter
            if element.is_line_based:
                diameter = diameter * 1000
                return f"{diameter:.0f}"
            diameter = diameter * 100
            return f"{diameter:.0f}"

        values = [dimensions.length, dimensions.width]
        values = sorted(values, reverse=True)
        return "x".join(f"{value:.2f}" for value in values)

    def get_placeholder(self, name: str) -> re.Match[str] | None:
        return self.placeholder_pattern.search(name)
