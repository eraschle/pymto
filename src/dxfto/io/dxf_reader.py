"""DXF file reader for extracting pipes, shafts, and texts.

This module handles reading DXF files using the ezdxf library and
extracting the relevant geometric entities (lines, polylines, circles,
rectangles, and text elements).
"""

from pathlib import Path

from ezdxf.entities.dxfentity import DXFEntity
import ezdxf.filemanagement as ezdxf
from ezdxf.document import Drawing
from ezdxf.lldxf.const import DXFError

from ..models import (
    DXFText,
    Pipe,
    Point3D,
    RectangularDimensions,
    RoundDimensions,
    Shaft,
    ShapeType,
)


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

    def extract_pipes(self) -> list[Pipe]:
        """Extract pipe geometries from DXF file.

        Pipes are identified as LINE and POLYLINE entities.
        Shape and dimensions are inferred from the geometry.

        Returns
        -------
        list[Pipe]
            List of extracted pipes
        """
        if self._doc is None:
            raise RuntimeError("DXF file not loaded. Call load_file() first.")

        pipes = []

        for entity in self._doc.modelspace():
            if entity.dxftype() in ("LINE", "POLYLINE", "LWPOLYLINE"):
                pipe = self._create_pipe_from_entity(entity)
                if pipe:
                    pipes.append(pipe)

        return pipes

    def extract_shafts(self) -> list[Shaft]:
        """Extract shaft geometries from DXF file.

        Shafts are identified as CIRCLE and rectangular entities
        (POLYLINE forming rectangles, or INSERT blocks).

        Returns
        -------
        list[Shaft]
            List of extracted shafts
        """
        if self._doc is None:
            raise RuntimeError("DXF file not loaded. Call load_file() first.")

        shafts = []

        for entity in self._doc.modelspace():
            if entity.dxftype() == "CIRCLE":
                shaft = self._create_round_shaft_from_circle(entity)
                if shaft:
                    shafts.append(shaft)
            elif entity.dxftype() in ("POLYLINE", "LWPOLYLINE"):
                shaft = self._create_rectangular_shaft_from_polyline(entity)
                if shaft:
                    shafts.append(shaft)

        return shafts

    def extract_texts(self) -> list[DXFText]:
        """Extract text elements from DXF file.

        Text elements contain dimension information for pipes
        and are spatially assigned to them.

        Returns
        -------
        list[DXFText]
            List of extracted text elements
        """
        if self._doc is None:
            raise RuntimeError("DXF file not loaded. Call load_file() first.")

        texts = []

        for entity in self._doc.modelspace():
            if entity.dxftype() in ("TEXT", "MTEXT"):
                text = self._create_text_from_entity(entity)
                if text:
                    texts.append(text)

        return texts

    def _create_pipe_from_entity(self, entity: DXFEntity) -> Pipe | None:
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
            points = self._extract_points_from_entity(entity)
            if not points:
                return None

            # For now, assume round pipes with default diameter
            # In a real implementation, this would be determined from
            # text assignments or other DXF attributes
            dimensions = RoundDimensions(diameter=200.0)  # Default 200mm

            color = self._get_entity_color(entity)
            layer = entity.dxf.layer if hasattr(entity.dxf, "layer") else "0"

            return Pipe(
                shape=ShapeType.ROUND,
                points=points,
                dimensions=dimensions,
                layer=layer,
                color=color,
            )
        except Exception:
            return None

    def _create_round_shaft_from_circle(self, entity: DXFEntity) -> Shaft | None:
        """Create a round Shaft object from a DXF circle entity.

        Parameters
        ----------
        entity : DXFEntity
            DXF CIRCLE entity

        Returns
        -------
        Shaft | None
            Shaft object or None if entity cannot be processed
        """
        try:
            center = entity.dxf.center
            radius = entity.dxf.radius

            position = Point3D(x=center.x, y=center.y, z=0.0)  # Z will be filled from LandXML
            dimensions = RoundDimensions(diameter=radius * 2)

            color = self._get_entity_color(entity)
            layer = entity.dxf.layer if hasattr(entity.dxf, "layer") else "0"

            return Shaft(
                shape=ShapeType.ROUND,
                position=position,
                dimensions=dimensions,
                layer=layer,
                color=color,
            )
        except Exception:
            return None

    def _create_rectangular_shaft_from_polyline(self, entity: DXFEntity) -> Shaft | None:
        """Create a rectangular Shaft object from a closed polyline.

        Parameters
        ----------
        entity : DXFEntity
            DXF POLYLINE or LWPOLYLINE entity

        Returns
        -------
        Shaft | None
            Shaft object or None if entity is not a valid rectangle
        """
        try:
            points = self._extract_points_from_entity(entity)
            if len(points) < 4:
                return None

            # Simple rectangular detection - check if closed and has 4 corners
            if not entity.is_closed or len(points) != 4:
                return None

            # Calculate center point
            center_x = sum(p.x for p in points) / len(points)
            center_y = sum(p.y for p in points) / len(points)
            position = Point3D(x=center_x, y=center_y, z=0.0)

            # Calculate dimensions (simplified)
            width = abs(points[1].x - points[0].x)
            length = abs(points[2].y - points[1].y)

            dimensions = RectangularDimensions(
                length=length,
                width=width,
                angle=0.0,  # Simplified - assume no rotation
            )

            color = self._get_entity_color(entity)
            layer = entity.dxf.layer if hasattr(entity.dxf, "layer") else "0"

            return Shaft(
                shape=ShapeType.RECTANGULAR,
                position=position,
                dimensions=dimensions,
                layer=layer,
                color=color,
            )
        except Exception:
            return None

    def _create_text_from_entity(self, entity: DXFEntity) -> DXFText | None:
        """Create a DXFText object from a DXF text entity.

        Parameters
        ----------
        entity : DXFEntity
            DXF TEXT or MTEXT entity

        Returns
        -------
        DXFText | None
            DXFText object or None if entity cannot be processed
        """
        try:
            text_content = entity.dxf.text if hasattr(entity.dxf, "text") else ""
            if not text_content:
                return None

            insert_point = entity.dxf.insert if hasattr(entity.dxf, "insert") else (0, 0, 0)
            position = Point3D(x=insert_point[0], y=insert_point[1], z=0.0)

            color = self._get_entity_color(entity)
            layer = entity.dxf.layer if hasattr(entity.dxf, "layer") else "0"

            return DXFText(content=text_content, position=position, layer=layer, color=color)
        except Exception:
            return None

    def _extract_points_from_entity(self, entity: DXFEntity) -> list[Point3D]:
        """Extract points from a DXF entity.

        Parameters
        ----------
        entity : DXFEntity
            DXF entity to extract points from

        Returns
        -------
        list[Point3D]
            List of 3D points (Z coordinate set to 0.0)
        """
        points = []

        if entity.dxftype() == "LINE":
            start = entity.dxf.start
            end = entity.dxf.end
            points = [Point3D(x=start.x, y=start.y, z=0.0), Point3D(x=end.x, y=end.y, z=0.0)]
        elif entity.dxftype() in ("POLYLINE", "LWPOLYLINE"):
            for vertex in entity.vertices:
                points.append(Point3D(x=vertex[0], y=vertex[1], z=0.0))

        return points

    def _get_entity_color(self, entity: DXFEntity) -> tuple[int, int, int]:
        """Get RGB color of a DXF entity.

        Parameters
        ----------
        entity : DXFEntity
            DXF entity to get color from

        Returns
        -------
        tuple[int, int, int]
            RGB color values (default: black if not specified)
        """
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
