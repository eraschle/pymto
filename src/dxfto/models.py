"""Data models for DXF processing and Revit export.

This module contains the dataclasses that represent the core entities
processed from DXF files: shafts (Schächte), pipes (Leitungen), and texts.
"""

from dataclasses import dataclass, field
from enum import Enum

from shapely.shape import Point
from im


class ShapeType(Enum):
    """Shape types for pipes and shafts."""

    RECTANGULAR = "rectangular"
    ROUND = "round"


@dataclass
class Point3D:
    """Represents a 3D point with x, y, z coordinates.

    Parameters
    ----------
    x : float
        X coordinate from DXF file
    y : float
        Y coordinate from DXF file
    z : float
        Z coordinate from LandXML (DGM) file
    """

    x: float
    y: float
    z: float


@dataclass
class RectangularDimensions:
    """Dimensions for rectangular shapes.

    Parameters
    ----------
    length : float
        Length of the rectangular shape
    width : float
        Width of the rectangular shape
    angle : float
        Rotation angle in degrees
    height : float | None
        Height of the rectangular shape (optional)
    """

    length: float
    width: float
    angle: float
    height: float | None = None


@dataclass
class RoundDimensions:
    """Dimensions for round shapes.

    Parameters
    ----------
    diameter : float
        Diameter of the round shape
    height : float | None
        Height of the round shape (optional)
    """

    diameter: float
    height: float | None = None


@dataclass
class ADXFText:
    """Represents a text element from DXF file.

    Parameters
    ----------
    content : str
        The text content
    position : Point3D
        Position of the text
    layer : str
        DXF layer name
    color : tuple[int, int, int]
        RGB color values
    """

    content: str
    position: Point3D
    layer: str
    color: tuple[int, int, int]


@dataclass
class AObject:
    """Base class for all DXF objects.

    This class serves as a base for other DXF-related data classes.
    It can be extended with common properties or methods in the future.
    """

    # Currently empty, but can be extended later
    shape: ShapeType | None
    dimensions: RectangularDimensions | RoundDimensions
    points: list[Point3D] = []
    positions: list[Point3D] = []
    layer: str
    color: tuple[int, int, int] = field(default_factory=tuple)
    assigned_text: DXFText | None = None


@dataclass
class Pipe(AObject):
    """Represents a pipe (Leitung) from DXF file.

    Parameters
    ----------
    shape : ShapeType
        Shape of the pipe (rectangular or round)
    points : list[Point3D]
        All points along the pipe geometry
    dimensions : RectangularDimensions | RoundDimensions
        Dimensions based on shape type (width/height for rectangular, diameter for round)
    layer : str
        DXF layer name
    color : tuple[int, int, int]
        RGB color values
    assigned_text : DXFText | None
        Text assigned to this pipe (optional)
    """

    shape: ShapeType
    points: list[Point3D]
    dimensions: RectangularDimensions | RoundDimensions
    layer: str
    color: tuple[int, int, int]
    assigned_text: DXFText | None = None


@dataclass
class Medium:
    """Represents a medium (e.g., Abwasserleitung) with its associated elements.

    Parameters
    ----------
    name : str
        Name of the medium (e.g., "Abwasserleitung")
    pipes : list[Pipe]
        List of pipes belonging to this medium
    shafts : list[Shaft]
        List of shafts belonging to this medium
    texts : list[DXFText]
        List of texts belonging to this medium
    """

    name: str
    pipes: list[Pipe]
    shafts: list[Shaft]
    texts: list[DXFText]


@dataclass
class GroupingConfig:
    """Configuration for grouping DXF elements by medium.

    Parameters
    ----------
    pipe_layer : str
        Layer name for pipes
    shaft_layer : str
        Layer name for shafts
    text_layer : str
        Layer name for texts
    pipe_color : tuple[int, int, int] | None
        RGB color for pipes (optional)
    shaft_color : tuple[int, int, int] | None
        RGB color for shafts (optional)
    text_color : tuple[int, int, int] | None
        RGB color for texts (optional)
    """

    pipe_layer: str
    shaft_layer: str
    text_layer: str
    pipe_color: tuple[int, int, int] | None = None
    shaft_color: tuple[int, int, int] | None = None
    text_color: tuple[int, int, int] | None = None
