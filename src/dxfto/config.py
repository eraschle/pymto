import json
from pathlib import Path

from .models import AssignmentConfig, LayerData, Medium


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
        self.medium_configs: dict[str, Medium] = {}

    @property
    def text_count(self) -> int:
        count = 0
        for medium in self.medium_configs.values():
            count += len(medium.element_data.texts)
            count += len(medium.line_data.texts)
        return count

    @property
    def element_count(self) -> int:
        count = 0
        for medium in self.medium_configs.values():
            count += len(medium.element_data.elements)
            count += len(medium.line_data.elements)
        return count

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

    def _create_assignment(self, assignments: dict) -> AssignmentConfig:
        return AssignmentConfig(
            geometry=self._create_layers(assignments.get("Geometrie", [])),
            text=self._create_layers(assignments.get("Text", [])),
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

                self.medium_configs[medium_name] = Medium(
                    name=medium_name,
                    elements=self._create_assignment(object_data),
                    lines=self._create_assignment(line_data),
                )

        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(f"Invalid JSON in configuration file: {e}", e.doc, e.pos) from e
