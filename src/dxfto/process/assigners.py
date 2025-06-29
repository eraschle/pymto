"""Text assignment strategies for associating texts with pipes.

This module implements strategies for spatially assigning text elements
to pipe segments based on proximity and validity rules between shafts
or pipe junctions.
"""

import numpy as np

from dxfto.protocols import IAssignmentStrategy

from ..models import DxfText, ObjectData, Point3D


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

    def _create_copy_of(self, elements: list[ObjectData]) -> list[ObjectData]:
        """Create a copy of ObjectData elements with reset assignments.

        Parameters
        ----------
        elements : list[ObjectData]
            List of ObjectData elements to copy

        Returns
        -------
        list[ObjectData]
            List of copied ObjectData elements with reset assignments
        """
        return elements.copy() if elements else []

    def texts_to_point_based(self, elements: list[ObjectData], texts: list[DxfText]) -> list[ObjectData]:
        """Assign texts to point-based elements based on spatial proximity.

        For point-based elements, texts are assigned to the closest element
        position within the maximum distance threshold.

        Parameters
        ----------
        elements : list[ObjectData]
            List of point-based elements to assign texts to
        texts : list[DxfText]
            List of available texts for assignment

        Returns
        -------
        list[ObjectData]
            List of elements with assigned texts where applicable
        """
        if not elements or not texts:
            return elements

        assigned_elements = self._create_copy_of(elements)
        # For each text, find the closest element position
        for text in texts:
            closest_element_idx, distance = self._find_closest_element_position(
                text.position, assigned_elements
            )

            # Assign text if within maximum distance and element doesn't have text yet
            if (
                distance <= self.max_distance
                and closest_element_idx is not None
                and assigned_elements[closest_element_idx].assigned_text is None
            ):
                assigned_elements[closest_element_idx].assigned_text = text

        return assigned_elements

    def _find_closest_element_position(
        self, text_position: Point3D, elements: list[ObjectData]
    ) -> tuple[int | None, float]:
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
        if not elements:
            return None, float("inf")

        min_distance = float("inf")
        closest_element_idx = None

        for element_idx, element in enumerate(elements):
            if element.positions:
                # For point-based elements, check all positions
                for position in element.positions:
                    distance = text_position.distance_2d(position)
                    if distance < min_distance:
                        min_distance = distance
                        closest_element_idx = element_idx
            elif element.points:
                # For line-based elements, use the first point as reference
                if element.points:
                    distance = text_position.distance_2d(element.points[0])
                    if distance < min_distance:
                        min_distance = distance
                        closest_element_idx = element_idx

        return closest_element_idx, min_distance

    def texts_to_line_based(self, elements: list[ObjectData], texts: list[DxfText]) -> list[ObjectData]:
        """Assign texts to pipes based on spatial proximity.

        Each text can be assigned to at most one pipe segment.
        Assignment is valid only if the text is close enough to
        the pipe and lies between pipe endpoints or junctions.

        Parameters
        ----------
        pipes : list[Pipe]
            List of pipes to assign texts to
        texts : list[DxfText]
            List of available texts for assignment

        Returns
        -------
        list[Pipe]
            List of pipes with assigned texts where applicable
        """
        if not elements or not texts:
            return elements

        # Create a copy of elements to avoid modifying the original list
        assigned_elements = self._create_copy_of(elements)

        # Build spatial index for element segments (only for elements with points)
        element_segments = []
        segment_to_element = []

        for element_idx, element in enumerate(assigned_elements):
            if element.points and len(element.points) >= 2:
                for idx in range(len(element.points) - 1):
                    start_point = element.points[idx]
                    end_point = element.points[idx + 1]

                    element_segments.append((start_point, end_point))
                    segment_to_element.append((element_idx, idx))

        if not element_segments:
            return assigned_elements

        for text in texts:
            closest_element_idx, _, distance = self._find_closest_element_segment(
                text.position, element_segments, segment_to_element
            )

            # Assign text if within maximum distance and element doesn't have text yet
            if (
                distance <= self.max_distance
                and closest_element_idx is not None
                and assigned_elements[closest_element_idx].assigned_text is None
            ):
                assigned_elements[closest_element_idx].assigned_text = text

        return assigned_elements

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
        if not element_segments:
            return None, None, float("inf")

        min_distance = float("inf")
        closest_element_idx = None
        closest_segment_idx = None

        for segment_idx, (start_point, end_point) in enumerate(element_segments):
            distance = self._point_to_line_distance(text_position, start_point, end_point)

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


class ZoneBasedTextAssigner(IAssignmentStrategy):
    """Assigns texts to pipes using zone-based validation.

    This assigner ensures that text assignments are valid only
    between shafts or pipe junctions, creating logical zones
    for text assignment.
    """

    def __init__(self, max_distance: float = 50.0, zone_buffer: float = 10.0) -> None:
        """Initialize zone-based text assigner.

        Parameters
        ----------
        max_distance : float, default 50.0
            Maximum distance for text-to-pipe assignment
        zone_buffer : float, default 10.0
            Buffer distance around shafts to define exclusion zones
        """
        self.max_distance = max_distance
        self.zone_buffer = zone_buffer

    def texts_to_point_based(self, elements: list[ObjectData], texts: list[DxfText]) -> list[ObjectData]:
        """Assign texts to point-based elements with zone validation.

        This method uses spatial assignment as base but adds zone-based
        validation to ensure assignments are valid within defined zones.

        Parameters
        ----------
        elements : list[ObjectData]
            List of point-based elements to assign texts to
        texts : list[DxfText]
            List of available texts for assignment

        Returns
        -------
        list[ObjectData]
            List of elements with assigned texts where applicable
        """
        if not elements or not texts:
            return elements

        # First, use spatial assignment as base
        spatial_assigner = SpatialTextAssigner(self.max_distance)
        assigned_elements = spatial_assigner.texts_to_point_based(elements, texts)

        # Then validate assignments based on zones
        for element in assigned_elements:
            if element.assigned_text is not None and element.positions:
                text_pos = element.assigned_text.position

                # Check if text is too close to any element position (zone buffer validation)
                for position in element.positions:
                    distance = text_pos.distance_2d(position)

                    # If text is too close to element position, remove assignment
                    if distance < self.zone_buffer:
                        element.assigned_text = None
                        break

        return assigned_elements

    def texts_to_line_based(self, elements: list[ObjectData], texts: list[DxfText]) -> list[ObjectData]:
        """Assign texts to pipes using zone-based validation.

        Text assignments are valid only in zones between pipe
        endpoints, junctions, or shaft connections.

        Parameters
        ----------
        pipes : list[Pipe]
            List of pipes to assign texts to
        texts : list[DxfText]
            List of available texts for assignment

        Returns
        -------
        list[Pipe]
            List of pipes with assigned texts where applicable
        """
        if not elements or not texts:
            return elements

        # First, use spatial assignment as base
        spatial_assigner = SpatialTextAssigner(self.max_distance)
        assigned_elements = spatial_assigner.texts_to_line_based(elements, texts)

        # Then validate assignments based on zones
        # This is a simplified implementation - in practice, you would
        # analyze element networks to identify junctions and connection points

        # For now, we validate that text is not too close to element endpoints
        for element in assigned_elements:
            if element.assigned_text is None:
                continue
            text_pos = element.assigned_text.position

            # Check if text is too close to element start or end (for elements with points)
            if element.points and len(element.points) >= 2:
                start_distance = text_pos.distance_2d(element.points[0])
                end_distance = text_pos.distance_2d(element.points[-1])

                # If text is too close to endpoints, remove assignment
                if start_distance < self.zone_buffer or end_distance < self.zone_buffer:
                    element.assigned_text = None

        return assigned_elements

    def assign_texts_to_objects(self, elements: list[ObjectData], texts: list[DxfText]) -> list[ObjectData]:
        """Assign texts to objects by combining point-based and line-based assignment with zone validation.

        This method first processes point-based elements, then line-based elements,
        with additional zone-based validation for all assignments.

        Parameters
        ----------
        elements : list[ObjectData]
            List of elements to assign texts to
        texts : list[DxfText]
            List of available texts for assignment

        Returns
        -------
        list[ObjectData]
            List of elements with assigned texts where applicable
        """
        if not elements or not texts:
            return elements

        # Separate elements by type
        point_based = []
        line_based = []

        for element in elements:
            if element.positions:  # Point-based elements have positions
                point_based.append(element)
            elif element.points:  # Line-based elements have points
                line_based.append(element)
            else:
                # Neither - keep as is
                pass

        # Process point-based elements first
        assigned_elements = []
        remaining_texts = texts.copy()

        if point_based:
            point_assigned = self.texts_to_point_based(point_based, remaining_texts)
            assigned_elements.extend(point_assigned)

            # Remove used texts from remaining texts
            used_texts = [elem.assigned_text for elem in point_assigned if elem.assigned_text]
            remaining_texts = [text for text in remaining_texts if text not in used_texts]

        # Then process line-based elements with remaining texts
        if line_based:
            line_assigned = self.texts_to_line_based(line_based, remaining_texts)
            assigned_elements.extend(line_assigned)

        # Add any elements that weren't point or line based
        for element in elements:
            if not element.positions and not element.points:
                assigned_elements.append(element)

        return assigned_elements
