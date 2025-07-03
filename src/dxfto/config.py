import json
import logging
from pathlib import Path

from .models import (
    LayerData,
    Medium,
    MediumConfig,
    MediumMasterConfig,
    ObjectType,
)

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

    def _create_layer_data(self, layer_data: list[dict]) -> list[LayerData]:
        layers = []
        for layer_info in layer_data:
            layers.append(
                LayerData(
                    name=layer_info.get("Name", ""),
                    color=layer_info.get("Farbe"),
                    block=layer_info.get("Block"),
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
            if shape_type.value.lower() != shape.lower():
                continue
            return shape_type
        log.warning(f"Unknown shape type: {shape}, defaulting to UNKNOWN")
        return ObjectType.UNKNOWN

    def _create_medium_config(self, medium_name: str, config: dict) -> MediumConfig:
        object_id = config.get("FDK_ID", "UNKNOWN")
        if len(object_id) == 0:
            log.warning(f"FDK_ID is empty for medium {medium_name}, defaulting to 'UNKNOWN'")
            object_id = "UNKNOWN"

        return MediumConfig(
            medium=medium_name,
            geometry=self._create_layer_data(config.get("Geometrie", [])),
            text=self._create_layer_data(config.get("Text", [])),
            family=config.get("Family", "NO FAMILY"),
            family_type=config.get("FamilyType", "NO FAMILY TYPE"),
            object_type=self._create_default_shape(config.get("Category", "NONE")),
            default_unit=self._create_default_unit(config.get("Unit", "mm")),
            elevation_offset=config.get("ElevationOffset", 0.0),
            object_id=object_id,
        )

    def _create_medium_configs(self, medium: str, configs: list[dict]) -> list[MediumConfig]:
        medium_configs = []
        for config in configs:
            medium_configs.append(self._create_medium_config(medium, config))
        return medium_configs

    def _create_master_config(self, medium: str, medium_master: dict) -> MediumMasterConfig:
        return MediumMasterConfig(
            medium=medium,
            point_based=self._create_medium_configs(medium, medium_master.get("Element", [])),
            line_based=self._create_medium_configs(medium, medium_master.get("Leitung", [])),
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
                self.mediums[medium_name] = Medium(
                    name=medium_name, config=self._create_master_config(medium_name, medium_data)
                )

        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON in configuration file: {e}", e.doc, e.pos) from e
