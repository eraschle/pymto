import json
import logging
from pathlib import Path

from .models import LayerData, Medium, MediumConfig, ObjectType

log = logging.getLogger(__name__)


class ConfigurationHandler:
    """Groups DXF elements based on layer configuration from JSON file.

    This grouper uses a JSON configuration file that specifies which
    layers belong to which medium and groups elements accordingly.
    """

    def __init__(self, config_path: Path) -> None:
        """Initialize layer-based grouper with configuration file.

        Parameters
        ----------
        config_path : Path
            Path to JSON configuration file
        """
        self.config_path = config_path
        self.mediums: dict[str, Medium] = {}

    def _create_layers(self, layer_data: list[dict]) -> list[LayerData]:
        layers = []
        for layer_info in layer_data:
            layers.append(
                LayerData(
                    name=layer_info.get("Name", ""),
                    color=layer_info.get("Farbe", {}),
                )
            )
        return layers

    def _create_default_unit(self, unit: str) -> str:
        """Create default unit based on string representation.

        Parameters
        ----------
        unit : str
            Unit type as string (e.g., "mm", "cm", "m")
        Returns
        -------
        str
            Corresponding unit string
        """
        valid_units = {"mm", "cm", "m"}
        if unit.lower() in valid_units:
            return unit.lower()
        log.warning(f"Unknown unit type: {unit}, defaulting to 'mm'")
        return "mm"

    def _create_default_shape(self, shape: str) -> ObjectType:
        """Create default shape based on string representation.

        Parameters
        ----------
        shape : str
            Shape type as string (e.g., "RECTANGLE", "CIRCLE")
        Returns
        -------
        ShapeType
            Corresponding ShapeType enum value
        """
        for shape_type in ObjectType:
            if shape_type.name.lower() != shape.lower():
                continue
            return shape_type
        log.warning(f"Unknown shape type: {shape}, defaulting to UNKNOWN")
        return ObjectType.UNKNOWN

    def _create_config(self, medium_config: dict) -> MediumConfig:
        return MediumConfig(
            default_shape=self._create_default_shape(medium_config.get("Shape", "NONE")),
            default_unit=self._create_default_unit(medium_config.get("Unit", "mm")),
            geometry=self._create_layers(medium_config.get("Geometrie", [])),
            text=self._create_layers(medium_config.get("Text", [])),
        )

    def load_config(self) -> None:
        """Load grouping configuration from JSON file.

        Expected JSON format:
        {
            "Abwasserleitung": {
                "Leitung": {"Layer": "PIPE_SEWER", "Farbe": [255, 0, 0]},
                "Schacht": {"Layer": "SHAFT_SEWER", "Farbe": [200, 0, 0]},
                "Text": {"Layer": "TEXT_SEWER", "Farbe": [255, 100, 100]}
            }
        }

        Raises
        ------
        FileNotFoundError
            If configuration file does not exist
        json.JSONDecodeError
            If configuration file is not valid JSON
        """
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")

        try:
            with open(self.config_path, encoding="utf-8") as f:
                config_data = json.load(f)

            for medium_name, medium_data in config_data.items():
                line_data = medium_data.get("Leitung", {})
                object_data = medium_data.get("Element", {})

                self.mediums[medium_name] = Medium(
                    name=medium_name,
                    elements=self._create_config(object_data),
                    lines=self._create_config(line_data),
                )

        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON in configuration file: {e}", e.doc, e.pos) from e
