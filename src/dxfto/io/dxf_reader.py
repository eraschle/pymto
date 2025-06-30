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

    def query_entities(self, layers: list[LayerData]) -> EntityQuery:
        """Query entities from specified layers.

        Parameters
        ----------
        layers : list[LayerData]
            List of layer configurations to query

        Returns
        -------
        EntityQuery
            Query result containing entities from specified layers

        Raises
        ------
        RuntimeError
            If DXF file is not loaded
        """
        if self._doc is None:
            raise RuntimeError("DXF file not loaded. Call load_file() first.")

        layer_names = [layer.name for layer in layers]
        if not layer_names:
            log.warning("No layers specified for entity query")
            return self._doc.modelspace().query('*[layer=="__NONEXISTENT__"]')  # Empty result

        query = '*[layer=="' + '" | layer=="'.join(layer_names) + '"]'
        log.debug(f"Querying entities from layers: {layer_names}")
        return self._doc.modelspace().query(query)

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
            """Check if entity color matches the layer color."""
            if layer.color is None:
                return True
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
            log.warning(
                f"No able to find color for {entity} in layer {layer.name} with color {layer.color}"
            )
            return False

        query = f'*[layer=="{layer.name}"]'
        log.debug(f"Querying entities from layer: {layer.name} with color {layer.color}")
        return self._doc.modelspace().query(query).filter(color_filter)

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
