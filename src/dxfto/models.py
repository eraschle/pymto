"""Data models for DXF processing and Revit export.

This module contains the dataclasses that represent the core entities
processed from DXF files: shafts (Schächte), pipes (Leitungen), and texts.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import ClassVar

import numpy as np

log = logging.getLogger(__name__)


class ObjectType(Enum):
    """Shape types for pipes and shafts."""

    UNKNOWN = "unknown"
    SHAFT = "shaft"
    PIPE_WASTEWATER = "wastewater"
    PIPE_WATER = "water"
    PIPE_GAS = "gas"
    CABLE_DUCT = "duct"


@dataclass(frozen=True)
class DxfColor:
    """Represents a color in RGB format.

    Parameters
    ----------
    r : int
        Red component (0-255)
    g : int
        Green component (0-255)
    b : int
        Blue component (0-255)
    """

    red: int
    green: int
    blue: int

    def to_tuple(self) -> tuple[int, int, int]:
        """Convert color to RGB tuple."""
        return self.red, self.green, self.blue


@dataclass(frozen=True)
class Point3D:
    """Represents a 3D point with x, y, z coordinates.

    Parameters
    ----------
    east : float
        X coordinate from DXF file
    north : float
        Y coordinate from DXF file
    altitude : float
        Z coordinate from LandXML (DGM) file
    """

    east: float
    north: float
    altitude: float

    def distance_2d(self, orher: "Point3D") -> float:
        """Calculate 2D distance between two points.

        Parameters
        ----------
        point1 : Point3D
            First point
        point2 : Point3D
            Second point

        Returns
        -------
        float
            2D Euclidean distance
        """
        dx = self.east - orher.east
        dy = self.north - orher.north
        return np.sqrt(dx**2 + dy**2)


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
class DxfText:
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

    medium: str
    content: str
    position: Point3D
    layer: str
    color: tuple[int, int, int]


@dataclass
class ObjectData:
    """Base class for all DXF objects.

    This class serves as a base for other DXF-related data classes.
    It can be extended with common properties or methods in the future.
    """

    line_based_types: ClassVar[set[ObjectType]] = {
        ObjectType.PIPE_WASTEWATER,
        ObjectType.PIPE_WATER,
        ObjectType.PIPE_GAS,
        ObjectType.CABLE_DUCT,
    }
    point_based_types: ClassVar[set[ObjectType]] = {
        ObjectType.SHAFT,
    }

    medium: str
    object_type: ObjectType
    dimensions: RectangularDimensions | RoundDimensions
    layer: str
    points: list[Point3D] = field(default_factory=list, repr=False, compare=False)
    positions: list[Point3D] = field(default_factory=list, repr=False, compare=False)
    color: tuple[int, int, int] = field(default_factory=tuple, repr=True, compare=True)
    assigned_text: DxfText | None = None

    @property
    def is_line_based(self) -> bool:
        """Check if the object is line-based (e.g., pipe, cable duct).

        Returns
        -------
        bool
            True if the object is line-based, False otherwise.
        """
        return self.object_type in self.line_based_types

    @property
    def is_point_based(self) -> bool:
        """Check if the object is point-based (e.g., shaft).

        Returns
        -------
        bool
            True if the object is point-based, False otherwise.
        """
        return self.object_type == ObjectType.SHAFT

    @property
    def should_be_round(self) -> bool:
        """Check if the object has round dimensions.

        Returns
        -------
        bool
            True if the object has round dimensions, False otherwise.
        """
        return self.object_type.name.startswith("PIPE") or self.object_type == ObjectType.SHAFT


@dataclass
class LayerData:
    name: str = field(repr=True, compare=True)
    color: str | int | tuple[int, int, int] | None = field(repr=True, compare=True)

    def __post_init__(self):
        if self.color is None:
            self.color = (0, 0, 0)


@dataclass(frozen=True)
class MediumConfig:
    medium: str
    geometry: list[LayerData]
    text: list[LayerData]
    default_unit: str = "mm"
    default_object_type: ObjectType = ObjectType.UNKNOWN


class AssingmentData:
    """Configuration per medium of DXF elements.

    Parameters
    ----------
    elements : list[ObjectData]
        List of elements assigned to this medium
    texts : list[DxfText]
        List of texts assigned to this medium
    """

    def __init__(self, elements: list[ObjectData] | None = None, texts: list[DxfText] | None = None) -> None:
        self._elements = elements if elements is not None else []
        self._texts = texts if texts is not None else []

    @property
    def elements(self) -> list[ObjectData]:
        """Get all elements assigned to this medium."""
        return self.elements

    def set_elements(self, medium: str, elements: list[ObjectData]) -> None:
        """Set elements for this medium."""
        for elem in elements:
            if not elem.is_line_based:
                log.warning(f"Element {elem} is not line-based, skipping assignment")
                raise ValueError(f"Element {elem} is not line-based")
            elem.medium = medium
        self._elements = elements

    @property
    def texts(self) -> list[DxfText]:
        """Get all texts assigned to this medium."""
        return self._texts

    def set_texts(self, medium: str, texts: list[DxfText]) -> None:
        """Set texts for this medium."""
        for text in texts:
            text.medium = medium
        self._texts = texts

    def update(self, medium: str, data: "AssingmentData") -> None:
        """Update elements and texts for this medium.

        Parameters
        ----------
        medium : str
            Name of the medium to update
        elements : list[ObjectData]
            List of elements to assign to this medium
        texts : list[DxfText]
            List of texts to assign to this medium
        """
        self.set_elements(medium, data.elements)
        self.set_texts(medium, data.texts)


@dataclass(frozen=True)
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
    elements: MediumConfig
    lines: MediumConfig
    element_data: AssingmentData = field(default_factory=AssingmentData, repr=False, compare=False)
    line_data: AssingmentData = field(default_factory=AssingmentData, repr=False, compare=False)

