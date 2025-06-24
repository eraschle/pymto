"""Grouping strategies by layer"""

from pathlib import Path

from ...models import LayerData, Medium


class LayerBasedGrouper:
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

    def group_elements(self, medium_configs: dict[str, Medium]) -> list[Medium]:
        """Group elements based on layer configuration.

        Parameters
        ----------
        medium_configs : dict[str, Medium]
            Dictionary of medium configurations

        Returns
        -------
        list[Medium]
            List of media with grouped elements
        """
        return list(medium_configs.values())

    def _matches_config(
        self,
        element_layer: str,
        element_color: tuple[int, int, int],
        config_layer: str,
        config_color: tuple[int, int, int] | None,
    ) -> bool:
        """Check if element matches configuration criteria.

        Parameters
        ----------
        element_layer : str
            Layer of the DXF element
        element_color : tuple[int, int, int]
            Color of the DXF element
        config_layer : str
            Required layer from configuration
        config_color : tuple[int, int, int] | None
            Required color from configuration (optional)

        Returns
        -------
        bool
            True if element matches configuration
        """
        element = LayerData(name=element_layer, color=element_color)
        config = LayerData(name=config_layer, color=config_color)
        return element == config
