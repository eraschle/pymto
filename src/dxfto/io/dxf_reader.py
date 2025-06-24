"""DXF file reader for extracting pipes, shafts, and texts.

This module handles reading DXF files using the ezdxf library and
extracting the relevant geometric entities (lines, polylines, circles,
rectangles, and text elements).
"""

import logging
from pathlib import Path

import ezdxf.filemanagement as ezdxf
from ezdxf.document import Drawing
from ezdxf.entities.circle import Circle
from ezdxf.entities.dxfentity import DXFEntity
from ezdxf.entities.insert import Insert
from ezdxf.entities.line import Line
from ezdxf.entities.lwpolyline import LWPolyline
from ezdxf.entities.mtext import MText
from ezdxf.entities.polyline import Polyline
from ezdxf.entities.text import Text
from ezdxf.lldxf.const import DXFError
from ezdxf.query import EntityQuery

from ..models import (
    AssignmentConfig,
    AssingmentData,
    DxfText,
    LayerData,
    Medium,
    ObjectData,
    Point3D,
    RectangularDimensions,
    RoundDimensions,
)

log = logging.getLogger(__name__)


class DXFReader:
    """Reader for DXF files to extract pipes, shafts, and texts.

    This class processes DXF files and identifies geometric entities
    that represent pipes (lines/polylines), shafts (circles/rectangles),
    and associated text elements.
    """

    def __init__(self, dxf_path: Path) -> None:
        """Initialize DXF reader with file path.

        Parameters
        ----------
        dxf_path : Path
            Path to the DXF file to process
        """
        self.dxf_path = dxf_path
        self._doc: Drawing | None = None

    def load_file(self) -> None:
        """Load the DXF file using ezdxf library.

        Raises
        ------
        FileNotFoundError
            If DXF file does not exist
        ezdxf.DXFError
            If DXF file cannot be parsed
        """
        if not self.dxf_path.exists():
            raise FileNotFoundError(f"DXF file not found: {self.dxf_path}")

        try:
            self._doc = ezdxf.readfile(str(self.dxf_path))
        except DXFError as e:
            raise DXFError(f"Cannot read DXF file {self.dxf_path}: {e}") from e

    def _query_modelspace(self, layers: list[LayerData]) -> EntityQuery:
        if self._doc is None:
            raise RuntimeError("DXF file not loaded. Call load_file() first.")

        layer_names = [layer.name for layer in layers]
        query = '*[layer=="' + '" | layer=="'.join(layer_names) + '"]'
        return self._doc.modelspace().query(query)

    def extract_data(self, mediums: dict[str, Medium]) -> None:
        """Extract geometries from DXF file.

        Elements are identified as LINE and POLYLINE entities.
        Shape and dimensions are inferred from the geometry.
        """

        for medium in mediums.values():
            medium.element_data = self._create_assignment(medium.elements)
            medium.line_data = self._create_assignment(medium.lines)

    def _create_assignment(self, config: AssignmentConfig) -> AssingmentData:
        """Create assignment data for elements and texts based on configuration."""
        return AssingmentData(
            elements=self._extract_elements(config),
            texts=self._extract_texts(config),
        )

    def _extract_elements(self, config: AssignmentConfig) -> list[ObjectData]:
        """Extract shaft geometries from DXF file.

        Processes various DXF entity types and classifies them as elements
        (shafts, complex geometries) based on their characteristics.
        """
        if self._doc is None:
            raise RuntimeError("DXF file not loaded. Call load_file() first.")

        elements = []
        for entity in self._query_modelspace(config.geometry):
            # Check if entity should be processed as an element
            if not self._should_process_as_element(entity):
                continue

            element = self._create_element_from_entity(entity)
            if element is None:
                log.error(f"_create_elements: Failed to create object from entity: {entity.dxftype()}")
                continue
            elements.append(element)
        return elements

    def _should_process_as_element(self, entity: DXFEntity) -> bool:
        """Determine if a DXF entity should be processed as an element.

        Elements are typically shafts or complex geometries that should be
        processed as point-based objects rather than line-based objects.

        Parameters
        ----------
        entity : DXFEntity
            DXF entity to classify

        Returns
        -------
        bool
            True if entity should be processed as element, False otherwise
        """
        entity_type = entity.dxftype()

        # Block references (INSERT) are always elements (typically shafts)
        if entity_type == "INSERT":
            return True

        # Circles are always elements (round shafts)
        if entity_type == "CIRCLE":
            return True

        # For polylines, check if they form complex shapes (4+ points)
        if entity_type in ("POLYLINE", "LWPOLYLINE"):
            if isinstance(entity, LWPolyline | Polyline) and entity.is_closed:
                return True
            points = self._extract_points_from(entity)
            # Complex polylines with 4+ points are likely rectangular shafts
            if len(points) >= 4:
                return True

        # Simple lines and short polylines are typically pipes/lines
        if entity_type in ("LINE", "POLYLINE", "LWPOLYLINE"):
            return False

        # Other entity types - skip for now
        return False

    def _is_rectangular_shape(self, points: list[Point3D]) -> bool:
        if len(points) != 4:
            return False
        diagonal1 = points[0].distance_2d(points[2])
        diagonal2 = points[1].distance_2d(points[3])
        return abs(diagonal1 - diagonal2) < 1e-6  # Allow

    def _get_bbox_dimension(self, points: list[Point3D]) -> tuple[float, float]:
        east_min = min(p.east for p in points)
        east_max = max(p.east for p in points)
        north_min = min(p.north for p in points)
        north_max = max(p.north for p in points)
        length = east_max - east_min
        width = north_max - north_min
        return length, width

    def _get_rect_dimension(self, points: list[Point3D]) -> tuple[float, float]:
        first_side = points[0].distance_2d(points[1])
        second_side = points[1].distance_2d(points[2])
        length = max(first_side, second_side)
        width = min(first_side, second_side)
        return length, width

    def _get_rectangular_dimension(self, points: list[Point3D]) -> RectangularDimensions:
        if len(points) == 4:
            length, width = self._get_rect_dimension(points)
        else:
            length, width = self._get_bbox_dimension(points)
        return RectangularDimensions(length=length, width=width, angle=0.0)

    def _get_rectangular_center(self, points: list[Point3D]) -> Point3D:
        center_x = sum(p.east for p in points) / len(points)
        center_y = sum(p.north for p in points) / len(points)
        return Point3D(east=center_x, north=center_y, altitude=0.0)

    def _create_element_from_entity(self, entity: DXFEntity) -> ObjectData | None:
        """Create an ObjectData element from various DXF entity types.

        This method routes different entity types to appropriate creation methods
        and applies intelligent shape detection.

        Parameters
        ----------
        entity : DXFEntity
            DXF entity to process

        Returns
        -------
        ObjectData | None
            Created object data or None if processing failed
        """
        entity_type = entity.dxftype()

        try:
            # Handle block references (INSERT entities)
            if entity_type == "INSERT":
                return self._create_object_from_insert(entity)

            # Handle circles (round shafts)
            elif entity_type == "CIRCLE":
                return self._create_round_from(entity)

            points = self._extract_points_from(entity)
            if self._is_rectangular_shape(points):
                return self._create_rectangular_from(entity)

            # Handle complex polylines (rectangular shafts)
            elif entity_type in ("POLYLINE", "LWPOLYLINE"):
                if len(points) >= 4:
                    return self._create_rectangular_from(entity)

            # Fallback to generic line-based processing
            return self._create_object_from(entity)

        except Exception as e:
            log.error(f"_create_element_from_entity: Failed to create element from {entity_type}: {e}")
            return None

    def _create_object_from(self, entity: DXFEntity) -> ObjectData | None:
        """Create a Pipe object from a DXF line/polyline entity.

        Parameters
        ----------
        entity : DXFEntity
            DXF entity (LINE, POLYLINE, or LWPOLYLINE)

        Returns
        -------
        Pipe | None
            Pipe object or None if entity cannot be processed
        """
        try:
            points = self._extract_points_from(entity)
            if not points:
                return None

            dimensions = RoundDimensions(diameter=200.0)  # Default 200mm
            color = self._get_entity_color(entity)
            layer = entity.dxf.layer if hasattr(entity.dxf, "layer") else "0"

            return ObjectData(
                dimensions=dimensions,
                layer=layer,
                points=points,
                color=color,
            )
        except Exception:
            return None

    def _create_object_from_insert(self, entity: DXFEntity) -> ObjectData | None:
        """Create an ObjectData from an INSERT entity (block reference).

        Processes block references which typically represent shafts or
        other standardized elements in civil engineering drawings.

        Parameters
        ----------
        entity : DXFEntity
            INSERT entity representing a block reference

        Returns
        -------
        ObjectData | None
            Created object or None if processing failed
        """
        if not isinstance(entity, Insert):
            return None
        try:
            # Get insertion point
            insert_pnt = entity.dxf.insert
            position = Point3D(east=insert_pnt.x, north=insert_pnt.y, altitude=0.0)

            # Try to determine shape from block geometry or attributes
            block_geometry = self._extract_block_points(entity)
            if self._is_round_block_geometry(entity):
                dimensions = RoundDimensions(diameter=800.0)
            dimensions = self._analyze_block_shape(entity, block_geometry)

            color = self._get_entity_color(entity)
            layer = entity.dxf.layer if hasattr(entity.dxf, "layer") else "0"

            # Create ObjectData with position for point-based elements
            return ObjectData(
                dimensions=dimensions,
                layer=layer,
                positions=[position],  # Block references are point-based
                points=block_geometry,  # Store extracted geometry for reference
                color=color,
            )

        except Exception as e:
            log.error(f"Failed to process INSERT entity '{entity.dxf.name}': {e}")
            return None

    def _get_block_geometry_entities(self, insert_entity: Insert) -> list[DXFEntity]:
        if self._doc is None:
            return []

        block_name = insert_entity.dxf.name
        if block_name not in self._doc.blocks:
            log.warning(f"Block definition '{block_name}' not found")
            return []

        return list(self._doc.blocks[block_name])

    def _is_round_block_geometry(self, insert_entity: Insert) -> bool:
        """Check if the block geometry represents a round shape.

        Parameters
        ----------
        insert_entity : Insert
            INSERT entity to check

        Returns
        -------
        bool
            True if block geometry is round, False otherwise
        """
        block_entities = self._get_block_geometry_entities(insert_entity)
        entity_types = {entity.dxftype() for entity in block_entities}
        round_types = ("CIRCLE", "ARC", "ELLIPSE")
        return all(e_type in round_types for e_type in entity_types)

    def _extract_block_points(self, insert_entity: Insert) -> list[Point3D]:
        """Extract geometry from a block definition.

        Parameters
        ----------
        insert_entity : Insert
            INSERT entity to extract geometry from

        Returns
        -------
        list[Point3D]
            List of points representing the block geometry
        """
        try:
            block_def = self._get_block_geometry_entities(insert_entity)
            if self._is_round_block_geometry(insert_entity):
                round_object = None
                max_diameter = 0.0
                for entity in block_def:
                    object_data = self._create_round_from(entity)
                    if object_data is None:
                        continue
                    if round_object is None:
                        round_object = object_data
                        continue
                    dimension = object_data.dimensions
                    if not isinstance(dimension, RoundDimensions):
                        continue
                    if max_diameter > dimension.diameter:
                        continue
                    max_diameter = dimension.diameter
                    round_objects = object_data
                return round_object

            geometry_points = []

            # Extract geometry from block entities
            for block_entity in block_def:
                if block_entity.dxftype() in ("LINE", "POLYLINE", "LWPOLYLINE", "CIRCLE"):
                    entity_points = self._extract_points_from(block_entity)
                    geometry_points.extend(entity_points)

            # Apply transformation (scale, rotation, translation)
            transformed_points = self._apply_block_transformation(geometry_points, insert_entity)

            return transformed_points

        except Exception as e:
            log.error(f"Failed to extract block geometry: {e}")
            return []

    def _apply_block_transformation(self, points: list[Point3D], insert_entity: Insert) -> list[Point3D]:
        """Apply block transformation to geometry points.

        Parameters
        ----------
        points : list[Point3D]
            Original points from block definition
        insert_entity : Insert
            INSERT entity with transformation parameters

        Returns
        -------
        list[Point3D]
            Transformed points
        """
        if not points:
            return points

        try:
            # Get transformation parameters
            insert_point = insert_entity.dxf.insert
            # Note: scale_x, scale_y, rotation could be used for full transformation
            # For now, implement basic translation
            # TODO: Add proper scaling and rotation if needed
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
            log.error(f"Failed to apply block transformation: {e}")
            return points

    def _is_round_name(self, block_name: str) -> bool:
        round_names = ["round", "circle", "rund"]
        return any(name in block_name.lower() for name in round_names)

    def _is_rectangular_name(self, block_name: str) -> bool:
        rectangular_names = ["rect", "square", "eckig"]
        return any(name in block_name.lower() for name in rectangular_names)

    def _analyze_block_shape(
        self, insert_entity: Insert, geometry: list[Point3D]
    ) -> RoundDimensions | RectangularDimensions:
        """Analyze block geometry to determine shape type and dimensions.

        Parameters
        ----------
        insert_entity : Insert
            INSERT entity to analyze
        geometry : list[Point3D]
            Extracted geometry points

        Returns
        -------
        tuple[ShapeType, RoundDimensions | RectangularDimensions]
            Detected shape type and dimensions
        """
        if self._is_rectangular_shape(geometry):
            return self._get_rectangular_dimension(geometry)

        block_name = insert_entity.dxf.name.lower()
        if self._is_rectangular_name(block_name):
            return RectangularDimensions(length=600.0, width=600.0, angle=0.0)
        return RoundDimensions(diameter=800.0)

    def _create_round_from(self, entity: DXFEntity) -> ObjectData | None:
        """Create a round Shaft object from a DXF circle entity."""
        try:
            if not isinstance(entity, Circle):
                return None

            center = entity.dxf.center
            radius = entity.dxf.radius

            position = Point3D(east=center.x, north=center.y, altitude=0.0)
            dimensions = RoundDimensions(diameter=radius * 2)

            color = self._get_entity_color(entity)
            layer = entity.dxf.layer if hasattr(entity.dxf, "layer") else "0"

            return ObjectData(
                dimensions=dimensions,
                layer=layer,
                positions=[position],
                color=color,
            )
        except Exception:
            return None

    def _create_rectangular_from(self, entity: DXFEntity) -> ObjectData | None:
        """Create a rectangular Shaft object from a closed polyline."""
        try:
            points = self._extract_points_from(entity)
            if len(points) < 4:
                return None

            color = self._get_entity_color(entity)
            layer = entity.dxf.layer if hasattr(entity.dxf, "layer") else "0"

            if self._is_rectangular_shape(points):
                position = self._get_rectangular_center(points)
                dimensions = self._get_rectangular_dimension(points)
                return ObjectData(
                    dimensions=dimensions,
                    layer=layer,
                    positions=[position],
                    color=color,
                )
        except Exception:
            return None

    def _extract_points_from(self, entity: DXFEntity) -> list[Point3D]:
        """Extract points from a DXF entity."""
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

    def _get_entity_color(self, entity: DXFEntity) -> tuple[int, int, int]:
        """Get RGB color of a DXF entity."""
        try:
            # This is a simplified color extraction
            # In reality, DXF color handling is more complex
            color_index = entity.dxf.color if hasattr(entity.dxf, "color") else 7

            # Simple mapping of AutoCAD color index to RGB
            # This would need to be expanded for full color support
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
            return (0, 0, 0)  # Default to black

    def _extract_texts(self, config: AssignmentConfig) -> list[DxfText]:
        """Extract text elements from DXF file."""
        if self._doc is None:
            raise RuntimeError("DXF file not loaded. Call load_file() first.")

        texts = []
        for entity in self._query_modelspace(config.text):
            if entity.dxftype() not in ("TEXT", "MTEXT"):
                continue
            text = self._create_text_from_entity(entity)
            if text is None:
                log.error(f"_extract_texts: Failed to create text from entity: {entity.dxftype()}")
                continue
            texts.append(text)

        return texts

    def _create_text_from_entity(self, entity: DXFEntity) -> DxfText | None:
        """Create a DxfText object from a DXF text entity."""
        if not isinstance(entity, (Text | MText)):
            return None
        try:
            text_content = None
            point = None
            if isinstance(entity, MText):
                lines = entity.plain_text()
                text_content = "".join(lines)
            else:
                text_content = entity.dxf.text
            if not text_content:
                log.error(f"Text content is empty for entity: {entity.dxftype()}")
                return None

            point = entity.dxf.insert if hasattr(entity.dxf, "insert") else (0, 0, 0)
            position = Point3D(east=point[0], north=point[1], altitude=0.0)

            color = self._get_entity_color(entity)
            layer = entity.dxf.layer if hasattr(entity.dxf, "layer") else "0"

            return DxfText(content=text_content, position=position, layer=layer, color=color)
        except Exception:
            log.error(f"_create_text_from_entity:Failed to create text data: {entity.dxftype()}")
            return None
