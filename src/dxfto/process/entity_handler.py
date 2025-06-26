"""Entity handler functions for DXF shape detection and classification.

This module provides functions to analyze DXF entities and determine their
shape characteristics (round, rectangular, multi-sided) and processing type.
"""

import logging

from ezdxf.entities.circle import Circle
from ezdxf.entities.dxfentity import DXFEntity
from ezdxf.entities.line import Line
from ezdxf.entities.lwpolyline import LWPolyline
from ezdxf.entities.polyline import Polyline

from ..models import MediumConfig, Point3D, ShapeType

log = logging.getLogger(__name__)


def extract_points_from_entity(entity: DXFEntity) -> list[Point3D]:
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
    points = []

    if isinstance(entity, Line):
        start = entity.dxf.start
        end = entity.dxf.end
        points = [
            Point3D(east=start.x, north=start.y, altitude=0.0),
            Point3D(east=end.x, north=end.y, altitude=0.0),
        ]
    elif isinstance(entity, Polyline):
        for point in entity.points():
            points.append(Point3D(east=point.x, north=point.y, altitude=0.0))
    elif isinstance(entity, LWPolyline):
        for point in entity.get_points("xy"):
            points.append(Point3D(east=point[0], north=point[1], altitude=0.0))
    elif isinstance(entity, Circle):
        # For circles, return center point
        center = entity.dxf.center
        points = [Point3D(east=center.x, north=center.y, altitude=0.0)]

    return points


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
    elif num_points < 4:
        return "linear"
    elif num_points == 4 and is_rectangular_shape(points):
        return "rectangular"
    elif is_closed_shape(points):
        return "multi_sided"
    elif is_near_circular_shape(points):
        return "round"
    raise ValueError(
        "Cannot determine shape type from points: "
        f"{num_points} points provided, expected at least 2."
    )


def is_rectangular_shape(points: list[Point3D]) -> bool:
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

def is_closed_shape(points: list[Point3D]) -> bool:
    """Check if a shape defined by points is closed (first point == last point).

    Parameters
    ----------
    points : List[Point3D]
        List of points defining the shape

    Returns
    -------
    bool
        True if shape is closed
    """
    if len(points) < 3:
        return False

    # Check if first and last points are the same
    return points[0].distance_2d(points[-1]) < 1e-6

def is_near_circular_shape(points: list[Point3D]) -> bool:
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


def calculate_bounding_box_dimensions(points: list[Point3D]) -> tuple[float, float]:
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
    if not points:
        return 0.0, 0.0

    east_min = min(p.east for p in points)
    east_max = max(p.east for p in points)
    north_min = min(p.north for p in points)
    north_max = max(p.north for p in points)

    length = east_max - east_min
    width = north_max - north_min

    return length, width


def calculate_precise_rectangular_dimensions(points: list[Point3D]) -> tuple[float, float]:
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
    if len(points) != 4:
        return calculate_bounding_box_dimensions(points)

    # Calculate side lengths
    side1 = points[0].distance_2d(points[1])
    side2 = points[1].distance_2d(points[2])

    # Return length (max) and width (min)
    length = max(side1, side2)
    width = min(side1, side2)

    return length, width


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


def estimate_diameter_from_polygon(points: list[Point3D]) -> float:
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
        points = extract_points_from_entity(entity)
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
