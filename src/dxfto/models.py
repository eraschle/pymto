"""Data models for DXF processing and Revit export.

This module contains the dataclasses that represent the core entities
processed from DXF files: shafts (Schächte), pipes (Leitungen), and texts.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar

import numpy as np

log = logging.getLogger(__name__)


class ObjectType(Enum):
    """Shape types for pipes and shafts."""

    UNKNOWN = "unknown"
    SHAFT = "shaft"  # Schacht (Abwasser)
    PIPE_WATER = "water"  # Wasser Leitung
    PIPE_WASTEWATER = "waste_water"  # Abwasser Leitung
    WATER_SPECIAL = "water_special"  # Wasser Spezialbauwerk
    WASTE_WATER_SPECIAL = "waser_water_special"  # Abwasser Spezialbauwerk
    CATE_VALUE = "gate_value"  # Schieber
    HYDRANT = "hydrant"  # Hydrant
    PIPE_GAS = "gas"
    CABLE_DUCT = "cable_duct"  # Kabekanal


@dataclass
class Parameter:
    name: str
    value: Any
    value_type: str
    unit: str | None = field(default=None)

    def to_dict(self) -> dict[str, Any]:
        """Convert parameter to dictionary format."""
        param_dict = {
            "name": self.name,
            "value": self.value,
            "value_type": self.value_type,
        }
        if self.unit is not None:
            param_dict["unit"] = self.unit
        return param_dict


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

    def to_parameters(self) -> list[Parameter]:
        """Get parameters as a dictionary."""
        return [
            Parameter(
                name="Länge",
                value=self.length,
                value_type="float",
                unit="m",
            ),
            Parameter(
                name="Breite",
                value=self.width,
                value_type="float",
                unit="m",
            ),
            Parameter(
                name="XY rotation (azimuth)",
                value=self.angle,
                value_type="float",
                unit="Degree",
            ),
            Parameter(
                name="Höhe",
                value=self.height if self.height is not None else 0.0,
                value_type="float",
                unit="m",
            ),
        ]


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

    def to_parameters(self) -> list[Parameter]:
        """Get parameters as a dictionary."""
        return [
            Parameter(
                name="Durchmesser",
                value=self.diameter,
                value_type="float",
                unit="m",
            ),
            Parameter(
                name="Höhe",
                value=self.height if self.height is not None else 0.0,
                value_type="float",
                unit="m",
            ),
        ]


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

    def to_parameters(self) -> list[Parameter]:
        """Get parameters as a dictionary."""
        return [
            Parameter(
                name="Text",
                value=self.content,
                value_type="string",
            )
        ]


@dataclass
class ObjectData:
    """Base class for all DXF objects.

    This class serves as a base for other DXF-related data classes.
    It can be extended with common properties or methods in the future.
    """

    @classmethod
    def point_types(cls) -> set[ObjectType]:
        """Get set of point-based object types."""
        point_based = set()
        for obj_type in ObjectType:
            if obj_type in cls.line_types:
                continue
            point_based.add(obj_type)
        return point_based

    line_types: ClassVar[set[ObjectType]] = {
        ObjectType.PIPE_WASTEWATER,
        ObjectType.PIPE_WATER,
        ObjectType.PIPE_GAS,
        ObjectType.CABLE_DUCT,
    }

    medium: str
    object_type: ObjectType
    family: str
    family_type: str
    dimensions: RectangularDimensions | RoundDimensions
    layer: str
    assigned_text: DxfText | None = None
    color: tuple[int, int, int] = field(default_factory=tuple, repr=True, compare=True)

    """points: list[Point3D]
        List of points for line-based objects."""
    points: list[Point3D] = field(default_factory=list, repr=False, compare=False)

    """positions: tuple[Point3D]
        Positions for point-based (single-point) objects.
        and for line-based objects (start- and end-point)."""
    positions: tuple[Point3D, ...] = field(default_factory=tuple, repr=True, compare=True)
    parameters: list[Parameter] = field(default_factory=list, repr=False, compare=False, init=False)

    @property
    def point(self) -> Point3D:
        """Single or Start point of the object.

        Returns
        -------
        Point3D
            Point3D representing the position of the object.
        """
        return self.positions[0]

    @property
    def end_point(self) -> Point3D | None:
        """End point of the line-based object.
        Point-based objects return None

        Returns
        -------
        Point3D | None
            Point3D representing the end position of the object, or None.
        """
        if len(self.positions) == 1:
            return None
        return self.positions[-1]

    @property
    def is_line_based(self) -> bool:
        """Check if the object is line-based (e.g., pipe, cable duct).

        Returns
        -------
        bool
            True if the object is line-based, False otherwise.
        """
        is_oject_type_line = self.object_type in self.line_types
        has_two_positions = len(self.positions) == 2
        has_end_point = self.end_point is not None
        return is_oject_type_line and has_two_positions and has_end_point

    @property
    def is_point_based(self) -> bool:
        """Check if the object is point-based (e.g., shaft).

        Returns
        -------
        bool
            True if the object is point-based, False otherwise.
        """
        is_oject_type_point = self.object_type in self.point_types()
        is_single_position = len(self.positions) == 1
        return is_oject_type_point and is_single_position

    def get_parameters(self) -> list[Parameter]:
        """Get parameters for the object.

        Returns
        -------
        list[Parameter]
            List of parameters associated with the object.
        """
        params = []
        if self.assigned_text is not None:
            params.extend(self.assigned_text.to_parameters())
        if isinstance(self.dimensions, RectangularDimensions):
            params.extend(self.dimensions.to_parameters())
        if isinstance(self.dimensions, RoundDimensions):
            params.extend(self.dimensions.to_parameters())
        params.extend(self.parameters)
        return params


@dataclass(slots=True)
class LayerData:
    name: str = field(repr=True, compare=True)
    color: str | int | tuple[int, int, int] | None = field(repr=True, compare=True)
    block: str | None = field(default=None, repr=True, compare=True)


@dataclass(slots=True)
class MediumConfig:
    medium: str
    geometry: list[LayerData]
    text: list[LayerData]
    family: str
    family_type: str
    elevation_offset: float
    default_unit: str
    object_type: ObjectType


@dataclass(frozen=True)
class MediumMasterConfig:
    """Master configuration for medium layers.

    Contains separate configurations for point-based and line-based elements.
    Each configuration includes a list of geometry and text layers to assign,
    inluding default values for unit and object type.

    Parameters
    ----------
    point_based : list[MediumConfig]
        List of configurations for point-based elements (e.g., shafts)
    line_based : list[MediumConfig]
        List of configurations for line-based elements (e.g., pipes, ducts)
    """

    medium: str
    point_based: list[MediumConfig] = field(default_factory=list, repr=True, compare=True)
    line_based: list[MediumConfig] = field(default_factory=list, repr=True, compare=True)


AssingmentGroup = tuple[list[ObjectData], list[DxfText]]


class ExtractedData:
    """Container for extracted DXF data.

    This class holds the extracted data from a DXF file, including
    pipes, shafts, and texts. It provides methods to access and manipulate
    the data.
    """

    def __init__(self) -> None:
        self._extracted: list[AssingmentGroup] = []

    @property
    def extracted(self) -> list[AssingmentGroup]:
        """Get all extracted data."""
        return self._extracted

    def setup(self, medium: str, elements: list[list[ObjectData]], texts: list[list[DxfText]]) -> None:
        """Setup assignment data for a medium.

        Parameters
        ----------
        medium : str
            Name of the medium
        elements : list[list[ObjectData]]
            List of elements assigned to this medium
        texts : list[list[DxfText]]
            List of texts assigned to this medium
        """
        for elem_group, text_group in zip(elements, texts, strict=True):
            if not isinstance(elem_group, list) or not isinstance(text_group, list):
                log.error(f"Invalid data format for medium '{medium}': {elem_group}, {text_group}")
                continue
            for elem_data in elem_group:
                elem_data.medium = medium
            for text_data in text_group:
                text_data.medium = medium
            self._extracted.append((elem_group, text_group))


class AssingmentData:
    """Configuration per medium of DXF elements.

    Parameters
    ----------
    elements : list[ObjectData]
        List of elements assigned to this medium
    texts : list[DxfText]
        List of texts assigned to this medium
    """

    def __init__(self) -> None:
        self._assigned: list[tuple[list[ObjectData], MediumConfig]] = []

    @property
    def assigned(self) -> list[tuple[list[ObjectData], MediumConfig]]:
        """Get all elements that have been assigned texts."""
        return self._assigned

    def add_assignment(self, config: MediumConfig, elements: list[ObjectData]) -> None:
        """Add an assignment of elements to a medium configuration.

        Parameters
        ----------
        config : MediumConfig
            Configuration for the medium
        elements : list[ObjectData]
            List of elements assigned to this medium
        """
        self._assigned.append((elements, config))


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
    config: MediumMasterConfig

    extracted_point: ExtractedData = field(default_factory=ExtractedData, repr=False, compare=False)
    extracted_line: ExtractedData = field(default_factory=ExtractedData, repr=False, compare=False)

    point_data: AssingmentData = field(default_factory=AssingmentData, repr=False, compare=False)
    line_data: AssingmentData = field(default_factory=AssingmentData, repr=False, compare=False)

    def _get_statistics(
        self,
        extracted: list[tuple[list[ObjectData], list[DxfText]]],
        assigned: list[tuple[list[ObjectData], MediumConfig]],
    ) -> dict[str, int | float]:
        """Calculate statistics for extracted and assigned elements."""
        assigned_count = sum(
            len([elem for elem in elements if elem.assigned_text is not None]) for elements, _ in assigned
        )
        return {
            "elements": sum(len(elements) for elements, _ in extracted),
            "texts": sum(len(texts) for _, texts in extracted),
            "assigned": assigned_count,
        }

    def get_assignment_elements(self) -> list[ObjectData]:
        """Get all assigned elements for this medium."""
        assigned_elements = []
        for elements, _ in self.point_data.assigned:
            assigned_elements.extend(elements)
        for elements, _ in self.line_data.assigned:
            assigned_elements.extend(elements)
        return assigned_elements

    def get_point_statistics(self) -> dict[str, int | float]:
        """Calculate statistics for point based assignments."""
        return self._get_statistics(self.extracted_point.extracted, self.point_data.assigned)

    def get_line_statistics(self) -> dict[str, int | float]:
        """Calculate statistics for line based assignments."""
        return self._get_statistics(self.extracted_line.extracted, self.line_data.assigned)

    def _get_total(self, assigned: list[tuple[list[ObjectData], MediumConfig]]) -> int:
        """Calculate the total number of assigned elements."""
        return sum([len(elems) for elems, _ in assigned])

    def get_point_total(self) -> int:
        """Calculate the total number of assigned point elements."""
        return sum([len(elems) for elems, _ in self.point_data.assigned])

    def get_line_total(self) -> int:
        """Calculate the total number of assigned line elements."""
        return sum([len(elems) for elems, _ in self.line_data.assigned])
