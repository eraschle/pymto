"""Entity handler functions for DXF shape detection and classification.

This module provides functions to analyze DXF entities and determine their
shape characteristics (round, rectangular, multi-sided) and processing type.
"""

import itertools
import logging
import math
from typing import TypeGuard

import numpy as np
from ezdxf import math as ezmath
from ezdxf.entities.arc import Arc
from ezdxf.entities.circle import Circle
from ezdxf.entities.dxfentity import DXFEntity
from ezdxf.entities.insert import Insert
from ezdxf.entities.line import Line
from ezdxf.entities.lwpolyline import LWPolyline
from ezdxf.entities.polyline import Polyline
from ezdxf.math import Vec2, Vec3

from ..models import MediumConfig, ObjectType, Point3D

log = logging.getLogger(__name__)


def extract_points_from(entity: DXFEntity) -> list[Point3D]:
    """Extract coordinate points from any DXF entity.

    Parameters
    ----------
    entity : DXFEntity
        DXF entity to extract points from

    Returns
    -------
    List[Point3D]
        List of extracted points
    """
    point_values = []

    if isinstance(entity, Line):
        start = entity.dxf.start
        end = entity.dxf.end
        point_values = [
            Point3D(east=start.x, north=start.y, altitude=0.0),
            Point3D(east=end.x, north=end.y, altitude=0.0),
        ]
    elif isinstance(entity, Polyline):
        for point in entity.points():
            point_values.append(Point3D(east=point.x, north=point.y, altitude=0.0))
    elif isinstance(entity, LWPolyline):
        for point in entity.get_points("xy"):
            point_values.append(Point3D(east=point[0], north=point[1], altitude=0.0))
    elif isinstance(entity, Arc):
        src_length = get_arc_length(entity)
        return split_arc_to_points(entity, num_points=int(src_length / 0.2))
    elif isinstance(entity, Circle):
        center = entity.dxf.center
        point_values = [Point3D(east=center.x, north=center.y, altitude=0.0)]

    return point_values


def get_arc_length(arc: Arc) -> float:
    radius = arc.dxf.radius
    start_angle = math.radians(arc.dxf.start_angle)
    end_angle = math.radians(arc.dxf.end_angle)
    if end_angle < start_angle:
        end_angle += 2 * math.pi
    return radius * (end_angle - start_angle)


def split_arc_to_points(arc: Arc, num_points: int | None = None, spacing: float | None = None) -> list[Point3D]:
    """Split an ARC into points"""
    center = Vec3(arc.dxf.center)
    radius = arc.dxf.radius
    start_angle = math.radians(arc.dxf.start_angle)
    end_angle = math.radians(arc.dxf.end_angle)

    # Handle angle wraparound
    if end_angle < start_angle:
        end_angle += 2 * math.pi

    if num_points:
        angles = np.linspace(start_angle, end_angle, num_points)
    elif spacing:
        arc_length = get_arc_length(arc)
        num_points = int(arc_length / spacing) + 1
        angles = np.linspace(start_angle, end_angle, num_points)
    else:
        angles = []

    points = []
    for angle in angles:
        x = center.x + radius * math.cos(angle)
        y = center.y + radius * math.sin(angle)
        z = center.z
        points.append(Point3D(east=x, north=y, altitude=z))
    return points


def get_default_point_diameter(object_type: ObjectType, config: MediumConfig) -> float:
    diameter = config.default_diameter or 0.0
    if diameter == 0 and object_type == ObjectType.SHAFT:
        diameter = 1.0
    return diameter


def has_bulge_value(entity: DXFEntity) -> bool:
    """Check if a polyline entity has bulge values.

    Parameters
    ----------
    entity : DXFEntity
        Entity to check

    Returns
    -------
    bool
        True if entity has bulge values
    """
    if not isinstance(entity, LWPolyline):
        return False
    return any(point[-1] != 0.0 for point in entity.get_points())


def _get_bulge_start_index(entity: LWPolyline) -> int:
    for idx, point_values in enumerate(entity.get_points()):
        if point_values[-1] == 0.0:
            continue
        return idx
    raise ValueError("No bulge found in polyline entity.")


def get_bulge_center_and_diameter(entity: DXFEntity) -> tuple[Point3D, float]:
    """Get the center point and diameter of a bulge in a polyline."""
    if not isinstance(entity, LWPolyline):
        raise TypeError("Entity must be a LWPolyline with bulge values.")
    if not has_bulge_value(entity):
        raise ValueError("Entity does not have bulge values. Did you check with has_bulge_value?")
    points_vec2 = entity.get_points("xy")
    start_index = _get_bulge_start_index(entity)
    start = points_vec2[start_index]
    end = points_vec2[(start_index + 1) % len(points_vec2)]
    bulge_value = entity.get_points()[start_index][-1]
    center = ezmath.bulge_center(start_point=start, end_point=end, bulge=bulge_value)
    radius = ezmath.bulge_radius(start_point=start, end_point=end, bulge=bulge_value)
    return (
        Point3D(east=center.x, north=center.y, altitude=0.0),
        radius * 2.0,  # Diameter
    )


def is_closed_polyline(entity: DXFEntity) -> bool:
    """Check if a polyline entity is closed.

    Parameters
    ----------
    entity : DXFEntity
        Entity to check

    Returns
    -------
    bool
        True if polyline is closed
    """
    if isinstance(entity, (Polyline | LWPolyline)):
        return getattr(entity, "is_closed", False)
    return False


DXFLine = Line | LWPolyline | Polyline


def is_dxf_line(entity: DXFEntity) -> TypeGuard[DXFLine]:
    """Check if a DXF entity is a line or polyline.

    Parameters
    ----------
    entity : DXFEntity
        Entity to check

    Returns
    -------
    bool
        True if entity is a Line or LWPolyline
    """
    return isinstance(entity, (Line | LWPolyline | Polyline))


def get_dxf_lines(entities: list[DXFEntity]) -> list[DXFLine]:
    """Get all DXF lines from a list of entities.

    Parameters
    ----------
    entities : List[DXFEntity]
        List of DXF entities to filter

    Returns
    -------
    List[DXFLine]
        List of DXF lines (Line or LWPolyline)
    """
    return [entity for entity in entities if is_dxf_line(entity)]


def get_group_extent(group: list[DXFLine]) -> float:
    """Calculate the extent of a group of DXF lines.

    Parameters
    ----------
    group : List[DXFLine]
        Group of DXF lines to calculate extent for

    Returns
    -------
    float
        Extent of the group in 2D space
    """
    extent = 0.0
    for line in group:
        if isinstance(line, Line):
            extent += get_distance(line.dxf.start, line.dxf.end)
        elif isinstance(line, LWPolyline):
            extent += get_lwpolyline_length(line)
        elif isinstance(line, Polyline):
            extent += get_polyline_length(line)
    return extent


def _is_within_point(point: Vec2, other: Vec2, threshold: float) -> bool:
    """Check if two points are within a specified distance threshold.

    Parameters
    ----------
    point : Vec2
        First point to check
    other : Vec2
        Second point to check against the first
    threshold : float
        Distance threshold to consider the points "at" each other

    Returns
    -------
    bool
        True if the points are within the threshold distance
    """
    return point.distance(other) <= threshold


def _is_line_start_or_end(line: DXFLine, point: Vec2, threshold: float) -> bool:
    """Check if a line starts or ends at a specific point within a threshold.

    Parameters
    ----------
    line : DXFLine
        Line entity to check
    point : Vec2
        Point to check against the line
    threshold : float, optional
        Distance threshold to consider the point "at" the line

    Returns
    -------
    bool
        True if the line is at the specified point within the threshold
    """
    start, end = _get_start_end_endpoint(line)
    return _is_within_point(start, point, threshold) or _is_within_point(end, point, threshold)


def _next_group_line(lines: list[DXFLine], point: Vec2, used_lines: set[DXFLine], threshold: float) -> DXFLine | None:
    """Find the next line that starts or ends at a specific point.

    Parameters
    ----------
    lines : List[DXFLine]
        List of DXF lines to search
    point : Vec2
        Point to check against the lines
    used_lines : set[DXFLine]
        Set of already used lines to avoid duplicates
    threshold : float
        Distance threshold to consider the point "at" the line

    Returns
    -------
    DXFLine | None
        The next line that starts or ends at the specified point, or None if not found
    """
    for line in lines:
        if line in used_lines:
            continue
        if not _is_line_start_or_end(line, point, threshold):
            continue
        used_lines.add(line)
        return line
    return None


def _get_start_end_endpoint(line: DXFLine) -> tuple[Vec2, Vec2]:
    """Get the start and end points of a DXF line.

    Parameters
    ----------
    line : DXFLine
        Line entity to extract points from

    Returns
    -------
    Tuple[Vec2, Vec2]
        Start and end points of the line
    """
    if isinstance(line, Line):
        return Vec2(line.dxf.start), Vec2(line.dxf.end)
    elif isinstance(line, LWPolyline):
        points = line.get_points("xy")
        return Vec2(points[0]), Vec2(points[-1])
    elif isinstance(line, Polyline):
        points = list(line.points())
        return points[0].vec2, points[-1].vec2
    raise TypeError("Unsupported line type. Expected Line or LWPolyline.")


def group_lines_by_points(lines: list[DXFLine], threshold: float) -> list[list[DXFLine]]:
    """Group lines by their start and end points.

    Parameters
    ----------
    lines : List[DXFLine]
        List of DXF lines to group
    threshold : float
        Distance threshold to consider the point "at" the line

    Returns
    -------
    List[List[DXFLine]]
        List of grouped lines
    """
    grouped_lines = []
    used_lines = set()

    for line in lines:
        if line in used_lines:
            continue

        group = [line]
        used_lines.add(line)

        _, end_point = _get_start_end_endpoint(line)
        while next_line := _next_group_line(lines, end_point, used_lines, threshold):
            group.append(next_line)
            used_lines.add(next_line)
            next_start, next_end = _get_start_end_endpoint(next_line)
            if _is_within_point(end_point, next_start, threshold):
                end_point = next_end
            else:
                end_point = next_start

        grouped_lines.append(group)

    return grouped_lines


def _is_rectangular_group(group: list[DXFLine]) -> bool:
    """Check if a group of lines forms a rectangular shape.

    Parameters
    ----------
    group : List[DXFLine]
        Group of DXF lines to check
    threshold : float
        Distance threshold to consider the point "at" the line

    Returns
    -------
    bool
        True if the group forms a rectangle, False otherwise
    """
    points = set()
    for line in group:
        points.update(extract_points_from(line))
    return len(points) == 4


def find_rectangles_from_groups(groups: list[list[DXFLine]]) -> list[list[DXFLine]]:
    """Find rectangles from grouped lines.

    Parameters
    ----------
    groups : List[List[DXFLine]]
        List of grouped lines
    threshold : float
        Distance threshold to consider the point "at" the line

    Returns
    -------
    List[List[DXFLine]]
        List of groups that form rectangles
    """
    rectangles = []
    for group in groups:
        if not _is_rectangular_group(group):
            continue
        rectangles.append(group)

    return rectangles


def detect_shape_type(points: list[Point3D]) -> str:
    """Detect the geometric shape type from a list of points.

    Parameters
    ----------
    points : List[Point3D]
        List of points defining the shape

    Returns
    -------
    str
        Shape type: 'rectangular', 'round', 'multi_sided', or 'linear'
    """
    num_points = len(points)

    if num_points < 2:
        return "point"
    elif num_points == 2:
        return "linear"
    elif num_points == 3:
        if has_bulge_value(points):
            return "bulge"  # Assume 3 points must be a bulge or arc
        else:
            return "triangle"  # 3 points can only form a triangle
    elif is_near_circular(points):
        return "round"
    elif num_points == 4 and is_rectangular(points):
        return "rectangular"
    elif num_points >= 4:
        return "multi_sided"
    raise ValueError(f"Cannot determine shape type from points: {num_points} points provided, expected at least 2.")


def get_angle_from_entity(entity: Insert) -> float:
    """Get the angle of a DXF entity if available.

    Parameters
    ----------
    entity : DXFEntity
        Entity to extract angle from

    Returns
    -------
    float
        Angle in degrees, or 0.0 if not applicable
    """
    try:
        return entity.dxf.rotation
        # return entity.dxf.insert.angle_deg
    except AttributeError:
        return 0.0


def get_distance(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    """Calculate the distance between two points in 2D space.

    Parameters
    ----------
    p1 : Tuple[float, float]
        First point (x1, y1)
    p2 : Tuple[float, float]
        Second point (x2, y2)

    Returns
    -------
    float
        Distance between the two points
    """
    return math.sqrt((p2[0] - p1[0]) ** 2 + (p2[1] - p1[1]) ** 2)


def get_lwpolyline_length(polyline: LWPolyline) -> float:
    """Calculate the length of a polyline"""
    length = 0.0
    points = polyline.get_points("xy")
    for idx, point in enumerate(points):
        if idx == 0:
            continue
        length += get_distance(points[idx - 1], point)  # type: ignore

    return length


def get_polyline_length(polyline: Polyline) -> float:
    """Calculate the length of a polyline"""
    length = 0.0
    points = polyline.points()
    for idx, point in enumerate(points):
        if idx == 0:
            continue
        length += get_distance(points[idx - 1], point)  # type: ignore

    return length


def get_lw_polyline_angle(self, polyline: LWPolyline) -> float:
    """get angle of two points in polyline"""
    with polyline.points() as points:
        p1 = (points[0][0], points[0][1])
        p2 = (points[-1][0], points[-1][1])
        angle = self.get_points_angle(p1, p2)

    return angle


def get_angle_point_on_line(
    line: Line | LWPolyline, point: tuple[float, float], threshold: float = 0.5
) -> float | None:
    """get angle of point on line or polyline"""
    if isinstance(line, Line):
        angle = get_line_angle(line)
        return angle

    entity_points: list[tuple[float, float]] = line.get_points("xy")  # type: ignore
    for idx, start_point in enumerate(entity_points):
        try:
            end_point = entity_points[idx + 1]
        except IndexError:
            continue

        if ezmath.is_point_on_line_2d(Vec2(point), Vec2(start_point), Vec2(end_point), ray=False, abs_tol=threshold):
            angle = get_points_angle(start_point, end_point)
            return angle

    return None


def get_parallel_angle(lines: list[Line]) -> float | None:
    """get the angle of first two parallel lines"""
    all_angles = [get_line_angle(i) for i in lines]
    all_round = [round(i) for i in all_angles]

    for idx, rounded in enumerate(all_round):
        if all_round.count(rounded) > 1:
            return all_angles[idx]

    return None


def get_line_angle(line: Line) -> float:
    """get angle of line"""
    p1 = line.dxf.start[0], line.dxf.start[1]
    p2 = line.dxf.end[0], line.dxf.end[1]
    angle = get_points_angle(p1, p2)

    return angle


def get_points_angle(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    """get angle from two line coordinates"""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.degrees(math.atan2(dy, dx))


def get_angle_to_line(self, dxf_layers: list[str], dfa_dict: dict, threshold: float) -> float | None:
    """get angle relative to line"""
    entities = self.get_entities_by_layer(dxf_layers)
    point = (dfa_dict["E"], dfa_dict["N"])
    nearest_entity = self.find_nearest_line_polyline(entities, point, threshold=threshold)
    if not nearest_entity:
        return None


def calculate_angle_from_points(points: list[Point3D]) -> float:
    point_pairs = []
    for start, end in itertools.pairwise(points):
        point_pairs.append((start, end))

    lengths = [start.distance_2d(end) for start, end in point_pairs]
    max_length_index = lengths.index(max(lengths))
    start_point, end_point = point_pairs[max_length_index]
    return get_points_angle(start_point.to_tuple(), end_point.to_tuple())


def is_rectangular(points: list[Point3D]) -> bool:
    """Check if 4 points form a rectangular shape.

    Parameters
    ----------
    points : List[Point3D]
        List of 4 points

    Returns
    -------
    bool
        True if points form a rectangle
    """
    if len(points) != 4:
        return False

    # Check if diagonals are equal (rectangle property)
    diagonal1 = points[0].distance_2d(points[2])
    diagonal2 = points[1].distance_2d(points[3])

    return abs(diagonal1 - diagonal2) < 1e-6


def is_near_circular(points: list[Point3D]) -> bool:
    """Check if points form a near-circular shape (regular polygon with many sides).

    Parameters
    ----------
    points : List[Point3D]
        List of points defining the shape

    Returns
    -------
    bool
        True if shape is approximately circular
    """
    if len(points) < 6:
        return False

    # Calculate center point
    center_x = sum(p.east for p in points) / len(points)
    center_y = sum(p.north for p in points) / len(points)
    center = Point3D(east=center_x, north=center_y, altitude=0.0)

    # Check if all points are approximately equidistant from center
    distances = [center.distance_2d(p) for p in points]
    avg_distance = sum(distances) / len(distances)

    # Check variance in distances (should be small for circular shapes)
    variance = sum((d - avg_distance) ** 2 for d in distances) / len(distances)

    # If variance is small relative to average distance, it's circular
    return variance < (avg_distance * 0.1) ** 2


def has_diagonal_cross(entity: DXFEntity, block_entities: list[DXFEntity] | None = None) -> bool:
    """Check if an entity or block contains diagonal cross lines.

    Parameters
    ----------
    entity : DXFEntity
        Main entity to check
    block_entities : List[DXFEntity], optional
        Additional entities from block definition

    Returns
    -------
    bool
        True if entity contains diagonal cross pattern
    """
    all_entities = [entity]
    if block_entities:
        all_entities.extend(block_entities)

    # Extract all line segments
    line_segments = []
    for ent in all_entities:
        if isinstance(ent, Line):
            start = ent.dxf.start
            end = ent.dxf.end
            line_segments.append(((start.x, start.y), (end.x, end.y)))

    if len(line_segments) < 2:
        return False

    # Check for diagonal patterns
    # This is a simplified check - could be made more sophisticated
    diagonal_count = 0
    for i, line1 in enumerate(line_segments):
        for line2 in line_segments[i + 1 :]:
            if are_crossing_diagonals(line1, line2):
                diagonal_count += 1

    return diagonal_count >= 1


def are_crossing_diagonals(
    line1: tuple[tuple[float, float], tuple[float, float]],
    line2: tuple[tuple[float, float], tuple[float, float]],
) -> bool:
    """Check if two line segments form crossing diagonals.

    Parameters
    ----------
    line1, line2 : Tuple[Tuple[float, float], Tuple[float, float]]
        Line segments defined by start and end points

    Returns
    -------
    bool
        True if lines are crossing diagonals
    """
    # Simple check: lines should intersect and have different slopes
    # This is a simplified implementation
    (x1, y1), (x2, y2) = line1
    (x3, y3), (x4, y4) = line2

    # Calculate slopes
    try:
        slope1 = (y2 - y1) / (x2 - x1) if x2 != x1 else float("inf")
        slope2 = (y4 - y3) / (x4 - x3) if x4 != x3 else float("inf")

        # Check if slopes are significantly different (not parallel)
        if abs(slope1 - slope2) > 0.1:
            return True
    except ZeroDivisionError:
        pass

    return False


def calculate_bbox_dimensions(points: list[Point3D]) -> tuple[float, float]:
    """Calculate length and width from bounding box of points.

    Parameters
    ----------
    points : List[Point3D]
        List of points

    Returns
    -------
    Tuple[float, float]
        Length and width of bounding box
    """
    east_min = min(p.east for p in points)
    east_max = max(p.east for p in points)
    north_min = min(p.north for p in points)
    north_max = max(p.north for p in points)

    length = east_max - east_min
    width = north_max - north_min

    return length, width


def calculate_rect_dimensions(points: list[Point3D]) -> tuple[float, float]:
    """Calculate precise rectangular dimensions from 4 corner points.

    Parameters
    ----------
    points : List[Point3D]
        List of 4 corner points

    Returns
    -------
    Tuple[float, float]
        Length and width of rectangle
    """
    point_pairs = []
    for point, other in itertools.pairwise(points):
        point_pairs.append((point, other))

    side_lengths = []
    for point, other in point_pairs:
        side_length = point.distance_2d(other)
        side_lengths.append(side_length)
    return max(side_lengths), min(side_lengths)


def calculate_center_point(points: list[Point3D]) -> Point3D:
    """Calculate center point (centroid) of a list of points.

    Parameters
    ----------
    points : List[Point3D]
        List of points

    Returns
    -------
    Point3D
        Center point
    """
    if not points:
        return Point3D(east=0.0, north=0.0, altitude=0.0)

    center_x = sum(p.east for p in points) / len(points)
    center_y = sum(p.north for p in points) / len(points)
    center_z = sum(p.altitude for p in points) / len(points)

    return Point3D(east=center_x, north=center_y, altitude=center_z)


def estimate_diameter_from(points: list[Point3D]) -> float:
    """Estimate diameter of a polygonal shape (for near-circular shapes).

    Parameters
    ----------
    points : List[Point3D]
        List of points defining the polygon

    Returns
    -------
    float
        Estimated diameter
    """
    if not points:
        return 0.0

    center = calculate_center_point(points)

    # Calculate average distance from center to vertices
    distances = [center.distance_2d(p) for p in points]
    avg_radius = sum(distances) / len(distances)

    return avg_radius * 2.0


def is_element_entity(entity: DXFEntity) -> bool:
    """Determine if a DXF entity should be processed as an element (shaft).

    Elements are typically point-based objects like shafts, distributors, etc.
    Lines are typically pipe segments.

    Parameters
    ----------
    entity : DXFEntity
        DXF entity to classify

    Returns
    -------
    bool
        True if entity should be processed as element
    """
    entity_type = entity.dxftype()

    # Block references (INSERT) are always elements
    if entity_type == "INSERT":
        return True

    # Circles are always elements (round shafts)
    if entity_type == "CIRCLE":
        return True

    # For polylines, check complexity and closure
    if entity_type in ("POLYLINE", "LWPOLYLINE"):
        # Closed polylines are typically elements
        if is_closed_polyline(entity):
            return True

        # Complex polylines (4+ points) are likely elements
        points = extract_points_from(entity)
        if len(points) >= 4:
            return True

    # Simple lines and short polylines are typically pipes
    return False


def is_text_entity(entity: DXFEntity) -> bool:
    """Determine if a DXF entity should be processed as text.

    Parameters
    ----------
    entity : DXFEntity
        DXF entity to classify

    Returns
    -------
    bool
        True if entity should be processed as teo
    """
    entity_type = entity.dxftype()
    return entity_type in ("TEXT", "MTEXT", "ATTRIB", "ATTDEF", "DIMENSION")
