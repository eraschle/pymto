"""Simplified connection analysis for gradient normalization based on shafts along pipes."""

import logging
import time
from collections.abc import Iterable
from functools import wraps
from typing import Any

from shapely.geometry import LineString, Point
from shapely.strtree import STRtree

from ..analyze.compatibilty import IMediumCompatibilityStrategy
from ..models import Medium, ObjectData, Point3D

log = logging.getLogger(__name__)


class ConnectionAnalyzerShapely:
    """Analyzes pipe connections and normalizes gradients using shapely geometries."""

    def __init__(
        self,
        tolerance: float,
        compatibility: IMediumCompatibilityStrategy,
        elevation_threshold: float,
    ):
        """
        Initialize connection analyzer using shapely geometries.

        Parameters
        ----------
        tolerance : float
            Maximum distance in meters to consider a connection valid
        compatibility : IMediumCompatibilityStrategy
            Strategy for checking medium compatibility
        elevation_threshold : float
            Minimum elevation change in meters to detect gradient breaks
        """
        self.tolerance = tolerance
        self.compatibility = compatibility
        self.elevation_threshold = elevation_threshold
        self.mediums: list[Medium] = []

        # Per-medium spatial indexing using shapely STRtree
        self._medium_spatial_indices = {}  # Dict[medium_name, Dict[str, STRtree]]
        self._spatial_indices_built = False

    def load_multiple_mediums(self, mediums: Iterable[Medium]) -> None:
        """Load data from multiple Medium objects.

        Parameters
        ----------
        mediums : Iterable[Medium]
            Iterable of mediums containing assigned elements
        """
        # Reset caches when data changes
        self._spatial_indices_built = False
        self._medium_spatial_indices = {}
        self.mediums = list(mediums)

    def _build_spatial_indices(self) -> None:
        """Build per-medium spatial indices using shapely STRtree."""
        if self._spatial_indices_built:
            return

        # Build spatial indices per medium
        for medium in self.mediums:
            medium_indices = {}

            # Get elements directly from Medium object
            shaft_elements = medium.get_point_elements()
            pipe_elements = medium.get_line_elements()

            # Build shaft spatial index using Point geometries
            if shaft_elements:
                shaft_geometries = []
                shaft_mapping = []  # Maps geometry index to shaft element

                for shaft_idx, shaft in enumerate(shaft_elements):
                    shaft_point = Point(shaft.point.east, shaft.point.north)
                    shaft_geometries.append(shaft_point)
                    shaft_mapping.append(shaft_idx)

                if shaft_geometries:
                    medium_indices["shaft_tree"] = STRtree(shaft_geometries)
                    medium_indices["shaft_mapping"] = shaft_mapping
                    medium_indices["shaft_elements"] = shaft_elements

            # Build pipe spatial index using LineString geometries
            if pipe_elements:
                pipe_geometries = []
                pipe_mapping = []  # Maps geometry index to pipe element

                for pipe_idx, pipe in enumerate(pipe_elements):
                    if len(pipe.points) >= 2:
                        # Create LineString from pipe points
                        coords = [(point.east, point.north) for point in pipe.points]
                        pipe_line = LineString(coords)
                        pipe_geometries.append(pipe_line)
                        pipe_mapping.append(pipe_idx)

                if pipe_geometries:
                    medium_indices["pipe_tree"] = STRtree(pipe_geometries)
                    medium_indices["pipe_mapping"] = pipe_mapping
                    medium_indices["pipe_elements"] = pipe_elements

            self._medium_spatial_indices[medium.name] = medium_indices

        self._spatial_indices_built = True

    def _find_shaft_at_point(self, point: Point3D, medium_name: str) -> ObjectData | None:
        """Find a shaft at the given point.

        Parameters
        ----------
        point : Point3D
            Point to search at
        medium_name : str
            Medium to search in

        Returns
        -------
        ObjectData | None
            Shaft at the point or None if not found
        """
        # Get spatial index for this medium
        medium_indices = self._medium_spatial_indices.get(medium_name)
        if not medium_indices or "shaft_tree" not in medium_indices:
            return None

        shaft_tree = medium_indices["shaft_tree"]
        shaft_mapping = medium_indices["shaft_mapping"]
        shaft_elements = medium_indices["shaft_elements"]

        # Create query point with buffer for tolerance
        query_point = Point(point.east, point.north)
        query_buffer = query_point.buffer(self.tolerance)

        # Query STRtree for shaft candidates
        candidate_indices = list(shaft_tree.query(query_buffer))

        # Find closest shaft within tolerance
        closest_shaft = None
        min_distance = float("inf")

        for geom_idx in candidate_indices:
            shaft_idx = shaft_mapping[geom_idx]
            shaft = shaft_elements[shaft_idx]

            distance = point.distance_2d(shaft.point)
            if distance <= self.tolerance and distance < min_distance:
                min_distance = distance
                closest_shaft = shaft

        return closest_shaft

    def _find_shafts_along_pipe(self, pipe: ObjectData) -> list[tuple[int, ObjectData]]:
        """Find all shafts near any point of a pipe.

        Parameters
        ----------
        pipe : ObjectData
            Pipe to check for nearby shafts

        Returns
        -------
        list[tuple[int, ObjectData]]
            List of (point_index, shaft) tuples for shafts found near pipe points
        """
        shafts_along_pipe = []

        # Check each point of the pipe for nearby shafts
        for point_idx, point in enumerate(pipe.points):
            shaft = self._find_shaft_at_point(point, pipe.medium)
            if shaft:
                shafts_along_pipe.append((point_idx, shaft))

        return shafts_along_pipe

    def _build_pipe_segments_with_shafts(self, pipe: ObjectData) -> list[dict]:
        """Build pipe segments between shafts or from shaft to pipe end.

        Parameters
        ----------
        pipe : ObjectData
            Pipe to segment

        Returns
        -------
        list[dict]
            List of segment dictionaries with keys:
            - 'start_point_idx': Starting point index in pipe
            - 'end_point_idx': Ending point index in pipe
            - 'start_shaft': Starting shaft (if any)
            - 'end_shaft': Ending shaft (if any)
            - 'points': List of points in this segment
            - 'length': Segment length
        """
        segments = []

        # Find all shafts along this pipe
        shafts_along_pipe = self._find_shafts_along_pipe(pipe)

        if not shafts_along_pipe:
            # No shafts found - treat entire pipe as one segment
            return [
                {
                    "start_point_idx": 0,
                    "end_point_idx": len(pipe.points) - 1,
                    "start_shaft": None,
                    "end_shaft": None,
                    "points": pipe.points.copy(),
                    "length": self._calculate_segment_length(pipe.points),
                }
            ]

        # Sort shafts by point index
        # shafts_along_pipe.sort(key=lambda x: x[0])

        # Create segments between shafts
        prev_point_idx = 0
        prev_shaft = None

        for point_idx, shaft in shafts_along_pipe:
            # Handle special case: shaft at first point
            if point_idx == 0:
                # First shaft is at start point - just record it
                prev_shaft = shaft
                prev_point_idx = 0
                continue

            # Create segment from previous position to current shaft
            if point_idx > prev_point_idx:
                segment_points = pipe.points[prev_point_idx : point_idx + 1]
                segment_length = self._calculate_segment_length(segment_points)

                # Ensure correct flow direction when both shafts exist
                final_start_shaft = prev_shaft
                final_end_shaft = shaft
                final_points = segment_points

                if prev_shaft and shaft:
                    # Check if segment direction needs to be reversed based on shaft altitudes
                    if prev_shaft.point.altitude < shaft.point.altitude:
                        # Reverse segment to ensure downward flow (higher to lower shaft)
                        final_points = list(reversed(segment_points))
                        final_start_shaft = shaft
                        final_end_shaft = prev_shaft
                        log.debug(
                            f"Reversed segment direction during building: shaft altitudes {prev_shaft.point.altitude:.2f} -> {shaft.point.altitude:.2f}"
                        )

                segments.append(
                    {
                        "start_point_idx": prev_point_idx,
                        "end_point_idx": point_idx,
                        "start_shaft": final_start_shaft,
                        "end_shaft": final_end_shaft,
                        "points": final_points,
                        "length": segment_length,
                    }
                )

            prev_point_idx = point_idx
            prev_shaft = shaft

        # Create final segment from last shaft to pipe end
        if prev_point_idx < len(pipe.points) - 1:
            segment_points = pipe.points[prev_point_idx:]
            segment_length = self._calculate_segment_length(segment_points)

            segments.append(
                {
                    "start_point_idx": prev_point_idx,
                    "end_point_idx": len(pipe.points) - 1,
                    "start_shaft": prev_shaft,
                    "end_shaft": None,  # No shaft at pipe end
                    "points": segment_points,
                    "length": segment_length,
                }
            )

        return segments

    def _calculate_segment_length(self, points: list[Point3D]) -> float:
        """Calculate length of a point sequence."""
        if len(points) < 2:
            return 0.0

        total_length = 0.0
        for idx in range(len(points) - 1):
            total_length += points[idx].distance_2d(points[idx + 1])

        return total_length

    def _has_gradient_break(self, points: list[Point3D]) -> bool:
        """Check if a sequence of points contains a significant gradient break.

        Parameters
        ----------
        points : list[Point3D]
            Points to check for gradient breaks

        Returns
        -------
        bool
            True if gradient break detected (elevation change > threshold)
        """
        if len(points) < 2:
            return False

        for i in range(len(points) - 1):
            elevation_diff = abs(points[i + 1].altitude - points[i].altitude)
            if elevation_diff > self.elevation_threshold:
                log.debug(
                    f"Gradient break detected: {elevation_diff:.2f}m elevation change "
                    f"exceeds threshold {self.elevation_threshold:.2f}m"
                )
                return True
        return False

    def _should_preserve_segment_gradient(self, segment: dict) -> bool:
        """Check if segment gradient should be preserved due to gradient breaks.

        Parameters
        ----------
        segment : dict
            Segment to check

        Returns
        -------
        bool
            True if segment gradient should be preserved (not normalized)
        """
        segment_points = segment["points"]

        # Preserve gradient if segment contains gradient breaks
        if self._has_gradient_break(segment_points):
            log.debug("Preserving segment gradient due to gradient break")
            return True

        # Also check if segment connects to shafts with significant height difference
        start_shaft = segment.get("start_shaft")
        end_shaft = segment.get("end_shaft")

        if start_shaft and end_shaft:
            shaft_height_diff = abs(start_shaft.point.altitude - end_shaft.point.altitude)
            if shaft_height_diff > self.elevation_threshold:
                log.debug(
                    f"Preserving segment gradient due to significant shaft height difference: {shaft_height_diff:.2f}m"
                )
                return True

        return False

    def _normalize_pipe_segments(self, pipe: ObjectData) -> None:
        """Normalize gradients for all segments of a pipe based on nearby shafts.

        Parameters
        ----------
        pipe : ObjectData
            Pipe to normalize
        """
        segments = self._build_pipe_segments_with_shafts(pipe)

        if not segments:
            return

        # Process each segment individually
        new_points = []

        for segment in segments:
            start_shaft = segment["start_shaft"]
            end_shaft = segment["end_shaft"]
            segment_points = list(segment["points"])  # Create explicit copy to avoid modifying original
            segment_length = segment["length"]

            if segment_length == 0:
                # Keep original points for zero-length segments
                log.warning(f"Zero-length segment detected during normalization: {segment_points}")
                new_points.extend(segment_points)
                continue

            # Check if gradient should be preserved due to gradient breaks
            if self._should_preserve_segment_gradient(segment):
                log.debug("Preserving original segment gradient due to gradient break detection")
                new_points.extend(segment_points if not new_points else segment_points[1:])
                continue

            # Calculate gradient based on shaft altitude difference (if both shafts exist)
            if start_shaft and end_shaft:
                # Segments are already correctly oriented by _build_pipe_segments_with_shafts
                start_pipe_altitude = segment_points[0].altitude
                end_pipe_altitude = segment_points[-1].altitude

                # Use difference between shaft altitudes to calculate gradient
                shaft_altitude_diff = end_shaft.point.altitude - start_shaft.point.altitude
                gradient = shaft_altitude_diff / segment_length

                # Start from pipe's actual start altitude
                start_altitude = start_pipe_altitude
                end_altitude = start_altitude + (gradient * segment_length)

                log.debug(
                    f"Shaft-based gradient: {gradient:.4f} m/m (shaft diff: {shaft_altitude_diff:.2f}m over {segment_length:.2f}m)"
                )

            elif start_shaft:
                # Read pipe altitudes for single shaft cases
                start_pipe_altitude = segment_points[0].altitude
                end_pipe_altitude = segment_points[-1].altitude

                # Only start shaft available - use pipe gradient
                pipe_gradient = (end_pipe_altitude - start_pipe_altitude) / segment_length
                start_altitude = start_pipe_altitude
                end_altitude = end_pipe_altitude
                gradient = pipe_gradient
                log.debug(f"Start shaft only: using pipe gradient {gradient:.4f} m/m")

            elif end_shaft:
                # Read pipe altitudes for single shaft cases
                start_pipe_altitude = segment_points[0].altitude
                end_pipe_altitude = segment_points[-1].altitude

                # Only end shaft available - use pipe gradient but ensure it flows toward shaft
                pipe_gradient = (end_pipe_altitude - start_pipe_altitude) / segment_length
                start_altitude = start_pipe_altitude
                end_altitude = end_pipe_altitude
                gradient = pipe_gradient

                log.debug(f"End shaft only: using pipe gradient {gradient:.4f} m/m")

            else:
                start_pipe_altitude = segment_points[0].altitude
                end_pipe_altitude = segment_points[-1].altitude

                # No shafts - keep original pipe gradient
                start_altitude = start_pipe_altitude
                end_altitude = end_pipe_altitude
                gradient = (end_altitude - start_altitude) / segment_length

                log.debug(f"No shafts: keeping original pipe gradient {gradient:.4f} m/m")

            # For non-shaft segments, ensure descending gradient (higher to lower)
            # if not (start_shaft and end_shaft) and start_altitude < end_altitude:
            #     # Reverse segment if ascending (only when no shafts are defining the direction)
            #     segment_points.reverse()
            #     start_altitude, end_altitude = end_altitude, start_altitude
            #     gradient = -gradient  # Reverse gradient sign

            # Apply gradient to segment points
            segment_new_points = []
            current_distance = 0.0

            for idx, point in enumerate(segment_points):
                if idx == 0:
                    # First point - use start altitude
                    new_altitude = start_altitude
                else:
                    # Calculate distance from previous point
                    prev_point = segment_points[idx - 1]
                    current_distance += point.distance_2d(prev_point)

                    # Apply gradient
                    new_altitude = start_altitude + (gradient * current_distance)

                # Create new Point3D with updated altitude
                new_point = Point3D(east=point.east, north=point.north, altitude=new_altitude)
                segment_new_points.append(new_point)

            # Add segment points to new points list (avoid duplication at boundaries)
            if not new_points:
                new_points.extend(segment_new_points)
            else:
                # Skip first point to avoid duplication with previous segment
                new_points.extend(segment_new_points[1:])

        # Replace pipe points with normalized points
        pipe.points = new_points

    def normalize_all_pipe_gradients_by_shafts(self) -> None:
        """Normalize gradients for all pipes based on shafts along their length."""
        self._build_spatial_indices()

        # Process each medium separately
        for medium in self.mediums:
            medium_indices = self._medium_spatial_indices.get(medium.name)
            if not medium_indices:
                continue

            pipe_elements = medium_indices.get("pipe_elements", [])
            if not pipe_elements:
                continue

            log.info(f"Normalizing gradients for {medium.name}: {len(pipe_elements)} pipes")

            # Process each pipe individually
            for pipe in pipe_elements:
                self._normalize_pipe_segments(pipe)

    def analyze_and_normalize_pipe_gradients(self) -> dict[str, Any]:
        """Analyze pipes and normalize gradients based on shafts along pipe length.

        Returns
        -------
        dict[str, Any]
            Analysis summary with statistics
        """
        # Normalize gradients for all pipes based on shaft positions
        self.normalize_all_pipe_gradients_by_shafts()

        # Calculate totals and statistics
        total_pipes = sum(len(medium.get_line_elements()) for medium in self.mediums)
        total_shafts = sum(len(medium.get_point_elements()) for medium in self.mediums)

        # Count pipes with shaft-based segments
        pipes_with_shafts = 0
        total_segments = 0

        for medium in self.mediums:
            medium_indices = self._medium_spatial_indices.get(medium.name)
            if not medium_indices:
                continue

            pipe_elements = medium_indices.get("pipe_elements", [])
            for pipe in pipe_elements:
                segments = self._build_pipe_segments_with_shafts(pipe)
                if len(segments) > 1 or (
                    len(segments) == 1 and (segments[0]["start_shaft"] or segments[0]["end_shaft"])
                ):
                    pipes_with_shafts += 1
                total_segments += len(segments)

        summary = {
            "total_pipes": total_pipes,
            "total_shafts": total_shafts,
            "pipes_with_shafts": pipes_with_shafts,
            "pipes_without_shafts": total_pipes - pipes_with_shafts,
            "total_segments": total_segments,
            "tolerance_meters": self.tolerance,
            "elevation_threshold_meters": self.elevation_threshold,
            "compatibility_strategy": type(self.compatibility).__name__,
            "processing_method": "shaft_based_segments",
        }

        return summary
