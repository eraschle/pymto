"""Text assignment strategies for associating texts with pipes.

This module implements strategies for spatially assigning text elements
to pipe segments based on proximity and validity rules between shafts
or pipe junctions.
"""

import numpy as np

from pymto.protocols import IAssignmentStrategy

from ..models import AssignmentGroup, DxfText, Medium, ObjectData, Point3D


class SpatialTextAssigner(IAssignmentStrategy):
    """Assigns texts to pipes based on spatial proximity.

    This assigner uses spatial analysis to find the closest pipe
    for each text element, with constraints on maximum distance
    and validity between shafts/junctions.
    """

    def __init__(self, max_distance: float) -> None:
        """Initialize spatial text assigner.

        Parameters
        ----------
        max_distance : float, default 50.0
            Maximum distance for text-to-pipe assignment
        """
        self.max_distance = max_distance
        self.assigned_elements: dict[str, list[ObjectData]] = {}

    def texts_to_point_based(self, medium: Medium, groups: list[AssignmentGroup]) -> None:
        for config, group in zip(medium.config.point_based, groups, strict=True):
            elements, texts = group
            elements = elements.copy()
            elements = [elem for elem in elements if elem.is_point_based]
            for text in texts:
                closest_idx = self._find_closest_element(text.position, elements)
                if closest_idx < 0:
                    continue
                element = elements[closest_idx]
                element.assigned_text = text
                self._add_assignment(text, element)

            medium.point_data.add_assignment(config, elements)

    def _add_assignment(self, text: DxfText, element: ObjectData) -> None:
        """Add assignment to medium's point data."""
        if text.uuid not in self.assigned_elements:
            self.assigned_elements[text.uuid] = []
        self.assigned_elements[text.uuid].append(element)

    def _find_closest_element(self, text_position: Point3D, elements: list[ObjectData]) -> int:
        """Find the closest element position to a text position.

        Parameters
        ----------
        text_position : Point3D
            Position of the text element
        elements : list[ObjectData]
            List of elements to search in

        Returns
        -------
        tuple[int | None, float]
            (element_index, distance) of closest element position,
            or (None, inf) if no valid positions exist
        """
        min_distance = float("inf")
        closest_idx = -1

        for element_idx, element in enumerate(elements):
            if element.assigned_text is not None:
                continue
            distance = text_position.distance_2d(element.point)
            if distance >= self.max_distance:
                continue
            if distance < min_distance:
                min_distance = distance
                closest_idx = element_idx

        return closest_idx

    def texts_to_line_based(self, medium: Medium, groups: list[AssignmentGroup]) -> None:
        """Assign texts to pipes based on spatial proximity.

        Each text can be assigned to at most one pipe segment.
        Assignment is valid only if the text is close enough to
        the pipe and lies between pipe endpoints or junctions.

        Parameters
        ----------
        medium : Medium
            Medium containing pipe data and configuration
        groups : list[AssignmentGroup]
            List of assignment groups containing pipes and texts
        """
        for config, group in zip(medium.config.line_based, groups, strict=True):
            elements, texts = group
            elements = elements.copy()
            elements = [elem for elem in elements if elem.is_line_based]
            # Build spatial index for element segments (only for elements with points)
            element_segments = []
            segment_to_element = []

            for element_idx, element in enumerate(elements):
                if element.assigned_text:
                    continue
                if element.points and len(element.points) >= 2:
                    for idx in range(len(element.points) - 1):
                        start_point = element.points[idx]
                        end_point = element.points[idx + 1]

                        element_segments.append((start_point, end_point))
                        segment_to_element.append((element_idx, idx))

            for text in texts:
                closest_idx, _, distance = self._find_closest_element_segment(
                    text.position, element_segments, segment_to_element
                )

                if (
                    distance <= self.max_distance
                    and closest_idx is not None
                    and elements[closest_idx].assigned_text is None
                ):
                    elements[closest_idx].assigned_text = text
                    self._add_assignment(text, elements[closest_idx])

            medium.line_data.add_assignment(config, elements)

    def _find_closest_element_segment(
        self,
        text_position: Point3D,
        element_segments: list[tuple[Point3D, Point3D]],
        segment_to_element: list[tuple[int, int]],
    ) -> tuple[int | None, int | None, float]:
        """Find the closest element segment to a text position.

        Parameters
        ----------
        text_position : Point3D
            Position of the text element
        element_segments : list[tuple[Point3D, Point3D]]
            List of element segments as (start_point, end_point) tuples
        segment_to_element : list[tuple[int, int]]
            Mapping from segment index to (element_index, segment_index)

        Returns
        -------
        tuple[int | None, int | None, float]
            (element_index, segment_index, distance) of closest segment,
            or (None, None, inf) if no segments exist
        """
        min_distance = float("inf")
        closest_element_idx = -1
        closest_segment_idx = None

        for segment_idx, (start_point, end_point) in enumerate(element_segments):
            distance = self._point_to_line_distance(text_position, start_point, end_point)
            if distance >= self.max_distance:
                continue

            if distance < min_distance:
                min_distance = distance
                element_idx, seg_idx = segment_to_element[segment_idx]
                closest_element_idx = element_idx
                closest_segment_idx = seg_idx

        return closest_element_idx, closest_segment_idx, min_distance

    def _point_to_line_distance(self, point: Point3D, line_start: Point3D, line_end: Point3D) -> float:
        """Calculate the shortest distance from a point to a line segment.

        Parameters
        ----------
        point : Point3D
            The point to measure distance from
        line_start : Point3D
            Start point of the line segment
        line_end : Point3D
            End point of the line segment

        Returns
        -------
        float
            Shortest distance from point to line segment
        """
        # Convert to numpy arrays for easier calculation (using 2D projection)
        p = np.array([point.east, point.north])
        a = np.array([line_start.east, line_start.north])
        b = np.array([line_end.east, line_end.north])

        # Vector from line start to end
        ab = b - a

        # Vector from line start to point
        ap = p - a

        # If line segment has zero length, return distance to point
        ab_length_squared = np.dot(ab, ab)
        if ab_length_squared == 0:
            return float(np.linalg.norm(ap))

        # Project point onto line (parametric form)
        t = np.dot(ap, ab) / ab_length_squared

        # Clamp t to [0, 1] to stay within line segment
        t = max(0, min(1, t))

        # Find the closest point on the line segment
        closest_point = a + t * ab

        # Return distance from original point to closest point on segment
        return float(np.linalg.norm(p - closest_point))
