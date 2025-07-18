"""Data models for DXF processing and Revit export.

This module contains the dataclasses that represent the core entities
processed from DXF files: shafts (Schächte), pipes (Leitungen), and texts.
"""

import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Generic, TypeGuard, TypeVar

import numpy as np

log = logging.getLogger(__name__)


class ShapeType(Enum):
    UNKNOWN = "UNKNOWN"
    ROUND = "ROUND"
    RECTANGULAR = "RECTANGULAR"


class ObjectType(Enum):
    UNKNOWN = "UNKNOWN"
    PIPE = "PIPE"  # Alle Leitungen unabhängig vom Medium
    DUCT = "DUCT"  # Kanal (Rechteckig) wie für Kabel oder Luft
    CONDUIT_BANK = "CONDUIT_BANK"  # Kabelrohr-Block
    GUTTER = "GUTTER"  # Rinne wie für Regenwasser
    SHAFT = "SHAFT"  # Either round or rectangular shaft
    SHAFT_ROUND = "SHAFT_ROUND"  # Schacht (Abwasser)
    SHAFT_RECTANGULAR = "SHAFT_RECTANGULAR"  # Schacht Rechteckig
    SHAFT_SPECIAL = "SHAFT_SPECIAL"  # Wasser Spezialbauwerk
    VALUE = "VALUE"  # Armatur als Ueberbegriff
    DISTRIBUTION_BOARD = "DISTRIBUTION_BOARD"  # Verteilerkasten
    CONSUMER = "CONSUMER"  # Verbraucher wie Hydrant oder leuchten
    MAST = "MAST"  # Masten wie für Strassenbeleuchtung


class ValueType(Enum):
    UNKNOWN = "UNKNOWN"
    STRING = "STRING"
    INT = "INT"
    FLOAT = "FLOAT"
    BOOLEAN = "BOOLEAN"
    DATETIME = "DATETIME"
    ENUM = "ENUM"


class Unit(Enum):
    UNKNOWN = "UNKNOWN"
    MILLIMETER = "MM"
    CENTIMETER = "CM"
    METER = "M"
    KILOMETER = "KM"
    DEGREE = "DEGREE"
    PERCENT = "%"


def is_int(val: Any) -> TypeGuard[int]:
    """Check if val is a float."""
    if isinstance(val, int):
        return True
    if not isinstance(val, str):
        val = str(val)
    try:
        int(val)
        return True
    except ValueError:
        return False


def to_int(val: Any) -> int:
    """Convert value to int."""
    if isinstance(val, int):
        return val
    if is_float(val):
        return int(val)
    if not isinstance(val, str):
        val = str(val)
    try:
        return int(val)
    except ValueError:
        return 0


def is_float(val: Any) -> TypeGuard[float]:
    """Check if val is a float."""
    if isinstance(val, float):
        return True
    if not isinstance(val, str):
        val = str(val)
    try:
        float(val)
        return True
    except ValueError:
        return False


def to_float(val: Any) -> float:
    """Convert value to float."""
    if isinstance(val, float):
        return val
    if is_int(val):
        return float(val)
    if not isinstance(val, str):
        val = str(val)
    try:
        return float(val)
    except ValueError:
        return 0.0


def is_boolean(val: Any) -> bool:
    """Check if val is a float."""
    if isinstance(val, bool):
        return True
    if is_int(val):
        return int(val) in (0, 1)
    if is_float(val):
        return float(val) in (0, 1)
    if not isinstance(val, str):
        val = str(val).lower()
    return val in ("true", "false", "1", "0", "yes", "no", "ja", "nein")


def to_bool(val: Any) -> bool:
    """Convert value to boolean."""
    if isinstance(val, bool):
        return val
    if is_int(val):
        return int(val) != 0
    if is_float(val):
        return float(val) != 0.0
    if not isinstance(val, str):
        val = str(val).lower()
    return val in ("true", "1", "yes", "ja")


def get_value_type(value: Any, value_type: ValueType | str) -> tuple[Any, ValueType]:
    """Get the value and its type."""
    if isinstance(value_type, str):
        value_type = ValueType(value_type.upper())
    if value_type != ValueType.UNKNOWN:
        return value, value_type
    if is_boolean(value):
        return to_bool(value), ValueType.BOOLEAN
    if is_int(value):
        return to_int(value), ValueType.INT
    if is_float(value):
        return to_float(value), ValueType.FLOAT
    return str(value).strip(), ValueType.STRING


class Parameter:
    def __init__(
        self, name: str, value: Any, value_type: ValueType = ValueType.UNKNOWN, unit: Unit = Unit.UNKNOWN
    ) -> None:
        """Initialize a parameter with name, value, type and optional unit."""
        value, value_type = get_value_type(value, value_type)
        self.name = name
        self.value = value
        self.value_type = value_type
        self.unit = unit if isinstance(unit, Unit) else Unit(str(unit).upper())

    @property
    def has_value(self) -> bool:
        return self.value is not None

    def to_dict(self) -> dict[str, Any]:
        """Convert parameter to dictionary format."""
        param_dict = {
            "name": self.name,
            "value": self.value.value if isinstance(self.value, Enum) else self.value,
            "value_type": self.value_type.value,
        }
        if self.unit != Unit.UNKNOWN:
            param_dict["unit"] = self.unit.value
        return param_dict

    def __str__(self) -> str:
        if self.unit is None:
            return f"Parameter(name={self.name}, value={self.value})"
        return f"Parameter(name={self.name}, value={self.value}, unit={self.unit})"

    def __repr__(self) -> str:
        return self.__str__()

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, Parameter):
            return False
        return self.name == value.name

    def __hash__(self) -> int:
        return hash(self.name)


class FormulaParameter(Parameter):
    """Parameter with a formula to calculate its value.

    This class extends the Parameter class to include a formula for calculating
    the value of the parameter. The formula is a string that can be evaluated
    to get the value of the parameter.
    """

    placeholder_pattern = re.compile(r"\{.*?\}")

    def __init__(
        self,
        name: str,
        formula: str,
        value_type: ValueType = ValueType.UNKNOWN,
        unit: Unit = Unit.UNKNOWN,
    ):
        super().__init__(name=name, value=None, value_type=value_type, unit=unit)
        self.formula = formula

    def _find_parameter_placeholders(self) -> list[str]:
        """Get a dictionary of parameter names and their values for the element."""
        placeholders = self.placeholder_pattern.findall(self.formula)
        return [placeholder.strip("{}") for placeholder in placeholders]

    def _get_parameter_value_dict(self, element: "ObjectData") -> dict[str, Any]:
        """Get a dictionary of parameter names and their values for the element."""
        values_map = {}
        for param_name in self._find_parameter_placeholders():
            param = element.parameter_by(param_name)
            value = "None"
            if param and param.has_value:
                value = str(param.value)
            values_map[param_name] = value
        return values_map

    def calculate_value(self, element: "ObjectData") -> None:
        """Calculate the value using the formula."""
        param_values = self._get_parameter_value_dict(element)
        formula = self.formula
        for param_name, value in param_values.items():
            placeholder = f"{{{param_name}}}"
            formula = formula.replace(placeholder, str(value))
        self.value = eval(formula)


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

    def is_within(self, other: "Point3D", tolerance: float) -> bool:
        """Check if this point is within a tolerance of another point.

        Parameters
        ----------
        other : Point3D
            The other point to compare with
        tolerance : float
            The tolerance distance to consider as "within"

        Returns
        -------
        bool
            True if this point is within the tolerance of the other point, False otherwise
        """
        distance = self.distance_2d(other)
        return distance <= tolerance

    def __eq__(self, value: object, /) -> bool:
        if not isinstance(value, Point3D):
            return False
        return (
            np.isclose(self.east, value.east)
            and np.isclose(self.north, value.north)
            and np.isclose(self.altitude, value.altitude)
        )

    def __hash__(self) -> int:
        """Get hash value for the point."""
        return hash((self.east, self.north, self.altitude))


def _get_parameters(instance: object) -> list[Parameter]:
    """Get parameters from an object.

    Parameters
    ----------
    obj : Any
        Object to extract parameters from

    Returns
    -------
    list[Parameter]
        List of parameters extracted from the object
    """
    params = []
    for _, param in instance.__dict__.items():
        if not isinstance(param, Parameter) or not param.has_value:
            continue
        params.append(param)
    return params


TValue = TypeVar("TValue")


class ParameterDescriptor(Generic[TValue]):
    """Descriptor for parameters in a class.

    This descriptor allows access to parameters as attributes.
    It is used to define parameters in classes that inherit from it.
    """

    def __init__(self, value_type: type[TValue]):
        self.value_type = value_type

    def __set_name__(self, owner: type, attr_name: str) -> None:
        """Set the name of the parameter."""
        self.attr_name = "_" + attr_name

    def _get_parameter(self, instance: object) -> Parameter:
        """Get the parameter from the instance."""
        parameter = getattr(instance, self.attr_name, None)
        if parameter is None:
            message = f"Parameter '{self.attr_name}' is not set in {instance.__class__.__name__}."
            raise ValueError(message)
        return parameter

    def __get__(self, instance: object, owner: type) -> TValue:
        """Get the parameter value."""
        parameter = self._get_parameter(instance)
        value = parameter.value
        if value is None:
            message = f"Parameter '{self.attr_name}' has no value set."
            raise ValueError(message)
        return value

    def __set__(self, instance: object, value: Any) -> None:
        """Set the parameter value."""
        if value is None:
            return
        if self.value_type is bool and not is_boolean(value):
            value = to_bool(value)
        if self.value_type is int and not is_int(value):
            value = to_int(value)
        if self.value_type is float and not is_float(value):
            value = to_float(value)
        parameter = self._get_parameter(instance)
        parameter.value = value


class Dimension:
    depth = ParameterDescriptor(float)
    width = ParameterDescriptor(float)
    length = ParameterDescriptor(float)
    angle = ParameterDescriptor(float)
    diameter = ParameterDescriptor(float)

    height = ParameterDescriptor(float)

    def __init__(
        self,
        shape: ShapeType,
        height: float | None = None,
        diameter: float | None = None,
        depth: float | None = None,
        width: float | None = None,
        length: float | None = None,
        angle: float | None = None,
    ) -> None:
        self._height = Parameter(name="Height", value=height, value_type=ValueType.FLOAT, unit=Unit.METER)
        self._diameter = Parameter(name="Diameter", value=diameter, value_type=ValueType.FLOAT, unit=Unit.METER)
        self._depth = Parameter(name="Depth", value=depth, value_type=ValueType.FLOAT, unit=Unit.METER)
        self._width = Parameter(name="Width", value=width, value_type=ValueType.FLOAT, unit=Unit.METER)
        self._length = Parameter(name="Length", value=length, value_type=ValueType.FLOAT, unit=Unit.METER)
        self._angle = Parameter(name="XY rotation (azimuth)", value=angle, value_type=ValueType.FLOAT, unit=Unit.DEGREE)
        self._shape_type = Parameter(name="Shape Type", value=shape, value_type=ValueType.ENUM)
        self._default_values = Parameter(name="Default Values Set", value=False, value_type=ValueType.BOOLEAN)

    @property
    def is_round(self) -> bool:
        """Check if the shape is round."""
        return self._shape_type.value == ShapeType.ROUND

    @property
    def is_rectangular(self) -> bool:
        """Check if the shape is rectangular."""
        return self._shape_type.value == ShapeType.RECTANGULAR

    @property
    def has_diameter(self) -> bool:
        try:
            return self.diameter > 0.0
        except ValueError:
            return False

    @property
    def has_depth(self) -> bool:
        try:
            return self.depth > 0.0
        except ValueError:
            return False

    @property
    def has_width(self) -> bool:
        try:
            return self.width > 0.0
        except ValueError:
            return False

    @property
    def has_height(self) -> bool:
        try:
            return self.height > 0.0
        except ValueError:
            return False

    @property
    def has_angle(self) -> bool:
        try:
            return self.angle > 0.0
        except ValueError:
            return False

    @property
    def has_length(self) -> bool:
        try:
            return self.length > 0.0
        except ValueError:
            return False

    def has_valid_values(self) -> bool:
        """Check if the object has valid dimension values.

        Returns
        -------
        bool
            True if valid values are set, False otherwise.
        """
        if self.is_round:
            return self.has_diameter and self.has_height
        if self.is_rectangular:
            return self.has_depth and self.has_width and self.has_height
        return self._shape_type != ShapeType.UNKNOWN

    def _set_round_defaults(self, config: "MediumConfig") -> None:
        if config.default_diameter is not None and not self.has_diameter:
            self.diameter = config.default_diameter
        self._shape_type.value = ShapeType.ROUND
        self._angle.value = None

    def _set_rectangular_defaults(self, config: "MediumConfig") -> None:
        if config.default_width is not None and not self.has_width:
            self.width = config.default_width
        if config.default_depth is not None and not self.has_depth:
            self.depth = config.default_depth
        self._shape_type.value = ShapeType.RECTANGULAR

    def set_default_values(self, config: "MediumConfig") -> None:
        """Set default values for the dimensions."""
        if self._default_values.value is True:
            return
        if self.is_round and config.has_round_default():
            self._set_round_defaults(config)
        elif self.is_rectangular and config.has_rectangular_default():
            self._set_rectangular_defaults(config)

        if config.default_height is not None and not self.has_height:
            self.height = config.default_height
        self._default_values.value = True

    def dimensions_updated(self) -> None:
        self._default_values.value = False

    def reset_round_dimension(self) -> None:
        """Reset dimensions for round shape."""
        self._diameter.value = None

    def reset_rectangular_dimension(self) -> None:
        """Reset dimensions for rectangular shape."""
        self._depth.value = None
        self._width.value = None

    def set_shape_type(self, shape_type: ShapeType) -> None:
        self._shape_type.value = shape_type

    def to_parameters(self) -> list[Parameter]:
        """Get parameters as a dictionary."""
        return _get_parameters(self)

    def __repr__(self) -> str:
        return self.__str__()


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

    def __init__(self, uuid: str, medium: str, content: str, position: Point3D, layer: str) -> None:
        self._uuid = uuid
        self.medium = medium
        self._content = Parameter(name="Kommentare", value=content, value_type=ValueType.STRING)
        self.position: Point3D = position
        self.layer = layer
        # self.color = color

    @property
    def uuid(self) -> str:
        """Get the unique identifier of the text."""
        return self._uuid

    @property
    def content(self) -> str:
        """Get the text content."""
        return self._content.value

    @content.setter
    def content(self, value: str) -> None:
        """Set the text content."""
        self._content.value = value

    def to_parameters(self) -> list[Parameter]:
        """Get parameters as a dictionary."""
        return [self._content]


@dataclass(slots=True)
class LayerData:
    name: str | None = field(repr=True, compare=True)
    color: str | int | tuple[int, int, int] | None = field(repr=True, compare=True)
    block: str | None = field(default=None, repr=True, compare=True)

    @property
    def is_block_query(self) -> bool:
        """Check if this layer is a block query."""
        if self.is_block_name_query:
            return True
        if self.is_block_startswith_query:
            return True
        return self.is_block_endswith_query

    @property
    def is_block_name_query(self) -> bool:
        """Check if this layer is a block query."""
        if not _is_block_query(self.block):
            return False
        return not _is_start_or_endswith_query(self.block)

    @property
    def is_block_startswith_query(self) -> bool:
        """Check if this layer is a block query."""
        return _is_startswith_query(self.block)

    @property
    def is_block_endswith_query(self) -> bool:
        """Check if this layer is a block query."""
        return _is_endswith_query(self.block)

    @property
    def is_block_start_or_endswith_query(self) -> bool:
        """Check if this layer is a block query."""
        return _is_start_or_endswith_query(self.block)


@dataclass(unsafe_hash=True)
class ObjectData:
    """Base class for all DXF objects.

    This class serves as a base for other DXF-related data classes.
    It can be extended with common properties or methods in the future.
    """

    uuid: str  # from ezdxf
    medium: str
    object_type: ObjectType
    dimension: Dimension
    family: str
    family_type: str

    assigned_text: DxfText | None = None
    points: list[Point3D] = field(default_factory=list, repr=False, compare=False)
    parameters: list[Parameter] = field(default_factory=list, repr=False, compare=False)

    @property
    def point(self) -> Point3D:
        """Single or Start point of the object."""
        return self.points[0]

    @property
    def has_end_point(self) -> bool:
        """Check if the object has an end point."""
        return len(self.points) > 1

    @property
    def end_point(self) -> Point3D:
        """End point of the line-based object. Point-based objects return None"""
        if len(self.points) == 1:
            raise ValueError("Element has no end point. Did you check 'has_end_point'?")
        return self.points[-1]

    @property
    def is_line_based(self) -> bool:
        """Check if the object is line-based (e.g., pipe, cable duct)."""
        return self.has_end_point

    @property
    def is_point_based(self) -> bool:
        """Check if the object is point-based (e.g., shaft)."""
        return len(self.points) == 1

    def add_parameter(self, parameter: Parameter) -> None:
        if parameter in self.parameters:
            return
        self.parameters.append(parameter)

    def parameter_by(self, name: str) -> Parameter | None:
        """Get a parameter by its name."""
        for param in self.get_parameters(update=False):
            if param.name == name:
                return param
        return None

    def get_parameters(self, update: bool) -> list[Parameter]:
        """Get all parameters of the object.

        Parameters
        ----------
        update : bool
            If True, update the values of FormulaParameters before returning

        Returns
        -------
        list[Parameter]
            List of parameters sorted by name
        """
        params = []
        if self.assigned_text is not None:
            params.extend(self.assigned_text.to_parameters())
        params.extend(self.dimension.to_parameters())
        params.extend(self.parameters)
        if update:
            for param in params:
                if not isinstance(param, FormulaParameter):
                    continue
                param.calculate_value(self)
        return sorted(params, key=lambda param: param.name)


def _is_block_query(block_query: str | None) -> TypeGuard[str]:
    """Check if the layer is a block query."""
    if block_query is None or not isinstance(block_query, str):
        return False
    return len(block_query.strip()) > 0


def _is_startswith_query(query: str | None) -> TypeGuard[str]:
    """Check if the layer is a block query."""
    if not _is_block_query(query):
        return False
    return query.endswith("*")


def _is_endswith_query(query: str | None) -> TypeGuard[str]:
    """Check if the layer is a block query."""
    if not _is_block_query(query):
        return False
    return query.startswith("*")


def _is_start_or_endswith_query(query: str | None) -> TypeGuard[str]:
    """Check if the layer is a block query."""
    if not _is_block_query(query):
        return False
    return _is_startswith_query(query) or _is_endswith_query(query)


@dataclass(slots=True)
class LayerGroup:
    geometry: list[LayerData] = field(default_factory=list, repr=True, compare=True)
    text: list[LayerData] = field(default_factory=list, repr=True, compare=True)


@dataclass(slots=True)
class MediumConfig:
    medium: str
    layer_group: LayerGroup
    default_unit: Unit
    family: str
    family_type: str
    object_type: ObjectType
    object_id: str
    elevation_offset: float = 0.0
    default_width: float | None = None
    default_depth: float | None = None
    default_diameter: float | None = None
    default_height: float | None = None
    parameters: list[Parameter] = field(default_factory=list, repr=False, compare=False)

    def _is_default(self, value) -> bool:
        """Check if the configuration has a round default."""
        if value is None:
            return False
        if isinstance(value, (int | float)):
            return value > 0.0
        return False

    def has_round_default(self) -> bool:
        """Check if the configuration has a round default."""
        return self._is_default(self.default_diameter)

    def has_rectangular_default(self) -> bool:
        """Check if the configuration has a rectangular default."""
        return all(self._is_default(attr) for attr in (self.default_width, self.default_depth))

    def has_height_default(self) -> bool:
        """Check if the configuration has a height default."""
        return self._is_default(self.default_height)

    def is_line_based(self) -> bool:
        """Check if the medium configuration is line-based."""
        return self.object_type in (
            ObjectType.PIPE,
            ObjectType.DUCT,
            ObjectType.CONDUIT_BANK,
            ObjectType.GUTTER,
        )

    def is_round_line_based(self) -> bool:
        """Check if the medium configuration is round line-based."""
        if not self.is_line_based():
            return False
        return self.object_type in (ObjectType.PIPE, ObjectType.GUTTER)

    def is_rectangular_line_based(self) -> bool:
        """Check if the medium configuration is rectangular line-based."""
        if not self.is_line_based():
            return False
        return self.object_type in (ObjectType.DUCT, ObjectType.CONDUIT_BANK)

    def is_point_based(self) -> bool:
        """Check if the medium configuration is point-based."""
        return not self.is_line_based()


@dataclass(frozen=True)
class MediumMasterConfig:
    """Master configuration for medium layers.

    Contains separate configurations for point-based and line-based elements.
    Each configuration includes a list of geometry and text layers to assign,
    including default values for unit and object type.

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

    def config_by(self, object_type: ObjectType) -> MediumConfig | None:
        """Get configuration for a specific object type.

        Parameters
        ----------
        object_type : ObjectType
            The type of the object to get the configuration for

        Returns
        -------
        MediumConfig | None
            Configuration for the specified object type, or None if not found
        """
        for config in self.point_based + self.line_based:
            if config.object_type != object_type:
                continue
            return config
        return None


AssignmentGroup = tuple[list[ObjectData], list[DxfText]]


class ExtractedData:
    """Container for extracted DXF data.

    This class holds the extracted data from a DXF file, including
    pipes, shafts, and texts. It provides methods to access and manipulate
    the data.
    """

    def __init__(self) -> None:
        self._extracted: list[AssignmentGroup] = []

    @property
    def extracted(self) -> list[AssignmentGroup]:
        """Get all extracted data."""
        return self._extracted

    def setup(self, medium: str, groups: list[tuple[list[ObjectData], list[DxfText]]]) -> None:
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
        for elem_group, text_group in groups:
            if not isinstance(elem_group, list) or not isinstance(text_group, list):
                log.error(f"Invalid data format for medium '{medium}': {elem_group}, {text_group}")
                return
            for elem_data in elem_group:
                elem_data.medium = medium
            for text_data in text_group:
                text_data.medium = medium
            self._extracted.append((elem_group, text_group))


class AssignmentData:
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

    point_data: AssignmentData = field(default_factory=AssignmentData, repr=False, compare=False)
    line_data: AssignmentData = field(default_factory=AssignmentData, repr=False, compare=False)

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

    def get_point_elements(self) -> list[ObjectData]:
        """Get all assigned elements for this medium."""
        assigned_elements = []
        for elements, _ in self.point_data.assigned:
            assigned_elements.extend(elements)
        return assigned_elements

    def get_line_elements(self) -> list[ObjectData]:
        """Get all assigned elements for this medium."""
        assigned_elements = []
        for elements, _ in self.line_data.assigned:
            assigned_elements.extend(elements)
        return assigned_elements

    def get_assignment_elements(self) -> list[ObjectData]:
        """Get all assigned elements for this medium."""
        assigned_elements = []
        assigned_elements.extend(self.get_point_elements())
        assigned_elements.extend(self.get_line_elements())
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
