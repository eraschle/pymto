"""Clean DXF file reader focused only on file I/O and entity querying.

This module contains a refactored DXFReader that follows the Single
Responsibility Principle by handling only DXF file operations.
"""

import logging
from pathlib import Path

import ezdxf.filemanagement as ezdxf
from ezdxf.colors import RGB
from ezdxf.document import Drawing
from ezdxf.entities.dxfentity import DXFEntity
from ezdxf.entities.insert import Insert
from ezdxf.enums import ACI
from ezdxf.lldxf.const import DXFError
from ezdxf.query import EntityQuery

from ..models import LayerData

log = logging.getLogger(__name__)


LAYER_TRANSLATION = {
    "VON BLOCK": "BY BLOCK",
    "VON LAYER": "BY LAYER",
    "BLAU": "BLUE",
    "ROT": "RED",
    "GRÜN": "GREEN",
    "GELB": "YELLOW",
    "CYAN": "CYAN",
    "MAGENTA": "MAGENTA",
    "WEISS": "WHITE",
    "SCHWARZ": "BLACK",
    "GRAU": "GRAY",
    "HELLGRAU": "LIGHTGRAY",
}


def get_color_filter(entity: DXFEntity, layer: LayerData) -> bool:
    """Check if entity color matches the layer color."""
    if layer.color is None:
        return False
    if isinstance(layer.color, (tuple | list)):
        entity_color = getattr(entity, "rgb", RGB(0, 0, 0))
        layer_color = RGB(*layer.color)
        return entity_color == layer_color
    elif isinstance(layer.color, int):
        return entity.dxf.color == layer.color
    elif isinstance(layer.color, str):
        layer_color = layer.color.upper()
        layer_color = LAYER_TRANSLATION.get(layer_color, layer_color)
        for aci_color in ACI:
            if aci_color.name != layer_color:
                continue
            return True
    log.warning(f"No able to find color for {entity} in layer {layer.name} with color {layer.color}")
    return False


def _block_startswith_filter(entity: DXFEntity, value: str) -> bool:
    """Get the block query function based on layer configuration."""
    if not isinstance(entity, Insert):
        return False
    block_name = entity.dxf.name
    startswith = block_name.startswith(value)
    if not startswith:
        log.debug(f"Block name '{block_name}' does not start with '{value}'")
    return startswith


def _block_endswith_filter(entity: DXFEntity, endswith: str) -> bool:
    if not isinstance(entity, Insert):
        return False
    block_name = entity.dxf.name
    return block_name.endswith(endswith)


def get_where_string(layer: LayerData) -> str:
    """Get where clauses for querying entities based on layer configuration."""
    clauses = []
    if layer.name is not None:
        clauses.append(f'layer=="{layer.name}"')
    if layer.is_block_name_query:
        clauses.append(f'name=="{layer.block}"')
    return " & ".join(clauses)


def get_entity_query(layer: LayerData) -> str:
    """Get where clauses for querying entities based on layer configuration."""
    type_query = "*"
    if layer.is_block_query:
        type_query = "INSERT"
    where_cause = get_where_string(layer)
    if len(where_cause) == 0:
        return ""
    return f"{type_query}[{where_cause}]"


class DXFReader:
    """Clean DXF file reader focused on file I/O and entity querying.

    This class handles only DXF file loading and entity querying,
    delegating object creation to other specialized classes.
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
            log.info(f"Successfully loaded DXF file: {self.dxf_path}")
        except DXFError as e:
            raise DXFError(f"Cannot read DXF file {self.dxf_path}: {e}") from e

    def query_layer(self, layer: LayerData) -> EntityQuery:
        """Query entities from specified layers.

        Parameters
        ----------
        layer : LayerData
            Layer configuration to query

        Returns
        -------
        EntityQuery
            Query result containing entities from the specified layer

        Raises
        ------
        RuntimeError
            If DXF file is not loaded
        """
        if self._doc is None:
            raise RuntimeError("DXF file not loaded. Call load_file() first.")

        def color_filter(entity: DXFEntity) -> bool:
            """Filter function to check entity color against layer color."""
            return get_color_filter(entity, layer)

        def block_filter(entity: DXFEntity) -> bool:
            """Filter function to query entities by block name
            startswith or endswith with a given block name."""
            if not isinstance(entity, Insert) or layer.is_block_name_query:
                return False
            if layer.is_block_startswith_query and layer.block:
                query_value = layer.block.rstrip("*")
                return _block_startswith_filter(entity, query_value)
            if layer.is_block_endswith_query and layer.block:
                query_value = layer.block.lstrip("*")
                return _block_endswith_filter(entity, query_value)
            return False

        entity_query = EntityQuery(self._doc.modelspace())

        query_string = get_entity_query(layer)
        if len(query_string) > 0:
            entity_query = entity_query.query(query_string)
        if layer.color is not None:
            log.debug(f"Applying color filter for layer: {layer.name} with color {layer.color}")
            entity_query = entity_query.filter(color_filter)
        if layer.is_block_query:
            entity_query = entity_query.filter(block_filter)
        return entity_query

    @property
    def document(self) -> Drawing:
        """Get the loaded DXF document.

        Returns
        -------
        Drawing | None
            Loaded DXF document or None if not loaded
        Raises
        ------
        RuntimeError
            If DXF file is not loaded
        """
        if self._doc is None:
            raise RuntimeError("DXF file not loaded. Call load_file() first.")
        return self._doc

    def is_loaded(self) -> bool:
        """Check if DXF file is loaded.

        Returns
        -------
        bool
            True if DXF file is loaded, False otherwise
        """
        return self._doc is not None

    def get_layer_names(self) -> list[str]:
        """Get all layer names from the DXF file.

        Returns
        -------
        list[str]
            List of all layer names in the DXF file

        Raises
        ------
        RuntimeError
            If DXF file is not loaded
        """
        if self._doc is None:
            raise RuntimeError("DXF file not loaded. Call load_file() first.")

        return [layer.dxf.name for layer in self._doc.layers]
