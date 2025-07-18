import re

from ..models import (
    AssignmentData,
    FormulaParameter,
    ObjectData,
    ObjectType,
    Point3D,
)
from ..protocols import IRevitFamilyNameUpdater


class RevitFamilyNameUpdater(IRevitFamilyNameUpdater):
    placeholder_pattern = re.compile(r"(\{.*?\})")

    def update_elements(self, assignment: AssignmentData) -> None:
        for elements, _ in assignment.assigned:
            self._update_dimensions(elements)
            self._update_elevations(elements)

    def _update_dimensions(self, elements: list[ObjectData]) -> None:
        for element in elements:
            self._update_family_dimensions(element)
            self._update_family_type_dimensions(element)

    def _update_elevations(self, elements: list[ObjectData]) -> None:
        for element in elements:
            if element.object_type != ObjectType.GUTTER:
                continue
            self._update_gutter_elevations(element)

    def _update_gutter_elevations(self, element: ObjectData) -> None:
        if not element.dimension.is_round:
            return
        diameter = element.dimension.diameter
        for idx, point in enumerate(element.points):
            new_point = Point3D(point.east, point.north, point.altitude - diameter)
            element.points[idx] = new_point

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
        dimension = element.dimension
        if dimension.is_round:
            diameter = dimension.diameter
            if element.is_line_based:
                diameter = diameter * 1000
                return f"{diameter:.0f}"
            diameter = diameter * 100
            return f"{diameter:.0f}"
        if dimension.is_rectangular:
            values = [dimension.width, dimension.depth]
            values = sorted(values, reverse=True)
            return "x".join(f"{value:.2f}" for value in values)
        raise ValueError(f"Unknown dimension type {element}")

    def get_placeholder(self, name: str) -> re.Match[str] | None:
        return self.placeholder_pattern.search(name)

    def add_parameters(self, assignment: AssignmentData) -> None:
        for elements, config in assignment.assigned:
            for element in elements:
                for parameter in config.parameters:
                    if isinstance(parameter, FormulaParameter):
                        parameter.calculate_value(element)
                    element.add_parameter(parameter)

    def remove_duplicate_point_based(self, assignment: AssignmentData) -> tuple[list[ObjectData], list[ObjectData]]:
        removed_objects = []
        medium_elements = []
        for idx, (elements, config) in enumerate(assignment.assigned):
            unique_points = set()
            unique_elements = []
            medium_elements.extend(elements)
            for element in elements:
                if element.point in unique_points:
                    removed_objects.append(element)
                    continue
                unique_points.add(element.point)
                unique_elements.append(element)
            assignment.assigned[idx] = (unique_elements, config)
        return medium_elements, removed_objects
