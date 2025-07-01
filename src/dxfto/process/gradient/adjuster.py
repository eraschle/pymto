"""Pipeline gradient adjustment for medium-compatible flow systems.

This module provides functionality to adjust pipeline elevations based on
connected manhole elevations, with configurable medium compatibility strategies.
"""

import logging
from dataclasses import dataclass
from typing import Any


from ...models import ObjectData, ObjectType, Point3D
from .compatibilty import IMediumCompatibilityStrategy, PrefixBasedCompatibility

log = logging.getLogger(__name__)


@dataclass
class GradientAdjustmentParams:
    """Parameters for gradient adjustment."""

    manhole_search_radius: float = 3.0  # Radius to find connected manholes (meters)
    min_gradient_percent: float = 0.5  # Minimum gradient to enforce
    max_gradient_percent: float = 12.0  # Maximum gradient to allow


@dataclass
class PipelineAdjustment:
    """Record of a pipeline adjustment."""

    pipeline: ObjectData
    start_manhole: ObjectData | None
    end_manhole: ObjectData | None
    original_start: float
    original_end: float
    adjusted_start: float
    adjusted_end: float
    calculated_gradient: float
    adjustment_applied: bool
    adjustment_reason: str
    medium_compatibility: str


class PipelineGradientAdjuster:
    """Adjusts pipeline gradients with configurable medium compatibility strategies."""

    def __init__(
        self,
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
        return obj.object_type in {ObjectType.SHAFT, ObjectType.WASTE_WATER_SPECIAL, ObjectType.WATER_SPECIAL}

    def _adjust_single_pipeline(self, pipeline: ObjectData, manholes: list[ObjectData]) -> PipelineAdjustment | None:
        """Adjust elevation for a single pipeline based on compatible manholes."""
        if not pipeline.is_line_based or len(pipeline.positions) != 2:
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

        # Calculate new elevations
        new_start_elev, new_end_elev, gradient_perc, reason = self._calculate_elevations(
            start_point, end_point, start_shaft, end_shaft
        )

        # Create compatibility description
        compatibility_desc = self._describe_compatibility(pipeline, start_shaft, end_shaft)

        # Check if adjustment is needed
        elevation_tolerance = 0.05  # 5cm tolerance
        start_needs_adjust = abs(new_start_elev - orig_start_elev) > elevation_tolerance
        end_needs_adjust = abs(new_end_elev - orig_end_elev) > elevation_tolerance

        if start_needs_adjust or end_needs_adjust:
            # Apply the adjustment
            self._apply_elevation_adjustment(pipeline, new_start_elev, new_end_elev)

            return PipelineAdjustment(
                pipeline=pipeline,
                start_manhole=start_shaft,
                end_manhole=end_shaft,
                original_start=orig_start_elev,
                original_end=orig_end_elev,
                adjusted_start=new_start_elev,
                adjusted_end=new_end_elev,
                calculated_gradient=gradient_perc,
                adjustment_applied=True,
                adjustment_reason=reason,
                medium_compatibility=compatibility_desc,
            )

        return None

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

    def _calculate_elevations(
        self, start_point: Point3D, end_point: Point3D, start_manhole: ObjectData | None, end_manhole: ObjectData | None
    ) -> tuple[float, float, float, str]:
        """Calculate new pipeline elevations based on connected manholes."""
        distance_2d = start_point.distance_2d(end_point)

        # Case 1: Both manholes found
        if start_manhole and end_manhole:
            start_elev = start_manhole.point.altitude
            end_elev = end_manhole.point.altitude

            elevation_diff = end_elev - start_elev
            gradient_percent = (elevation_diff / distance_2d) * 100 if distance_2d > 0 else 0

            if abs(gradient_percent) < self.params.min_gradient_percent:
                min_drop = (self.params.min_gradient_percent / 100) * distance_2d
                end_elev = start_elev - min_drop
                gradient_percent = -self.params.min_gradient_percent
                reason = f"Enforced minimum gradient {self.params.min_gradient_percent}%"
            elif gradient_percent > self.params.max_gradient_percent:
                max_drop = (self.params.max_gradient_percent / 100) * distance_2d
                end_elev = start_elev - max_drop
                gradient_percent = -self.params.max_gradient_percent
                reason = f"Limited to maximum gradient {self.params.max_gradient_percent}%"
            elif gradient_percent > 0:
                end_elev = start_elev - (self.params.min_gradient_percent / 100) * distance_2d
                gradient_percent = -self.params.min_gradient_percent
                reason = "Reversed uphill flow to create proper downhill gradient"
            else:
                reason = f"Used compatible manhole elevations with {gradient_percent:.2f}% gradient"

            return start_elev, end_elev, gradient_percent, reason

        # Case 2: Only start manhole found
        elif start_manhole:
            start_elev = start_manhole.point.altitude
            min_drop = (self.params.min_gradient_percent / 100) * distance_2d
            end_elev = start_elev - min_drop
            gradient_percent = -self.params.min_gradient_percent
            reason = f"Used compatible start manhole, applied {self.params.min_gradient_percent}% downhill gradient"
            return start_elev, end_elev, gradient_percent, reason

        # Case 3: Only end manhole found
        elif end_manhole:
            end_elev = end_manhole.point.altitude
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
        if len(pipeline.positions) >= 2:
            start_pos = pipeline.positions[0]
            end_pos = pipeline.positions[1]

            new_start_pos = Point3D(start_pos.east, start_pos.north, new_start_elevation)
            new_end_pos = Point3D(end_pos.east, end_pos.north, new_end_elevation)

            pipeline.positions = (new_start_pos, new_end_pos)

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

        for i in range(1, len(pipeline.points)):
            segment_distance = pipeline.points[i - 1].distance_2d(pipeline.points[i])
            total_distance += segment_distance
            distances.append(total_distance)

        # Interpolate elevations
        elevation_diff = end_elevation - start_elevation

        new_points = []
        for i, point in enumerate(pipeline.points):
            if i == 0:
                new_elevation = start_elevation
            elif i == len(pipeline.points) - 1:
                new_elevation = end_elevation
            else:
                distance_ratio = distances[i] / total_distance if total_distance > 0 else 0
                new_elevation = start_elevation + (elevation_diff * distance_ratio)

            new_point = Point3D(point.east, point.north, new_elevation)
            new_points.append(new_point)

        pipeline.points = new_points

    def generate_report(self, adjustments: list[PipelineAdjustment]) -> dict[str, Any]:
        """Generate a report of pipeline adjustments."""
        if not adjustments:
            return {
                "summary": "No pipeline adjustments needed",
                "total_adjustments": 0,
                "compatibility_strategy": type(self.compatibility).__name__,
                "adjustments": [],
            }

        # Group by compatibility groups
        compatibility_groups = {}
        for adj in adjustments:
            group = self.compatibility.get_group(adj.pipeline.medium)
            if group not in compatibility_groups:
                compatibility_groups[group] = []
            compatibility_groups[group].append(adj)

        total_elevation_change = sum(
            abs(adj.adjusted_start - adj.original_start) + abs(adj.adjusted_end - adj.original_end)
            for adj in adjustments
        )

        return {
            "summary": f"Adjusted {len(adjustments)} pipelines across {len(compatibility_groups)} compatibility groups",
            "total_adjustments": len(adjustments),
            "compatibility_strategy": type(self.compatibility).__name__,
            "compatibility_groups": list(compatibility_groups.keys()),
            "total_elevation_change_meters": round(total_elevation_change, 3),
            "average_gradient_percent": round(
                sum(adj.calculated_gradient for adj in adjustments) / len(adjustments), 2
            ),
            "adjustments_by_group": {group: len(adjs) for group, adjs in compatibility_groups.items()},
            "adjustments": [
                {
                    "pipeline_medium": adj.pipeline.medium,
                    "pipeline_layer": adj.pipeline.layer,
                    "medium_compatibility": adj.medium_compatibility,
                    "start_elevation_change": round(adj.adjusted_start - adj.original_start, 3),
                    "end_elevation_change": round(adj.adjusted_end - adj.original_end, 3),
                    "gradient_percent": round(adj.calculated_gradient, 2),
                    "reason": adj.adjustment_reason,
                    "start_manhole_connected": adj.start_manhole is not None,
                    "end_manhole_connected": adj.end_manhole is not None,
                }
                for adj in adjustments
            ],
        }
