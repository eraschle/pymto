"""Factory for creating ObjectData instances from DXF entities.

This module provides a factory pattern for creating ObjectData objects
from various DXF entity types with intelligent shape detection and
dimension calculation.
"""

import logging

from ezdxf.document import Drawing
from ezdxf.entities.arc import Arc
from ezdxf.entities.circle import Circle
from ezdxf.entities.dxfentity import DXFEntity
from ezdxf.entities.insert import Insert
from ezdxf.entities.lwpolyline import LWPolyline
from ezdxf.entities.polyline import Polyline

from ..models import (
    Dimension,
    MediumConfig,
    ObjectData,
    Parameter,
    Point3D,
    ShapeType,
    ValueType,
)
from . import entity_handler as dxf

log = logging.getLogger(__name__)


def _get_default_line_dimension(config: MediumConfig, fallback_diameter: float = 0.1) -> Dimension:
    if config.default_diameter is None:
        log.debug(f"No default diameter set in {config.medium}-config, using fallback {fallback_diameter} m")
        diameter = fallback_diameter
    else:
        diameter = config.default_diameter
    return Dimension(diameter=diameter, height=config.default_height, shape=ShapeType.ROUND)


def _get_default_rectangular_dimension(
    config: MediumConfig, fallback_width: float = 0.1, fallback_depth: float = 0.1, angle: float = 0.0
) -> Dimension:
    if config.default_width is None:
        log.debug(f"No default diameter set in {config.medium}-config, using fallback {fallback_width} m")
        width = fallback_width
    else:
        width = config.default_diameter
    if config.default_depth is None:
        log.debug(f"No default depth set in {config.medium}-config, using fallback {fallback_depth} m")
        depth = fallback_depth
    else:
        depth = config.default_depth
    return Dimension(
        width=width,
        depth=depth,
        height=config.default_height,
        angle=angle,
        shape=ShapeType.RECTANGULAR,
    )


def get_object(entity: DXFEntity, config: MediumConfig, dimension: Dimension, points: list[Point3D]) -> ObjectData:
    """Get the object ID from the configuration.

    Parameters
    ----------
    entity : DXFEntity
        The DXF entity to process
    config : MediumConfig
        Configuration for medium processing
    dimension : Dimension
        Dimension of the object
    points : List[Point3D]
        Points defining the object geometry

    Returns
    -------
    ObjectData
        Created ObjectData with the specified parameters
    """
    return ObjectData(
        uuid=str(entity.uuid),
        medium=config.medium,
        object_type=config.object_type,
        family=config.family,
        family_type=config.family_type,
        dimension=dimension,
        points=points,
        parameters=[
            Parameter(
                name="FDK_ID",
                value=config.object_id,
                value_type=ValueType.STRING,
            ),
            Parameter(
                name="Layer-Name",
                value=getattr(entity.dxf, "layer", "0"),
                value_type=ValueType.STRING,
            ),
        ],
    )


class ObjectDataFactory:
    """Factory for creating ObjectData from DXF entities."""

    def __init__(self, dxf_document: Drawing):
        self.dxf_doc = dxf_document
        self._block_cache = {}

    def create_from_entity(self, entity: DXFEntity, config: MediumConfig) -> ObjectData | None:
        """Create ObjectData from any DXF entity.

        Parameters
        ----------
        entity : DXFEntity
            DXF entity to process
        config : MediumConfig
            Configuration for medium processing

        Returns
        -------
        Optional[ObjectData]
            Created ObjectData or None if processing failed
        """
        try:
            entity_type = entity.dxftype()

            if entity_type == "HATCH":
                return None  # HATCH entities are not processed here
            if entity_type == "INSERT":
                return self._create_from_insert(entity, config)
            elif entity_type == "CIRCLE":
                return self._create_from_circle(entity, config)
            elif entity_type in "POLYLINE":
                return self._create_from_polyline(entity, config)
            elif entity_type in "LWPOLYLINE":
                return self._create_from_lw_polyline(entity, config)
            elif entity_type == "LINE":
                return self._create_from_line(entity, config)
            elif entity_type == "ARC":
                return self._create_from_arc(entity, config)
            else:
                log.warning(f"Unsupported entity type: {entity_type}")
                return None

        except Exception as e:
            log.error(f"Failed to create ObjectData from {entity.dxftype()}: {e}")
            return None

    def _create_from_insert(self, entity: DXFEntity, config: MediumConfig) -> ObjectData | None:
        """Create ObjectData from INSERT entity (block reference).

        Parameters
        ----------
        entity : Insert
            INSERT entity to process
        config : MediumConfig
            Configuration for medium processing

        Returns
        -------
        Optional[ObjectData]
            Created ObjectData or None if processing failed
        """
        if not isinstance(entity, Insert):
            log.error("Expected INSERT entity for block reference")
            return None
        try:
            insert_point = entity.dxf.insert
            position = Point3D(east=insert_point.x, north=insert_point.y, altitude=0.0)

            block_entities = self._get_block_entities(entity)
            shape_analysis = self._analyze_block_shape(entity, block_entities)

            if shape_analysis is None:
                return None

            dimension, _ = shape_analysis
            return get_object(
                config=config,
                entity=entity,
                dimension=dimension,
                points=[position],
            )
        except Exception as e:
            log.error(f"Failed to process INSERT entity: {e}")
            return None

    def _create_from_circle(self, entity: DXFEntity, config: MediumConfig) -> ObjectData | None:
        if not isinstance(entity, Circle):
            log.error("Expected CIRCLE entity")
            return None
        try:
            center = entity.dxf.center
            radius = entity.dxf.radius

            position = Point3D(east=center.x, north=center.y, altitude=0.0)
            diameter = radius * 2.0
            dimension = Dimension(diameter=diameter / 1000.0, shape=ShapeType.ROUND, angle=0.0)

            return get_object(
                config=config,
                entity=entity,
                dimension=dimension,
                points=[position],
            )

        except Exception as e:
            log.error(f"Failed to process CIRCLE entity: {e}")
            return None

    def _create_from_polyline(self, entity: DXFEntity, config: MediumConfig) -> ObjectData | None:
        """Create ObjectData from POLYLINE entity.

        Parameters
        ----------
        entity : DXFEntity
            POLYLINE entity to process
        config : MediumConfig
            Configuration for medium processing

        Returns
        -------
        Optional[ObjectData]
            Created ObjectData or None if processing failed
        """
        if not isinstance(entity, Polyline):
            log.error("Expected POLYLINE entity")
            return None
        try:
            points = dxf.extract_points_from(entity)
            if not points:
                log.warning("No points extracted from POLYLINE entity")
                return None
            if config.is_round_line_based():
                log.debug("Creating DEFAULT round line-based object from POLYLINE")
                return self._default_round_line_based(entity, points, config)
            if config.is_rectangular_line_based():
                log.debug("Creating DEFAULT rectangular line-based object from POLYLINE")
                return self._default_rectangular_line_based(entity, points, config)
            largest_point = self._get_largest_rectangle([entity])
            if largest_point is not None:
                dimension, _ = self._analyze_rectangular_sided_block(largest_point, 0)
                center_point = dxf.calculate_center_point(points)
                return get_object(
                    entity=entity,
                    config=config,
                    dimension=dimension,
                    points=[center_point],
                )
            shape_type = dxf.detect_shape_type(points)
            if config.is_point_based():
                return self._create_round_point_based(entity, points, config)
            if config.is_line_based():
                return self._create_round_line_based(entity, points, config)
            log.error(f" Create object from POLYLINE: Unknown shape {shape_type}, {entity}")
            return None

        except Exception as e:
            log.error(f"Failed to process polyline entity: {e}")
            return None

    def _create_from_lw_polyline(self, entity: DXFEntity, config: MediumConfig) -> ObjectData | None:
        """Create ObjectData from LWPOLYLINE entity.

        Parameters
        ----------
        entity : DXFEntity
            LWPOLYLINE entity to process
        config : MediumConfig
            Configuration for medium processing

        Returns
        -------
        Optional[ObjectData]
            Created ObjectData or None if processing failed
        """
        if not isinstance(entity, LWPolyline):
            log.error("Expected LWPOLYLINE entity")
            return None
        try:
            points = dxf.extract_points_from(entity)
            if not points:
                return None
            if config.is_round_line_based():
                return self._default_round_line_based(entity, points, config)
            if config.is_rectangular_line_based():
                return self._default_rectangular_line_based(entity, points, config)

            largest_point = self._get_largest_rectangle([entity])
            if largest_point is not None:
                dimension, _ = self._analyze_rectangular_sided_block(largest_point, 0)
                center_point = dxf.calculate_center_point(points)
                return get_object(
                    entity=entity,
                    config=config,
                    dimension=dimension,
                    points=[center_point],
                )
            shape_type = dxf.detect_shape_type(points)
            if shape_type == "rectangular":
                return self._create_rect_point_based_object(entity, points, config)
            elif shape_type == "round":
                return self._create_round_point_based_from_polyline(entity, points, config)
            elif shape_type == "triangle":
                return self._create_round_point_based_from_polyline(entity, points, config)
            elif shape_type == "multi_sided":
                return self._create_multi_sided_object(entity, points, config)
            elif shape_type == "linear":
                return self._create_round_point_based(entity, points, config)
            elif shape_type == "bulge":
                return self._create_bulge_point_based_object(entity, config)
            elif config.is_point_based():
                return self._create_round_point_based(entity, points, config)
            elif config.is_line_based():
                return self._create_round_line_based(entity, points, config)
            log.warning(f" Create object from LWPOLINE: Unknown shape {shape_type}, {entity}")
            return None

        except Exception as e:
            log.error(f"Failed to process polyline entity: {e}")
            return None

    def _create_from_line(self, entity: DXFEntity, config: MediumConfig) -> ObjectData | None:
        try:
            points = dxf.extract_points_from(entity)
            if config.is_rectangular_line_based():
                return self._default_rectangular_line_based(entity, points, config)
            elif config.is_round_line_based():
                return self._create_round_line_based(entity, points, config)
            else:
                return self._create_round_point_based(entity, points, config)
        except Exception as e:
            log.error(f"Failed to process LINE entity: {e}")
            return None

    def _create_from_arc(self, entity: DXFEntity, config: MediumConfig) -> ObjectData | None:
        if not isinstance(entity, Arc):
            log.debug("Expected ARC entity")
            return None
        points = dxf.extract_points_from(entity)

        if config.is_rectangular_line_based():
            return self._default_rectangular_line_based(entity, points, config)

        dimension = _get_default_line_dimension(config)
        return get_object(
            entity=entity,
            config=config,
            dimension=dimension,
            points=points,
        )

    def _create_rect_point_based_object(
        self, entity: DXFEntity, points: list[Point3D], config: MediumConfig
    ) -> ObjectData:
        if dxf.is_rectangular(points):
            width, depth = dxf.calculate_rect_dimensions(points)
            width = width / 1000.0
            depth = depth / 1000.0
        else:
            width, depth = dxf.calculate_bbox_dimensions(points)

        if config.default_width is not None and (width is None or width == 0.0):
            width = config.default_width
        if config.default_depth is not None and (depth is None or depth == 0.0):
            depth = config.default_depth

        position = dxf.calculate_center_point(points)
        angle = dxf.calculate_angle_from_points(points)
        dimension = Dimension(length=width, width=depth, angle=angle, shape=ShapeType.RECTANGULAR)

        return get_object(
            entity=entity,
            config=config,
            dimension=dimension,
            points=[position],
        )

    def _default_rectangular_line_based(
        self, entity: DXFEntity, points: list[Point3D], config: MediumConfig, angle: float = 0.0
    ) -> ObjectData:
        dimension = _get_default_rectangular_dimension(config=config, angle=angle)
        return get_object(
            entity=entity,
            config=config,
            dimension=dimension,
            points=points,
        )

    def _default_round_line_based(self, entity: DXFEntity, points: list[Point3D], config: MediumConfig) -> ObjectData:
        dimension = _get_default_line_dimension(config)
        return get_object(
            entity=entity,
            config=config,
            dimension=dimension,
            points=points,
        )

    def _create_round_point_based_from_polyline(
        self, entity: DXFEntity, points: list[Point3D], config: MediumConfig
    ) -> ObjectData:
        position = dxf.calculate_center_point(points)
        if config.default_diameter is None:
            diameter = dxf.estimate_diameter_from(points)
        else:
            diameter = config.default_diameter

        return get_object(
            entity=entity,
            config=config,
            dimension=Dimension(diameter=diameter, shape=ShapeType.ROUND),
            points=[position],
        )

    def _create_multi_sided_object(
        self,
        entity: DXFEntity,
        points: list[Point3D],
        config: MediumConfig,
    ) -> ObjectData:
        position = dxf.calculate_center_point(points)
        width, depth = dxf.calculate_bbox_dimensions(points)
        if config.default_width is not None:
            width = width or config.default_width
        if config.default_depth is not None:
            depth = depth or config.default_depth
        dimensions = Dimension(length=width, width=depth, angle=0.0, shape=ShapeType.RECTANGULAR)

        return get_object(
            entity=entity,
            config=config,
            dimension=dimensions,
            points=[position],
        )

    def _create_bulge_point_based_object(self, entity: DXFEntity, config: MediumConfig) -> ObjectData:
        center, diameter = dxf.get_bulge_center_and_diameter(entity)
        if diameter == 0.0 and config.default_diameter is not None:
            diameter = diameter or config.default_diameter
        dimensions = Dimension(diameter=diameter, shape=ShapeType.ROUND)

        return get_object(
            entity=entity,
            config=config,
            dimension=dimensions,
            points=[center],
        )

    def _create_round_line_based(self, entity: DXFEntity, points: list[Point3D], config: MediumConfig) -> ObjectData:
        dimension = _get_default_line_dimension(config)

        return get_object(
            entity=entity,
            config=config,
            dimension=dimension,
            points=points,
        )

    def _create_round_point_based(self, entity: DXFEntity, points: list[Point3D], config: MediumConfig) -> ObjectData:
        dimension = Dimension(diameter=config.default_diameter or 1.0, shape=ShapeType.ROUND)
        return get_object(
            entity=entity,
            config=config,
            dimension=dimension,
            points=points,
        )

    def _get_block_entities(self, insert_entity: Insert) -> list[DXFEntity]:
        block_name = insert_entity.dxf.name

        if block_name not in self._block_cache:
            entities = list(self.dxf_doc.blocks[block_name])
            entities = [e for e in entities if e.dxftype() not in ["HATCH"]]
            self._block_cache[block_name] = entities
        return self._block_cache[block_name]

    def _analyze_block_shape(self, insert_entity: Insert, block_entities: list[DXFEntity]) -> tuple | None:
        angle = dxf.get_angle_from_entity(insert_entity)
        if not block_entities:
            return self._default_block_dimensions(insert_entity, angle)

        # Check for circular blocks (containing circles)
        circles = [e for e in block_entities if e.dxftype() == "CIRCLE"]
        if len(circles) == len(block_entities):
            return self._analyze_circular_block(circles)

        # Extract all geometry points from block entities
        all_points = []
        for entity in block_entities:
            entity_points = dxf.extract_points_from(entity)
            all_points.extend(entity_points)

        if not all_points:
            raise ValueError(f"No points found in block entities {insert_entity.dxf.name}")

        largest_rectangle = self._get_largest_rectangle(block_entities)
        if largest_rectangle is not None:
            return self._analyze_rectangular_sided_block(largest_rectangle, angle)

        # Detect shape type
        shape_type = dxf.detect_shape_type(all_points)

        if shape_type == "rectangular":
            if dxf.is_rectangular(all_points):
                width, depth = dxf.calculate_rect_dimensions(all_points)
            else:
                width, depth = dxf.calculate_bbox_dimensions(all_points)
            dimensions = Dimension(
                width=width,
                depth=depth,
                angle=angle,
                shape=ShapeType.RECTANGULAR,
            )
        elif shape_type == "round":
            diameter = dxf.estimate_diameter_from(all_points)
            dimensions = Dimension(diameter=diameter, shape=ShapeType.ROUND)
        else:
            # Multi-sided or complex - use bounding box
            width, depth = dxf.calculate_bbox_dimensions(all_points)
            dimensions = Dimension(
                width=width,
                depth=depth,
                angle=angle,
                shape=ShapeType.RECTANGULAR,
            )

        return dimensions, all_points

    def _analyze_circular_block(self, circles: list[DXFEntity]) -> tuple[Dimension, list[Point3D]]:
        max_diameter = 0.0
        center_point = None

        for circle in circles:
            if not isinstance(circle, Circle):
                continue
            diameter = circle.dxf.radius * 2.0
            if diameter > max_diameter:
                max_diameter = diameter
                center = circle.dxf.center
                center_point = Point3D(east=center.x, north=center.y, altitude=0.0)

        dimensions = Dimension(diameter=max_diameter, shape=ShapeType.ROUND)
        geometry_points = [center_point] if center_point else []

        return dimensions, geometry_points

    def _get_largest_rectangle(self, entities: list[DXFEntity]) -> list[DXFEntity] | None:
        """Find the largest rectangle from a set of lines."""
        lines = dxf.get_dxf_lines(entities)
        line_groups = dxf.group_lines_by_points(lines, threshold=0.01)
        rectangles = dxf.find_rectangles_from_groups(line_groups)

        if len(rectangles) == 0:
            return None
        if len(rectangles) == 1:
            return rectangles[0]  # pyright: ignore[reportReturnType]
        # Find the rectangle with the largest line
        group_extents = [dxf.get_group_extent(rectangle) for rectangle in rectangles]
        largest_rectangle = max(group_extents)
        largest_index = group_extents.index(largest_rectangle)
        return rectangles[largest_index]  # pyright: ignore[reportReturnType]

    def _analyze_rectangular_sided_block(self, lines: list[DXFEntity], angle: float) -> tuple[Dimension, list[Point3D]]:
        points = []
        for line in lines:
            points.extend(dxf.extract_points_from(line))
        if len(points) != 4:
            raise ValueError(f"Expected 4 points for rectangular block, got {len(points)}")
        width, depth = dxf.calculate_rect_dimensions(points)
        dimension = Dimension(width=width, depth=depth, angle=angle, shape=ShapeType.RECTANGULAR)
        return dimension, points

    def _default_block_dimensions(self, insert_entity: Insert, angle: float) -> tuple[Dimension, list[Point3D]]:
        block_name = insert_entity.dxf.name.lower()
        if any(keyword in block_name for keyword in ["round", "circle", "rund"]):
            dimensions = Dimension(diameter=0.8, shape=ShapeType.ROUND)
        else:
            dimensions = Dimension(
                width=1.0,
                depth=0.6,
                angle=angle,
                shape=ShapeType.RECTANGULAR,
            )

        return dimensions, []

    def _transform_block_geometry(self, points: list[Point3D], insert_entity: Insert) -> list[Point3D]:
        """Transform block geometry points to world coordinates.

        Parameters
        ----------
        points : List[Point3D]
            Points from block definition
        insert_entity : Insert
            INSERT entity with transformation

        Returns
        -------
        List[Point3D]
            Transformed points
        """
        if not points:
            return points

        try:
            insert_point = insert_entity.dxf.insert

            # Apply translation (basic transformation)
            # TODO: Add scaling and rotation support
            transformed_points = []
            for point in points:
                new_point = Point3D(
                    east=point.east + insert_point.x,
                    north=point.north + insert_point.y,
                    altitude=point.altitude,
                )
                transformed_points.append(new_point)

            return transformed_points

        except Exception as e:
            log.error(f"Failed to transform block geometry: {e}")
            return points
