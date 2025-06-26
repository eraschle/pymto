"""Factory for creating ObjectData instances from DXF entities.

This module provides a factory pattern for creating ObjectData objects
from various DXF entity types with intelligent shape detection and
dimension calculation.
"""

import logging

from ezdxf.document import Drawing
from ezdxf.entities.circle import Circle
from ezdxf.entities.dxfentity import DXFEntity
from ezdxf.entities.insert import Insert

from ..models import (
    ObjectData,
    ObjectType,
    Point3D,
    RectangularDimensions,
    RoundDimensions,
)
from . import entity_handler as dxf

log = logging.getLogger(__name__)


def is_pipe_or_duct(object_type: ObjectType) -> bool:
    """Check if the object type is PIPE or DUCT.

    Parameters
    ----------
    object_type : ShapeType
        The type of the object to check

    Returns
    -------
    bool
        True if the object type is PIPE or DUCT, False otherwise
    """
    return object_type in (
        ObjectType.CABLE_DUCT,
        ObjectType.PIPE_GAS,
        ObjectType.PIPE_WASTEWATER,
        ObjectType.PIPE_WATER,
    )


class ObjectDataFactory:
    """Factory for creating ObjectData from DXF entities."""

    def __init__(self, dxf_document: Drawing):
        """Initialize factory with DXF document.

        Parameters
        ----------
        dxf_document : Drawing
            DXF document for block resolution
        """
        self.doc = dxf_document
        self._block_cache = {}

    def create_from_entity(
        self, medium: str, entity: DXFEntity, object_type: ObjectType
    ) -> ObjectData | None:
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

            if entity_type == "INSERT":
                return self._create_from_insert(medium, entity, object_type)
            elif entity_type == "CIRCLE":
                return self._create_from_circle(medium, entity, object_type)
            elif entity_type in ("POLYLINE", "LWPOLYLINE"):
                return self._create_from_polyline(medium, entity, object_type)
            elif entity_type == "LINE":
                return self._create_from_line(medium, entity, object_type)
            else:
                log.warning(f"Unsupported entity type: {entity_type}")
                return None

        except Exception as e:
            log.error(f"Failed to create ObjectData from {entity.dxftype()}: {e}")
            return None

    def _create_from_insert(
        self, medium: str, entity: DXFEntity, object_type: ObjectType
    ) -> ObjectData | None:
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
            # Get insertion point
            insert_point = entity.dxf.insert
            position = Point3D(east=insert_point.x, north=insert_point.y, altitude=0.0)

            # Analyze block geometry
            block_entities = self._get_block_entities(entity)
            shape_analysis = self._analyze_block_shape(entity, block_entities)

            if shape_analysis is None:
                return None

            dimensions, geometry_points = shape_analysis

            # Transform geometry points to world coordinates
            transformed_points = self._transform_block_geometry(geometry_points, entity)

            color = self._get_entity_color(entity)
            layer = getattr(entity.dxf, "layer", "0")

            return ObjectData(
                medium=medium,
                object_type=object_type,
                dimensions=dimensions,
                layer=layer,
                positions=[position],
                points=transformed_points,
                color=color,
            )

        except Exception as e:
            log.error(f"Failed to process INSERT entity: {e}")
            return None

    def _create_from_circle(
        self, medium: str, entity: DXFEntity, object_type: ObjectType
    ) -> ObjectData | None:
        """Create ObjectData from CIRCLE entity.

        Parameters
        ----------
        entity : Circle
            CIRCLE entity to process
        config : MediumConfig
            Configuration for medium processing

        Returns
        -------
        Optional[ObjectData]
            Created ObjectData or None if processing failed
        """
        if not isinstance(entity, Circle):
            log.error("Expected CIRCLE entity")
            return None
        try:
            center = entity.dxf.center
            radius = entity.dxf.radius

            position = Point3D(east=center.x, north=center.y, altitude=0.0)
            dimensions = RoundDimensions(diameter=radius * 2.0)

            color = self._get_entity_color(entity)
            layer = getattr(entity.dxf, "layer", "0")

            return ObjectData(
                medium=medium,
                object_type=object_type,
                dimensions=dimensions,
                layer=layer,
                positions=[position],
                color=color,
            )

        except Exception as e:
            log.error(f"Failed to process CIRCLE entity: {e}")
            return None

    def _create_from_polyline(
        self, medium: str, entity: DXFEntity, object_type: ObjectType
    ) -> ObjectData | None:
        """Create ObjectData from POLYLINE or LWPOLYLINE entity.

        Parameters
        ----------
        entity : DXFEntity
            POLYLINE or LWPOLYLINE entity to process
        config : MediumConfig
            Configuration for medium processing

        Returns
        -------
        Optional[ObjectData]
            Created ObjectData or None if processing failed
        """
        try:
            points = dxf.extract_points_from(entity)
            if not points:
                return None
            if object_type.name.lower().startswith("pipe"):
                return self._create_round_object_from_polygon(medium, entity, points, object_type)
            elif object_type == ObjectType.CABLE_DUCT:
                return self._create_rectangular_object(medium, entity, points, object_type)
            shape_type = dxf.detect_shape_type(points)
            if shape_type == "rectangular":
                return self._create_rectangular_object(medium, entity, points, object_type)
            elif shape_type == "round":
                return self._create_round_object_from_polygon(medium, entity, points, object_type)
            elif shape_type == "multi_sided":
                return self._create_multi_sided_object(medium, entity, points, object_type)
            else:
                # Linear or simple shape - treat as line-based
                return self._create_line_object(medium, entity, points, object_type)

        except Exception as e:
            log.error(f"Failed to process polyline entity: {e}")
            return None

    def _create_from_line(self, medium: str, entity: DXFEntity, object_type: ObjectType) -> ObjectData | None:
        """Create ObjectData from LINE entity.

        Parameters
        ----------
        entity : DXFEntity
            LINE entity to process
        config : MediumConfig
            Configuration for medium processing

        Returns
        -------
        Optional[ObjectData]
            Created ObjectData or None if processing failed
        """
        try:
            points = dxf.extract_points_from(entity)
            return self._create_line_object(medium,entity, points, object_type)

        except Exception as e:
            log.error(f"Failed to process LINE entity: {e}")
            return None

    def _create_rectangular_object(
        self, medium: str, entity: DXFEntity, points: list[Point3D], object_type: ObjectType
    ) -> ObjectData:
        """Create rectangular ObjectData from points.

        Parameters
        ----------
        entity : DXFEntity
            Source entity
        points : List[Point3D]
            Points defining the rectangle
        object_type : ShapeType
            Type of object (PIPE, DUCT, etc.)

        Returns
        -------
        ObjectData
            Created ObjectData with rectangular dimensions
        """
        length, width = 0.0, 0.0
        if not is_pipe_or_duct(object_type):
            if dxf.is_rectangular(points):
                length, width = dxf.calculate_rect_dimensions(points)
            else:
                length, width = dxf.calculate_bbox_dimensions(points)

        position = dxf.calculate_center_point(points)
        dimensions = RectangularDimensions(length=length, width=width, angle=0.0)

        color = self._get_entity_color(entity)
        layer = getattr(entity.dxf, "layer", "0")

        return ObjectData(
            medium=medium,
            object_type=object_type,
            dimensions=dimensions,
            layer=layer,
            positions=[position],
            points=points,
            color=color,
        )

    def _create_round_object_from_polygon(
        self, medium: str, entity: DXFEntity, points: list[Point3D], object_type: ObjectType
    ) -> ObjectData:
        """Create round ObjectData from polygonal points.

        Parameters
        ----------
        entity : DXFEntity
            Source entity
        points : List[Point3D]
            Points defining the near-circular shape
        object_type : ShapeType
            Type of object (PIPE, DUCT, etc.)

        Returns
        -------
        ObjectData
            Created ObjectData with round dimensions
        """
        position = dxf.calculate_center_point(points)
        diameter = 0.0
        if not is_pipe_or_duct(object_type):
            diameter = dxf.estimate_diameter_from(points)
        dimensions = RoundDimensions(diameter=diameter)

        color = self._get_entity_color(entity)
        layer = getattr(entity.dxf, "layer", "0")

        return ObjectData(
            medium=medium,
            object_type=object_type,
            dimensions=dimensions,
            layer=layer,
            positions=[position],
            points=points,
            color=color,
        )

    def _create_multi_sided_object(
        self, medium: str, entity: DXFEntity, points: list[Point3D], object_type: ObjectType
    ) -> ObjectData:
        """Create multi-sided ObjectData from points.

        For multi-sided shapes, we use bounding box dimensions but keep
        the original geometry for reference.

        Parameters
        ----------
        entity : DXFEntity
            Source entity
        points : List[Point3D]
            Points defining the multi-sided shape
        object_type : ObjectType
            Type of object (PIPE, DUCT, etc.)

        Returns
        -------
        ObjectData
            Created ObjectData with rectangular dimensions (bounding box)
        """
        position = dxf.calculate_center_point(points)
        length, width = dxf.calculate_bbox_dimensions(points)
        dimensions = RectangularDimensions(length=length, width=width, angle=0.0)

        color = self._get_entity_color(entity)
        layer = getattr(entity.dxf, "layer", "0")

        return ObjectData(
            medium=medium,
            object_type=object_type,
            dimensions=dimensions,
            layer=layer,
            positions=[position],
            points=points,
            color=color,
        )

    def _create_line_object(
        self, medium: str, entity: DXFEntity, points: list[Point3D], object_type: ObjectType
    ) -> ObjectData:
        """Create line-based ObjectData from points.

        Parameters
        ----------
        entity : DXFEntity
            Source entity
        points : List[Point3D]
            Points defining the line
        object_type : ObjectType
            Type of object (PIPE, DUCT, etc.)

        Returns
        -------
        ObjectData
            Created ObjectData with default round dimensions
        """
        # Default diameter for pipes
        dimensions = RoundDimensions(diameter=200.0)  # 200mm default

        color = self._get_entity_color(entity)
        layer = getattr(entity.dxf, "layer", "0")

        return ObjectData(
            medium=medium,
            object_type=object_type,
            dimensions=dimensions,
            layer=layer,
            points=points,
            color=color,
        )

    def _get_block_entities(self, insert_entity: Insert) -> list[DXFEntity]:
        """Get entities from block definition.

        Parameters
        ----------
        insert_entity : Insert
            INSERT entity

        Returns
        -------
        List[DXFEntity]
            List of entities from block definition
        """
        block_name = insert_entity.dxf.name

        if block_name not in self._block_cache:
            entities = list(self.doc.blocks[block_name])
            self._block_cache[block_name] = entities
        return self._block_cache[block_name]

    def _analyze_block_shape(self, insert_entity: Insert, block_entities: list[DXFEntity]) -> tuple | None:
        """Analyze block geometry to determine shape and dimensions.

        Parameters
        ----------
        insert_entity : Insert
            INSERT entity
        block_entities : List[DXFEntity]
            Entities from block definition

        Returns
        -------
        Optional[tuple]
            Tuple of (dimensions, geometry_points) or None if analysis failed
        """
        if not block_entities:
            return self._default_block_dimensions(insert_entity)

        # Check for circular blocks (containing circles)
        circles = [e for e in block_entities if e.dxftype() == "CIRCLE"]
        if circles:
            return self._analyze_circular_block(circles)

        # Extract all geometry points from block entities
        all_points = []
        for entity in block_entities:
            entity_points = dxf.extract_points_from(entity)
            all_points.extend(entity_points)

        if not all_points:
            return self._default_block_dimensions(insert_entity)

        # Detect shape type
        shape_type = dxf.detect_shape_type(all_points)

        if shape_type == "rectangular":
            if dxf.is_rectangular(all_points):
                length, width = dxf.calculate_rect_dimensions(all_points)
            else:
                length, width = dxf.calculate_bbox_dimensions(all_points)
            dimensions = RectangularDimensions(length=length, width=width, angle=0.0)
        elif shape_type == "round":
            diameter = dxf.estimate_diameter_from(all_points)
            dimensions = RoundDimensions(diameter=diameter)
        else:
            # Multi-sided or complex - use bounding box
            length, width = dxf.calculate_bbox_dimensions(all_points)
            dimensions = RectangularDimensions(length=length, width=width, angle=0.0)

        return dimensions, all_points

    def _analyze_circular_block(self, circles: list[DXFEntity]) -> tuple:
        """Analyze block containing circles to determine dimensions.

        Parameters
        ----------
        circles : List[DXFEntity]
            List of CIRCLE entities from block

        Returns
        -------
        tuple
            Tuple of (dimensions, geometry_points)
        """
        # Find the largest circle (outer diameter)
        max_diameter = 0.0
        center_point = None

        for circle in circles:
            if isinstance(circle, Circle):
                diameter = circle.dxf.radius * 2.0
                if diameter > max_diameter:
                    max_diameter = diameter
                    center = circle.dxf.center
                    center_point = Point3D(east=center.x, north=center.y, altitude=0.0)

        dimensions = RoundDimensions(diameter=max_diameter)
        geometry_points = [center_point] if center_point else []

        return dimensions, geometry_points

    def _default_block_dimensions(self, insert_entity: Insert) -> tuple:
        """Provide default dimensions for unknown block types.

        Parameters
        ----------
        insert_entity : Insert
            INSERT entity

        Returns
        -------
        tuple
            Tuple of (dimensions, geometry_points)
        """
        block_name = insert_entity.dxf.name.lower()

        # Try to guess from block name
        if any(keyword in block_name for keyword in ["round", "circle", "rund"]):
            dimensions = RoundDimensions(diameter=800.0)  # Default 800mm
        else:
            dimensions = RectangularDimensions(length=600.0, width=600.0, angle=0.0)

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

    def _get_entity_color(self, entity: DXFEntity) -> tuple[int, int, int]:
        """Get RGB color of a DXF entity.

        Parameters
        ----------
        entity : DXFEntity
            Entity to get color from

        Returns
        -------
        tuple[int, int, int]
            RGB color values
        """
        try:
            color_index = getattr(entity.dxf, "color", 7)

            # Simple AutoCAD color index to RGB mapping
            color_map = {
                1: (255, 0, 0),  # Red
                2: (255, 255, 0),  # Yellow
                3: (0, 255, 0),  # Green
                4: (0, 255, 255),  # Cyan
                5: (0, 0, 255),  # Blue
                6: (255, 0, 255),  # Magenta
                7: (0, 0, 0),  # Black/White
            }

            return color_map.get(color_index, (0, 0, 0))

        except Exception:
            return (0, 0, 0)

    def should_process_as_element(self, entity: DXFEntity) -> bool:
        """Determine if entity should be processed as element or line.

        Parameters
        ----------
        entity : DXFEntity
            Entity to classify

        Returns
        -------
        bool
            True if should be processed as element
        """
        return dxf.is_element_entity(entity)
