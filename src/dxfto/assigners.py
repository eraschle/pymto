"""Text assignment strategies for associating texts with pipes.

This module implements strategies for spatially assigning text elements
to pipe segments based on proximity and validity rules between shafts
or pipe junctions.
"""

import numpy as np

from dxfto.protocols import ITextAssignmentStrategy

from .models import DXFText, Pipe, Point3D


class SpatialTextAssigner(ITextAssignmentStrategy):
    """Assigns texts to pipes based on spatial proximity.

    This assigner uses spatial analysis to find the closest pipe
    for each text element, with constraints on maximum distance
    and validity between shafts/junctions.
    """

    def __init__(self, max_distance: float = 50.0) -> None:
        """Initialize spatial text assigner.

        Parameters
        ----------
        max_distance : float, default 50.0
            Maximum distance for text-to-pipe assignment
        """
        self.max_distance = max_distance

    def assign_texts_to_pipes(self, pipes: list[Pipe], texts: list[DXFText]) -> list[Pipe]:
        """Assign texts to pipes based on spatial proximity.

        Each text can be assigned to at most one pipe segment.
        Assignment is valid only if the text is close enough to
        the pipe and lies between pipe endpoints or junctions.

        Parameters
        ----------
        pipes : list[Pipe]
            List of pipes to assign texts to
        texts : list[DXFText]
            List of available texts for assignment

        Returns
        -------
        list[Pipe]
            List of pipes with assigned texts where applicable
        """
        if not pipes or not texts:
            return pipes

        # Create a copy of pipes to avoid modifying the original list
        assigned_pipes = [
            Pipe(
                shape=pipe.shape,
                points=pipe.points.copy(),
                dimensions=pipe.dimensions,
                layer=pipe.layer,
                color=pipe.color,
                assigned_text=None,  # Reset any existing assignments
            )
            for pipe in pipes
        ]

        # Build spatial index for pipe segments
        pipe_segments = []
        segment_to_pipe = []

        for pipe_idx, pipe in enumerate(assigned_pipes):
            for i in range(len(pipe.points) - 1):
                start_point = pipe.points[i]
                end_point = pipe.points[i + 1]

                # Store segment as (start_point, end_point, pipe_index, segment_index)
                pipe_segments.append((start_point, end_point))
                segment_to_pipe.append((pipe_idx, i))

        if not pipe_segments:
            return assigned_pipes

        # For each text, find the closest pipe segment
        for text in texts:
            closest_pipe_idx, closest_segment_idx, distance = self._find_closest_pipe_segment(
                text.position, pipe_segments, segment_to_pipe
            )

            # Assign text if within maximum distance and pipe doesn't have text yet
            if (
                distance <= self.max_distance
                and closest_pipe_idx is not None
                and assigned_pipes[closest_pipe_idx].assigned_text is None
            ):
                assigned_pipes[closest_pipe_idx].assigned_text = text

        return assigned_pipes

    def _find_closest_pipe_segment(
        self,
        text_position: Point3D,
        pipe_segments: list[tuple[Point3D, Point3D]],
        segment_to_pipe: list[tuple[int, int]],
    ) -> tuple[int | None, int | None, float]:
        """Find the closest pipe segment to a text position.

        Parameters
        ----------
        text_position : Point3D
            Position of the text element
        pipe_segments : list[tuple[Point3D, Point3D]]
            List of pipe segments as (start_point, end_point) tuples
        segment_to_pipe : list[tuple[int, int]]
            Mapping from segment index to (pipe_index, segment_index)

        Returns
        -------
        tuple[int | None, int | None, float]
            (pipe_index, segment_index, distance) of closest segment,
            or (None, None, inf) if no segments exist
        """
        if not pipe_segments:
            return None, None, float("inf")

        min_distance = float("inf")
        closest_pipe_idx = None
        closest_segment_idx = None

        for segment_idx, (start_point, end_point) in enumerate(pipe_segments):
            distance = self._point_to_line_distance(text_position, start_point, end_point)

            if distance < min_distance:
                min_distance = distance
                pipe_idx, seg_idx = segment_to_pipe[segment_idx]
                closest_pipe_idx = pipe_idx
                closest_segment_idx = seg_idx

        return closest_pipe_idx, closest_segment_idx, min_distance

    def _point_to_line_distance(
        self, point: Point3D, line_start: Point3D, line_end: Point3D
    ) -> float:
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
        p = np.array([point.x, point.y])
        a = np.array([line_start.x, line_start.y])
        b = np.array([line_end.x, line_end.y])

        # Vector from line start to end
        ab = b - a

        # Vector from line start to point
        ap = p - a

        # If line segment has zero length, return distance to point
        ab_length_squared = np.dot(ab, ab)
        if ab_length_squared == 0:
            return np.linalg.norm(ap)

        # Project point onto line (parametric form)
        t = np.dot(ap, ab) / ab_length_squared

        # Clamp t to [0, 1] to stay within line segment
        t = max(0, min(1, t))

        # Find the closest point on the line segment
        closest_point = a + t * ab

        # Return distance from original point to closest point on segment
        return np.linalg.norm(p - closest_point)


class ZoneBasedTextAssigner(ITextAssignmentStrategy):
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

    def assign_texts_to_pipes(self, pipes: list[Pipe], texts: list[DXFText]) -> list[Pipe]:
        """Assign texts to pipes using zone-based validation.

        Text assignments are valid only in zones between pipe
        endpoints, junctions, or shaft connections.

        Parameters
        ----------
        pipes : list[Pipe]
            List of pipes to assign texts to
        texts : list[DXFText]
            List of available texts for assignment

        Returns
        -------
        list[Pipe]
            List of pipes with assigned texts where applicable
        """
        if not pipes or not texts:
            return pipes

        # First, use spatial assignment as base
        spatial_assigner = SpatialTextAssigner(self.max_distance)
        assigned_pipes = spatial_assigner.assign_texts_to_pipes(pipes, texts)

        # Then validate assignments based on zones
        # This is a simplified implementation - in practice, you would
        # analyze pipe networks to identify junctions and connection points

        # For now, we validate that text is not too close to pipe endpoints
        for pipe in assigned_pipes:
            if pipe.assigned_text is not None:
                text_pos = pipe.assigned_text.position

                # Check if text is too close to pipe start or end
                if len(pipe.points) >= 2:
                    start_distance = self._point_distance_2d(text_pos, pipe.points[0])
                    end_distance = self._point_distance_2d(text_pos, pipe.points[-1])

                    # If text is too close to endpoints, remove assignment
                    if start_distance < self.zone_buffer or end_distance < self.zone_buffer:
                        pipe.assigned_text = None

        return assigned_pipes

    def _point_distance_2d(self, point1: Point3D, point2: Point3D) -> float:
        """Calculate 2D distance between two points.

        Parameters
        ----------
        point1 : Point3D
            First point
        point2 : Point3D
            Second point

        Returns
        -------
        float
            2D Euclidean distance
        """
        dx = point1.x - point2.x
        dy = point1.y - point2.y
        return np.sqrt(dx**2 + dy**2)
