"""Grouping strategies for organizing DXF elements into media.

This module implements different strategies for grouping pipes, shafts,
and texts into logical media based on layer information or color similarity.
"""

import abc
import json
from pathlib import Path

import numpy as np

from .models import DXFText, GroupingConfig, Medium, Pipe, Shaft


class LayerBasedGrouper(abc.ABC):
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
        self.medium_configs: dict[str, GroupingConfig] = {}

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
                pipe_config = medium_data.get("Leitung", {})
                shaft_config = medium_data.get("Schacht", {})
                text_config = medium_data.get("Text", {})

                # Extract layer names
                pipe_layer = pipe_config.get("Layer", "")
                shaft_layer = shaft_config.get("Layer", "")
                text_layer = text_config.get("Layer", "")

                # Extract optional colors
                pipe_color = tuple(pipe_config["Farbe"]) if "Farbe" in pipe_config else None
                shaft_color = tuple(shaft_config["Farbe"]) if "Farbe" in shaft_config else None
                text_color = tuple(text_config["Farbe"]) if "Farbe" in text_config else None

                self.medium_configs[medium_name] = GroupingConfig(
                    pipe_layer=pipe_layer,
                    shaft_layer=shaft_layer,
                    text_layer=text_layer,
                    pipe_color=pipe_color,
                    shaft_color=shaft_color,
                    text_color=text_color,
                )

        except json.JSONDecodeError as e:
            raise json.JSONDecodeError(
                f"Invalid JSON in configuration file: {e}", e.doc, e.pos
            ) from e

    def group_elements(
        self, pipes: list[Pipe], shafts: list[Shaft], texts: list[DXFText]
    ) -> list[Medium]:
        """Group elements based on layer configuration.

        Parameters
        ----------
        pipes : list[Pipe]
            List of pipes from DXF file
        shafts : list[Shaft]
            List of shafts from DXF file
        texts : list[DXFText]
            List of texts from DXF file

        Returns
        -------
        list[Medium]
            List of media with grouped elements
        """
        if not self.medium_configs:
            raise RuntimeError("Configuration not loaded. Call load_config() first.")

        media = []

        for medium_name, config in self.medium_configs.items():
            # Group pipes by layer (and optionally color)
            medium_pipes = [
                pipe
                for pipe in pipes
                if self._matches_config(
                    pipe.layer, pipe.color, config.pipe_layer, config.pipe_color
                )
            ]

            # Group shafts by layer (and optionally color)
            medium_shafts = [
                shaft
                for shaft in shafts
                if self._matches_config(
                    shaft.layer, shaft.color, config.shaft_layer, config.shaft_color
                )
            ]

            # Group texts by layer (and optionally color)
            medium_texts = [
                text
                for text in texts
                if self._matches_config(
                    text.layer, text.color, config.text_layer, config.text_color
                )
            ]

            # Only create medium if it has at least some elements
            if medium_pipes or medium_shafts or medium_texts:
                media.append(
                    Medium(
                        name=medium_name,
                        pipes=medium_pipes,
                        shafts=medium_shafts,
                        texts=medium_texts,
                    )
                )

        return media

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
        # Layer must match
        if element_layer != config_layer:
            return False

        # If color is specified in config, it must also match
        if config_color is not None and element_color != config_color:
            return False

        return True


class ColorBasedGrouper:
    """Groups DXF elements based on color similarity.

    This grouper analyzes the colors of pipes, shafts, and texts and
    groups elements with similar colors into the same medium.
    """

    def __init__(self, color_tolerance: float = 30.0) -> None:
        """Initialize color-based grouper.

        Parameters
        ----------
        color_tolerance : float, default 30.0
            Maximum color distance for grouping (in RGB space)
        """
        self.color_tolerance = color_tolerance

    def group_elements(
        self, pipes: list[Pipe], shafts: list[Shaft], texts: list[DXFText]
    ) -> list[Medium]:
        """Group elements based on color similarity.

        Elements with similar colors are grouped together. For each color group,
        it's assumed that darker colors represent shafts, medium colors represent
        pipes, and lighter colors represent texts.

        Parameters
        ----------
        pipes : list[Pipe]
            List of pipes from DXF file
        shafts : list[Shaft]
            List of shafts from DXF file
        texts : list[DXFText]
            List of texts from DXF file

        Returns
        -------
        list[Medium]
            List of media with grouped elements
        """
        # Collect all unique colors
        all_colors = set()

        for pipe in pipes:
            all_colors.add(pipe.color)
        for shaft in shafts:
            all_colors.add(shaft.color)
        for text in texts:
            all_colors.add(text.color)

        # Group similar colors
        color_groups = self._group_similar_colors(list(all_colors))

        media = []

        for i, color_group in enumerate(color_groups):
            # Find elements with colors in this group
            group_pipes = [
                pipe
                for pipe in pipes
                if any(
                    self._color_distance(pipe.color, color) <= self.color_tolerance
                    for color in color_group
                )
            ]

            group_shafts = [
                shaft
                for shaft in shafts
                if any(
                    self._color_distance(shaft.color, color) <= self.color_tolerance
                    for color in color_group
                )
            ]

            group_texts = [
                text
                for text in texts
                if any(
                    self._color_distance(text.color, color) <= self.color_tolerance
                    for color in color_group
                )
            ]

            # Only create medium if it has elements
            if group_pipes or group_shafts or group_texts:
                # Generate medium name based on dominant color
                dominant_color = self._get_dominant_color(color_group)
                medium_name = self._color_to_medium_name(dominant_color)

                media.append(
                    Medium(
                        name=f"{medium_name}_{i + 1}",
                        pipes=group_pipes,
                        shafts=group_shafts,
                        texts=group_texts,
                    )
                )

        return media

    def _group_similar_colors(
        self, colors: list[tuple[int, int, int]]
    ) -> list[list[tuple[int, int, int]]]:
        """Group colors that are similar to each other.

        Parameters
        ----------
        colors : list[tuple[int, int, int]]
            List of RGB color tuples

        Returns
        -------
        list[list[tuple[int, int, int]]]
            List of color groups, where each group contains similar colors
        """
        if not colors:
            return []

        groups = []
        remaining_colors = colors.copy()

        while remaining_colors:
            # Start new group with first remaining color
            current_color = remaining_colors.pop(0)
            current_group = [current_color]

            # Find all colors similar to current color
            i = 0
            while i < len(remaining_colors):
                if self._color_distance(current_color, remaining_colors[i]) <= self.color_tolerance:
                    similar_color = remaining_colors.pop(i)
                    current_group.append(similar_color)
                else:
                    i += 1

            groups.append(current_group)

        return groups

    def _color_distance(self, color1: tuple[int, int, int], color2: tuple[int, int, int]) -> float:
        """Calculate Euclidean distance between two RGB colors.

        Parameters
        ----------
        color1 : tuple[int, int, int]
            First RGB color
        color2 : tuple[int, int, int]
            Second RGB color

        Returns
        -------
        float
            Euclidean distance between colors
        """
        r1, g1, b1 = color1
        r2, g2, b2 = color2
        return np.sqrt((r1 - r2) ** 2 + (g1 - g2) ** 2 + (b1 - b2) ** 2)

    def _get_dominant_color(self, color_group: list[tuple[int, int, int]]) -> tuple[int, int, int]:
        """Get the dominant (average) color from a group of colors.

        Parameters
        ----------
        color_group : list[tuple[int, int, int]]
            List of RGB color tuples

        Returns
        -------
        tuple[int, int, int]
            Average RGB color
        """
        if not color_group:
            return (0, 0, 0)

        avg_r = sum(color[0] for color in color_group) // len(color_group)
        avg_g = sum(color[1] for color in color_group) // len(color_group)
        avg_b = sum(color[2] for color in color_group) // len(color_group)

        return (avg_r, avg_g, avg_b)

    def _color_to_medium_name(self, color: tuple[int, int, int]) -> str:
        """Convert RGB color to a descriptive medium name.

        Parameters
        ----------
        color : tuple[int, int, int]
            RGB color tuple

        Returns
        -------
        str
            Descriptive name for the color (e.g., "Blau", "Rot", "Grün")
        """
        r, g, b = color

        # Simple color name mapping based on dominant RGB component
        if r > g and r > b:
            if r > 150:
                return "Rot"
            else:
                return "Dunkelrot"
        elif g > r and g > b:
            if g > 150:
                return "Grün"
            else:
                return "Dunkelgrün"
        elif b > r and b > g:
            if b > 150:
                return "Blau"
            else:
                return "Dunkelblau"
        elif r > 100 and g > 100 and b < 50:
            return "Gelb"
        elif r > 100 and g < 50 and b > 100:
            return "Magenta"
        elif r < 50 and g > 100 and b > 100:
            return "Cyan"
        elif r < 50 and g < 50 and b < 50:
            return "Schwarz"
        elif r > 200 and g > 200 and b > 200:
            return "Weiß"
        else:
            return "Grau"
