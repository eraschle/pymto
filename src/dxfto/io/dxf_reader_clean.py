"""Clean DXF file reader focused only on file I/O and entity querying.

This module contains a refactored DXFReader that follows the Single
Responsibility Principle by handling only DXF file operations.
"""

import logging
from pathlib import Path

import ezdxf.filemanagement as ezdxf
from ezdxf.document import Drawing
from ezdxf.lldxf.const import DXFError
from ezdxf.query import EntityQuery

from ..models import LayerData

log = logging.getLogger(__name__)


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

    @property
    def document(self) -> Drawing | None:
        """Get the loaded DXF document.

        Returns
        -------
        Drawing | None
            Loaded DXF document or None if not loaded
        """
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

    def get_entity_count(self, layers: list[LayerData] | None = None) -> int:
        """Get count of entities in specified layers.

        Parameters
        ----------
        layers : list[LayerData] | None
            Layers to count entities from. If None, counts all entities.

        Returns
        -------
        int
            Number of entities found

        Raises
        ------
        RuntimeError
            If DXF file is not loaded
        """
        if self._doc is None:
            raise RuntimeError("DXF file not loaded. Call load_file() first.")

        if layers is None:
            return len(self._doc.modelspace())
        else:
            return len(self.query_entities(layers))
