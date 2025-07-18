"""Pipeline gradient adjustment for medium-compatible flow systems.

This module provides functionality to adjust pipeline elevations based on
connected manhole elevations, with configurable medium compatibility strategies.
"""

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from ..models import (
    Medium,
    MediumConfig,
    ObjectData,
    ObjectType,
    Point3D,
)
from .compatibilty import (
    IMediumCompatibilityStrategy,
    PrefixBasedCompatibility,
)

log = logging.getLogger(__name__)


@dataclass
class GradientAdjustmentParams:
    """Parameters for gradient adjustment."""

    manhole_search_radius: float = 3.0  # Radius to find connected manholes (meters)
    min_gradient_percent: float = 0.5  # Minimum gradient to enforce
    gradient_break_threshold: float = 2.0  # Minimum gradient change to be considered a break


@dataclass
class PipelineAdjustment:
    """Record of a pipeline adjustment (simplified for basic usage)."""

    pipeline: ObjectData
    original_start: float
    original_end: float
    adjusted_start: float
    adjusted_end: float
    calculated_gradient: float
    adjustment_reason: str


@dataclass
class CoverToPipeHeight:
    """Record of cover-to-pipe height calculation."""

    shaft: ObjectData
    connected_pipes: list[ObjectData]
    lowest_pipe: ObjectData | None
    cover_elevation: float
    lowest_pipe_elevation: float | None
    height_difference: float | None
    medium_compatibility: str


class PipelineGradientAdjuster:
    """Adjusts pipeline gradients with configurable medium compatibility strategies."""

    def __init__(
        self,
        mediums: Iterable[Medium],
        min_height: float = 1.0,
        params: GradientAdjustmentParams | None = None,
        compatibility: IMediumCompatibilityStrategy | None = None,
    ) -> None:
        """Initialize the gradient adjuster.

        Parameters
        ----------
        params : GradientAdjustmentParams | None
            Adjustment parameters, uses defaults if None
        compatibility_strategy : MediumCompatibilityStrategy | None
            Strategy for checking medium compatibility, uses prefix-based if None
        """
        self.mediums = mediums
        self.min_height = min_height
        self.params = params or GradientAdjustmentParams()
        self.compatibility = compatibility or PrefixBasedCompatibility()

    def adjust_gradients_by(self, elements: list[ObjectData]) -> list[PipelineAdjustment]:
        """Adjust pipeline gradients considering medium compatibility."""
        medium_groups = self._group_objects_by(elements)

        adjustments = []
        for group_id, group_objects in medium_groups.items():
            log.info(f"Adjusting gradients for compatibility group: {group_id}")
            group_adjustments = self._adjust_medium_group(group_objects)
            adjustments.extend(group_adjustments)

        return adjustments

    def _group_objects_by(self, objects: list[ObjectData]) -> dict[str, list[ObjectData]]:
        """Group objects by compatibility groups."""
        groups = {}

        for obj in objects:
            group_id = self.compatibility.get_group(obj.medium)
            if group_id not in groups:
                groups[group_id] = []
            groups[group_id].append(obj)

        return groups

    def _adjust_medium_group(self, objects: list[ObjectData]) -> list[PipelineAdjustment]:
        """Adjust gradients for objects in the same compatibility group."""
        adjustments = []

        pipelines = [obj for obj in objects if obj.is_line_based]
        manholes = [obj for obj in objects if obj.is_point_based and self._is_manhole(obj)]

        log.info(f"Processing {len(pipelines)} pipelines and {len(manholes)} manholes")

        for pipeline in pipelines:
            adjustment = self._adjust_single_pipeline(pipeline, manholes)
            if adjustment:
                adjustments.append(adjustment)

        return adjustments

    def _is_manhole(self, obj: ObjectData) -> bool:
        """Check if object is a manhole/shaft."""
        return "shaft" in obj.object_type.value.lower()

    def _is_pipe(self, obj: ObjectData) -> bool:
        """Check if object is a manhole/shaft."""
        return obj.object_type in (ObjectType.PIPE)

    def _adjust_single_pipeline(self, pipeline: ObjectData, manholes: list[ObjectData]) -> PipelineAdjustment | None:
        """Adjust elevation for a single pipeline based on compatible manholes."""
        if not pipeline.is_line_based:
            return None

        # Handle both simple (2-point) and complex (multi-point) pipelines
        if len(pipeline.points) < 2:
            return None

        start_point = pipeline.point
        end_point = pipeline.end_point

        if end_point is None:
            return None

        # Find connected manholes (considering medium compatibility)
        start_shaft = self._find_nearest_manhole(start_point, manholes, pipeline.medium)
        end_shaft = self._find_nearest_manhole(end_point, manholes, pipeline.medium)

        # Store original elevations
        orig_start_elev = start_point.altitude
        orig_end_elev = end_point.altitude

        # Handle gradient breaks for complex pipelines
        if pipeline.points and len(pipeline.points) > 2:
            return self._adjust_pipeline_with_gradient_breaks(pipeline, start_shaft, end_shaft)

        # Simple 2-point pipeline adjustment
        new_start_elev, new_end_elev, gradient_perc, reason = self._calculate_elevations(
            start_point, end_point, start_shaft, end_shaft
        )

        # Check if adjustment is needed
        elevation_tolerance = 0.05  # 5cm tolerance
        start_needs_adjust = abs(new_start_elev - orig_start_elev) > elevation_tolerance
        end_needs_adjust = abs(new_end_elev - orig_end_elev) > elevation_tolerance

        if start_needs_adjust or end_needs_adjust:
            # Apply the adjustment
            self._apply_elevation_adjustment(pipeline, new_start_elev, new_end_elev)

            return PipelineAdjustment(
                pipeline=pipeline,
                original_start=orig_start_elev,
                original_end=orig_end_elev,
                adjusted_start=new_start_elev,
                adjusted_end=new_end_elev,
                calculated_gradient=gradient_perc,
                adjustment_reason=reason,
            )

        return None

    def _adjust_pipeline_with_gradient_breaks(
        self,
        pipeline: ObjectData,
        start_shaft: ObjectData | None,
        end_shaft: ObjectData | None,
    ) -> PipelineAdjustment | None:
        """Adjust pipeline with multiple points, preserving gradient breaks."""
        if not pipeline.points or len(pipeline.points) < 3:
            return None

        original_points = list(pipeline.points)
        original_start = original_points[0].altitude
        original_end = original_points[-1].altitude

        # Detect gradient breaks and terrain bumps
        gradient_breaks = self._detect_gradient_breaks(original_points)
        terrain_bumps = self._detect_terrain_bumps(original_points)

        # Calculate target elevations for start and end
        start_point = original_points[0]
        end_point = original_points[-1]

        target_start_elev, target_end_elev, gradient_perc, reason = self._calculate_elevations(
            start_point, end_point, start_shaft, end_shaft
        )

        # Apply adjustments preserving gradient breaks
        new_points = self._apply_gradient_preserving_adjustment(
            original_points, target_start_elev, target_end_elev, gradient_breaks, terrain_bumps
        )

        # Update pipeline points
        pipeline.points = new_points

        return PipelineAdjustment(
            pipeline=pipeline,
            original_start=original_start,
            original_end=original_end,
            adjusted_start=new_points[0].altitude,
            adjusted_end=new_points[-1].altitude,
            calculated_gradient=gradient_perc,
            adjustment_reason=f"{reason} with gradient break preservation",
        )

    def _detect_gradient_breaks(self, points: list[Point3D]) -> list[int]:
        """Detect significant downward gradient breaks in pipeline."""
        gradient_breaks = []

        if len(points) < 3:
            return gradient_breaks

        # Calculate gradients between consecutive segments
        for idx in range(1, len(points) - 1):
            prev_point = points[idx - 1]
            curr_point = points[idx]
            next_point = points[idx + 1]

            # Calculate distances
            dist_prev = prev_point.distance_2d(curr_point)
            dist_next = curr_point.distance_2d(next_point)

            if dist_prev == 0 or dist_next == 0:
                continue

            # Calculate gradients (positive = uphill, negative = downhill)
            grad_prev = ((curr_point.altitude - prev_point.altitude) / dist_prev) * 100
            grad_next = ((next_point.altitude - curr_point.altitude) / dist_next) * 100

            # Detect significant downward break using configurable threshold
            # gradient_change = grad_next - grad_prev
            # if gradient_change < -self.params.gradient_break_threshold:
            gradient_change = abs(grad_next - grad_prev)
            if gradient_change > self.params.gradient_break_threshold:
                gradient_breaks.append(idx)

        return gradient_breaks

    def _detect_terrain_bumps(self, points: list[Point3D]) -> list[int]:
        """Detect terrain bumps (uphill followed by downhill) that need correction."""
        terrain_bumps = []

        if len(points) < 3:
            return terrain_bumps

        # Look for uphill-downhill patterns
        for idx in range(1, len(points) - 1):
            prev_point = points[idx - 1]
            curr_point = points[idx]
            next_point = points[idx + 1]

            # Check if current point is higher than both neighbors (bump)
            if curr_point.altitude > prev_point.altitude and curr_point.altitude > next_point.altitude:
                terrain_bumps.append(idx)

        return terrain_bumps

    def _apply_gradient_preserving_adjustment(
        self,
        original_points: list[Point3D],
        target_start_elev: float,
        target_end_elev: float,
        gradient_breaks: list[int],
        terrain_bumps: list[int],
    ) -> list[Point3D]:
        """Apply elevation adjustments while preserving gradient breaks."""
        new_points = []

        # Start with target elevations
        current_elevation = target_start_elev

        for idx, point in enumerate(original_points):
            if idx == 0:
                # First point gets target start elevation
                new_elevation = target_start_elev
            elif idx == len(original_points) - 1:
                # Last point gets target end elevation
                new_elevation = target_end_elev
            elif idx in terrain_bumps:
                # Terrain bump: smooth it out by interpolating
                prev_elev = new_points[idx - 1].altitude
                # Look ahead to find next non-bump point
                next_idx = idx + 1
                while next_idx < len(original_points) - 1 and next_idx in terrain_bumps:
                    next_idx += 1

                if next_idx < len(original_points):
                    next_orig_elev = original_points[next_idx].altitude
                    # Interpolate between previous adjusted and next original
                    distance_to_prev = point.distance_2d(original_points[idx - 1])
                    distance_to_next = point.distance_2d(original_points[next_idx])
                    total_distance = distance_to_prev + distance_to_next

                    if total_distance > 0:
                        ratio = distance_to_prev / total_distance
                        new_elevation = prev_elev - (ratio * abs(prev_elev - next_orig_elev))
                    else:
                        new_elevation = prev_elev
                else:
                    new_elevation = new_points[idx - 1].altitude
            elif idx in gradient_breaks:
                # Gradient break: preserve the break but adjust level
                prev_point = original_points[idx - 1]
                curr_point = original_points[idx]

                # Calculate distance and preserve the elevation drop
                distance = prev_point.distance_2d(curr_point)
                original_drop = prev_point.altitude - curr_point.altitude

                # Start from last calculated elevation and apply same drop
                new_elevation = new_points[idx - 1].altitude - original_drop
            else:
                # Regular point: interpolate based on terrain following DGM
                if idx < len(original_points) - 1:
                    # Calculate based on previous adjusted point and current DGM gradient
                    prev_adj_point = new_points[idx - 1]
                    prev_orig_point = original_points[idx - 1]
                    curr_orig_point = original_points[idx]

                    # Calculate distance and original gradient
                    distance = prev_orig_point.distance_2d(curr_orig_point)
                    if distance > 0:
                        original_gradient = ((curr_orig_point.altitude - prev_orig_point.altitude) / distance) * 100

                        # Apply minimum gradient constraint but preserve terrain following
                        if original_gradient > 0:  # Uphill in DGM
                            # Apply minimum downhill gradient instead
                            elevation_drop = (self.params.min_gradient_percent / 100) * distance
                            new_elevation = prev_adj_point.altitude - elevation_drop
                        else:
                            # Keep original downhill gradient if acceptable
                            if abs(original_gradient) >= self.params.min_gradient_percent:
                                elevation_change = (original_gradient / 100) * distance
                                new_elevation = prev_adj_point.altitude + elevation_change
                            else:
                                # Enforce minimum gradient
                                elevation_drop = (self.params.min_gradient_percent / 100) * distance
                                new_elevation = prev_adj_point.altitude - elevation_drop
                    else:
                        new_elevation = new_points[idx - 1].altitude
                else:
                    new_elevation = current_elevation

            # Create new point with adjusted elevation
            new_point = Point3D(point.east, point.north, new_elevation)
            new_points.append(new_point)
            current_elevation = new_elevation

        return new_points

    def _find_nearest_manhole(
        self, point: Point3D, manholes: list[ObjectData], pipeline_medium: str
    ) -> ObjectData | None:
        """Find the nearest manhole with compatible medium."""
        nearest_manhole = None
        min_distance = float("inf")

        for manhole in manholes:
            if not manhole.is_point_based:
                continue
            # Check medium compatibility using strategy
            if not self.compatibility.are_compatible(pipeline_medium, manhole.medium):
                continue

            distance = point.distance_2d(manhole.point)
            if distance <= self.params.manhole_search_radius and distance < min_distance:
                min_distance = distance
                nearest_manhole = manhole

        return nearest_manhole

    def _find_all_connected_pipes(self, shaft: ObjectData, pipelines: list[ObjectData]) -> list[ObjectData]:
        """Find all pipes connected to a shaft within the search radius."""
        connected_pipes = []

        for pipeline in pipelines:
            if not pipeline.is_line_based:
                continue

            # Check medium compatibility
            if not self.compatibility.are_compatible(shaft.medium, pipeline.medium):
                continue

            # Check if pipe start or end is within search radius of shaft
            start_distance = min(shaft.point.distance_2d(pipeline.point), shaft.point.distance_2d(pipeline.end_point))
            end_distance = min(shaft.point.distance_2d(pipeline.end_point), shaft.point.distance_2d(pipeline.point))

            if all(distance > self.params.manhole_search_radius for distance in (start_distance, end_distance)):
                continue
            connected_pipes.append(pipeline)

        return connected_pipes

    def calculate_dimension(self, elements: list[ObjectData]) -> list[CoverToPipeHeight]:
        """Calculate cover-to-lowest-pipe height differences for all shafts."""
        medium_groups = self._group_objects_by(elements)

        cover_heights = []
        for group_id, group_objects in medium_groups.items():
            log.info(f"Calculating cover heights for compatibility group: {group_id}")
            group_heights = self._calculate_group_cover_heights(group_objects)
            cover_heights.extend(group_heights)

        return cover_heights

    def _get_line_element_height(self, element: ObjectData) -> float:
        dimension = element.dimension
        if dimension.is_round:
            return dimension.diameter
        if dimension.is_rectangular:
            return dimension.depth
        return 0.0

    def _calculate_group_cover_heights(self, objects: list[ObjectData]) -> list[CoverToPipeHeight]:
        """Calculate cover heights for objects in the same compatibility group."""
        pipelines = [obj for obj in objects if obj.is_line_based and self._is_pipe(obj)]
        manholes = [obj for obj in objects if obj.is_point_based and self._is_manhole(obj)]

        cover_heights = []

        for shaft in manholes:
            connected_pipes = self._find_all_connected_pipes(shaft, pipelines)

            if len(connected_pipes) == 0:
                continue

            # Find the lowest pipe elevation
            lowest_pipe = None
            lowest_altitude = float("inf")

            for pipe in connected_pipes:
                if not pipe.has_end_point:
                    continue

                start_distance = shaft.point.distance_2d(pipe.point)
                end_distance = shaft.point.distance_2d(pipe.end_point)

                height = self._get_line_element_height(pipe)
                if start_distance <= end_distance:
                    pipe_altitude = pipe.point.altitude - height
                elif end_distance < start_distance:
                    pipe_altitude = pipe.end_point.altitude - height
                else:
                    continue

                if pipe_altitude < lowest_altitude or lowest_pipe is None:
                    lowest_altitude = pipe_altitude
                    lowest_pipe = pipe

            height_diff = shaft.point.altitude - lowest_altitude
            shaft.dimension.height = max(self.min_height, height_diff)

            compatibility_desc = self._describe_shaft_pipe_compatibility(shaft, connected_pipes)
            cover_heights.append(
                CoverToPipeHeight(
                    shaft=shaft,
                    connected_pipes=connected_pipes,
                    lowest_pipe=lowest_pipe,
                    cover_elevation=shaft.point.altitude,
                    lowest_pipe_elevation=lowest_altitude,
                    height_difference=height_diff,
                    medium_compatibility=compatibility_desc,
                )
            )

        return cover_heights

    def _describe_shaft_pipe_compatibility(self, shaft: ObjectData, connected_pipes: list[ObjectData]) -> str:
        """Create description of shaft-pipe medium compatibility."""
        if not connected_pipes:
            return f"No compatible pipes found for shaft {shaft.medium}"

        pipe_mediums = list({pipe.medium for pipe in connected_pipes})
        descriptions = []

        for pipe_medium in pipe_mediums:
            compatibility = self.compatibility.get_description(shaft.medium, pipe_medium)
            pipe_count = sum(1 for pipe in connected_pipes if pipe.medium == pipe_medium)
            descriptions.append(f"{pipe_count}x {pipe_medium} ({compatibility})")

        return f"Shaft {shaft.medium} → " + ", ".join(descriptions)

    def _describe_compatibility(
        self, pipeline: ObjectData, start_manhole: ObjectData | None, end_manhole: ObjectData | None
    ) -> str:
        """Create description of medium compatibility used."""
        descriptions = []

        if start_manhole:
            compatibility = self.compatibility.get_description(pipeline.medium, start_manhole.medium)
            descriptions.append(f"Start: {compatibility}")

        if end_manhole:
            compatibility = self.compatibility.get_description(pipeline.medium, end_manhole.medium)
            descriptions.append(f"End: {compatibility}")

        if not descriptions:
            return f"No compatible manholes found for {pipeline.medium}"

        return "; ".join(descriptions)

    def _get_object_config(self, element: ObjectData) -> MediumConfig | None:
        """Get the master medium configuration for an element."""
        for medium in self.mediums:
            if medium.name != element.medium:
                continue
            return medium.config.config_by(element.object_type)
        return None

    def _get_elevation_offset(self, element: ObjectData) -> float:
        """Get elevation offset for an element based on its medium."""
        master_config = self._get_object_config(element)
        return master_config.elevation_offset if master_config else 0.0

    def _calculate_elevations(
        self,
        start_point: Point3D,
        end_point: Point3D,
        start_manhole: ObjectData | None,
        end_manhole: ObjectData | None,
    ) -> tuple[float, float, float, str]:
        """Calculate new pipeline elevations based on connected manholes."""
        distance_2d = start_point.distance_2d(end_point)

        # Case 1: Both manholes found - ensure proper flow direction
        if start_manhole and end_manhole:
            start_elev = start_manhole.point.altitude - self._get_elevation_offset(start_manhole)
            end_elev = end_manhole.point.altitude - self._get_elevation_offset(end_manhole)

            # Always flow from higher to lower elevation
            if start_elev < end_elev:
                start_elev, end_elev = end_elev, start_elev
                reason = "Corrected flow direction from higher to lower shaft"
            else:
                reason = "Used shaft elevations with proper flow direction"

            elevation_diff = end_elev - start_elev
            gradient_percent = (elevation_diff / distance_2d) * 100 if distance_2d > 0 else 0

            # Apply gradient constraints
            if abs(gradient_percent) < self.params.min_gradient_percent:
                min_drop = (self.params.min_gradient_percent / 100) * distance_2d
                end_elev = start_elev - min_drop
                gradient_percent = -self.params.min_gradient_percent
                reason = f"Enforced minimum gradient {self.params.min_gradient_percent}%"

            return start_elev, end_elev, gradient_percent, reason

        # Case 2: Only start manhole found
        elif start_manhole:
            start_elev = start_manhole.point.altitude - self._get_elevation_offset(start_manhole)
            min_drop = (self.params.min_gradient_percent / 100) * distance_2d
            end_elev = start_elev - min_drop
            gradient_percent = -self.params.min_gradient_percent
            reason = f"Used compatible start manhole, applied {self.params.min_gradient_percent}% downhill gradient"
            return start_elev, end_elev, gradient_percent, reason

        # Case 3: Only end manhole found
        elif end_manhole:
            end_elev = end_manhole.point.altitude - self._get_elevation_offset(end_manhole)
            min_drop = (self.params.min_gradient_percent / 100) * distance_2d
            start_elev = end_elev + min_drop
            gradient_percent = -self.params.min_gradient_percent
            reason = f"Used compatible end manhole, applied {self.params.min_gradient_percent}% downhill gradient"
            return start_elev, end_elev, gradient_percent, reason

        # Case 4: No compatible manholes found
        else:
            start_elev = start_point.altitude
            end_elev = end_point.altitude

            elevation_diff = end_elev - start_elev
            gradient_percent = (elevation_diff / distance_2d) * 100 if distance_2d > 0 else 0

            if gradient_percent > 0:
                end_elev = start_elev - (self.params.min_gradient_percent / 100) * distance_2d
                gradient_percent = -self.params.min_gradient_percent
                reason = "Fixed uphill DGM gradient to proper downhill flow"
            else:
                reason = f"Kept DGM elevations with {gradient_percent:.2f}% gradient"

            return start_elev, end_elev, gradient_percent, reason

    def _apply_elevation_adjustment(
        self, pipeline: ObjectData, new_start_elevation: float, new_end_elevation: float
    ) -> None:
        """Apply elevation adjustments to pipeline."""
        # Update positions
        if len(pipeline.points) >= 2:
            start_pos = pipeline.points[0]
            end_pos = pipeline.points[1]

            new_start_pos = Point3D(start_pos.east, start_pos.north, new_start_elevation)
            pipeline.points[0] = new_start_pos
            new_end_pos = Point3D(end_pos.east, end_pos.north, new_end_elevation)
            pipeline.points[-1] = new_end_pos

        # Update intermediate points if they exist
        if pipeline.points and len(pipeline.points) > 2:
            self._interpolate_intermediate_points(pipeline, new_start_elevation, new_end_elevation)

    def _interpolate_intermediate_points(
        self, pipeline: ObjectData, start_elevation: float, end_elevation: float
    ) -> None:
        """Interpolate elevations for intermediate points."""
        if not pipeline.points or len(pipeline.points) < 3:
            return

        # Calculate distances
        total_distance = 0
        distances = [0.0]

        for idx in range(1, len(pipeline.points)):
            segment_distance = pipeline.points[idx - 1].distance_2d(pipeline.points[idx])
            total_distance += segment_distance
            distances.append(total_distance)

        # Interpolate elevations
        elevation_diff = end_elevation - start_elevation

        new_points = []
        for idx, point in enumerate(pipeline.points):
            if idx == 0:
                new_elevation = start_elevation
            elif idx == len(pipeline.points) - 1:
                new_elevation = end_elevation
            else:
                distance_ratio = distances[idx] / total_distance if total_distance > 0 else 0
                new_elevation = start_elevation + (elevation_diff * distance_ratio)

            new_point = Point3D(point.east, point.north, new_elevation)
            new_points.append(new_point)

        pipeline.points = new_points

    def generate_cover_height_report(self, cover_heights: list[CoverToPipeHeight]) -> dict[str, Any]:
        """Generate a report of cover-to-pipe height calculations."""
        if not cover_heights:
            return {
                "summary": "No cover height calculations performed",
                "total_shafts": 0,
                "compatibility_strategy": type(self.compatibility).__name__,
                "cover_heights": [],
            }

        # Separate shafts with and without connected pipes
        shafts_with_pipes = [ch for ch in cover_heights if ch.connected_pipes]
        shafts_without_pipes = [ch for ch in cover_heights if not ch.connected_pipes]

        # Calculate statistics
        height_differences = [ch.height_difference for ch in shafts_with_pipes if ch.height_difference is not None]
        avg_height_diff = sum(height_differences) / len(height_differences) if height_differences else 0
        min_height_diff = min(height_differences) if height_differences else 0
        max_height_diff = max(height_differences) if height_differences else 0

        return {
            "summary": f"Calculated cover heights for {len(cover_heights)} shafts ({len(shafts_with_pipes)} with pipes, {len(shafts_without_pipes)} isolated)",
            "total_shafts": len(cover_heights),
            "shafts_with_connected_pipes": len(shafts_with_pipes),
            "shafts_without_connected_pipes": len(shafts_without_pipes),
            "compatibility_strategy": type(self.compatibility).__name__,
            "height_statistics": {
                "average_cover_to_pipe_height_m": round(avg_height_diff, 3),
                "minimum_cover_to_pipe_height_m": round(min_height_diff, 3),
                "maximum_cover_to_pipe_height_m": round(max_height_diff, 3),
                "total_pipe_connections": sum(len(ch.connected_pipes) for ch in shafts_with_pipes),
            },
            "cover_heights": [
                {
                    "shaft_medium": ch.shaft.medium,
                    "shaft_layer": ch.shaft.layer,
                    "cover_elevation_m": round(ch.cover_elevation, 3),
                    "connected_pipes_count": len(ch.connected_pipes),
                    "lowest_pipe_medium": ch.lowest_pipe.medium if ch.lowest_pipe else None,
                    "lowest_pipe_elevation_m": round(ch.lowest_pipe_elevation, 3)
                    if ch.lowest_pipe_elevation is not None
                    else None,
                    "height_difference_m": round(ch.height_difference, 3) if ch.height_difference is not None else None,
                    "medium_compatibility": ch.medium_compatibility,
                }
                for ch in cover_heights
            ],
        }

    def generate_report(self, adjustments: list[PipelineAdjustment]) -> dict[str, Any]:
        """Generate a report of pipeline adjustments."""
        if not adjustments:
            return {
                "summary": "No pipeline adjustments needed",
                "total_adjustments": 0,
                "compatibility_strategy": type(self.compatibility).__name__,
                "adjustments": [],
            }

        # Group by medium
        medium_groups = {}
        for adj in adjustments:
            medium = adj.pipeline.medium
            if medium not in medium_groups:
                medium_groups[medium] = []
            medium_groups[medium].append(adj)

        total_elevation_change = sum(
            abs(adj.adjusted_start - adj.original_start) + abs(adj.adjusted_end - adj.original_end)
            for adj in adjustments
        )

        return {
            "summary": f"Adjusted {len(adjustments)} pipelines across {len(medium_groups)} mediums",
            "total_adjustments": len(adjustments),
            "medium_groups": list(medium_groups.keys()),
            "total_elevation_change_meters": round(total_elevation_change, 3),
            "average_gradient_percent": round(
                sum(adj.calculated_gradient for adj in adjustments) / len(adjustments), 2
            ),
            "adjustments_by_medium": {medium: len(adjs) for medium, adjs in medium_groups.items()},
            "adjustments": [
                {
                    "pipeline_medium": adj.pipeline.medium,
                    "pipeline_layer": adj.pipeline.layer,
                    "start_elevation_change": round(adj.adjusted_start - adj.original_start, 3),
                    "end_elevation_change": round(adj.adjusted_end - adj.original_end, 3),
                    "gradient_percent": round(adj.calculated_gradient, 2),
                    "reason": adj.adjustment_reason,
                }
                for adj in adjustments
            ],
        }
