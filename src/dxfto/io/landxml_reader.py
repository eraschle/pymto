"""LandXML file reader for extracting Z coordinates from DGM data.

This module handles reading LandXML files using the lxml library to
extract elevation data that will be used to set Z coordinates for
DXF points based on spatial interpolation.
"""

import xml.etree.ElementTree as ET
from collections.abc import Iterable
from pathlib import Path

import numpy as np
from scipy.spatial import KDTree

from ..models import AssingmentData, MediumConfig, Point3D


class LandXMLReader:
    """Reader for LandXML files to extract elevation data (DGM).

    This class processes LandXML files and extracts elevation points
    that are used to determine Z coordinates for DXF elements through
    spatial interpolation.
    """

    LAND_XML_NS = {"xmlns": "http://www.landxml.org/schema/LandXML-1.2"}

    def __init__(self, landxml_path: Path) -> None:
        """Initialize LandXML reader with file path.

        Parameters
        ----------
        landxml_path : Path
            Path to the LandXML file to process
        """
        self.landxml_path = landxml_path
        self.elevation_points: list[Point3D] = []
        self._kdtree: KDTree | None = None

    def load_file(self) -> None:
        """Load the LandXML file and extract elevation points.

        Raises
        ------
        FileNotFoundError
            If LandXML file does not exist
        etree.XMLSyntaxError
            If LandXML file cannot be parsed
        """
        if not self.landxml_path.exists():
            raise FileNotFoundError(f"LandXML file not found: {self.landxml_path}")

        try:
            tree = ET.parse(str(self.landxml_path))
            root = tree.getroot()

            # Extract elevation points from LandXML
            self.elevation_points = self._extract_elevation_points(root)

            # Build KDTree for efficient spatial queries
            if self.elevation_points:
                xy_points = np.array([(p.east, p.north) for p in self.elevation_points])
                self._kdtree = KDTree(xy_points)

        except Exception as e:
            raise Exception(f"Cannot parse LandXML file {self.landxml_path}: {e}") from e

    def get_elevation(self, x: float, y: float) -> float:
        """Get elevation (Z coordinate) for given X, Y coordinates.

        Uses spatial interpolation to determine elevation at the given
        coordinates based on nearby elevation points.

        Parameters
        ----------
        x : float
            X coordinate
        y : float
            Y coordinate

        Returns
        -------
        float
            Interpolated Z coordinate (elevation)
        """
        if not self.elevation_points or self._kdtree is None:
            raise RuntimeError("Elevation points not loaded or KDTree not initialized")

        # Find nearest elevation points
        query_point = np.array([x, y])
        distances, indices = self._kdtree.query(query_point, k=min(4, len(self.elevation_points)))

        # Handle both scalar and array cases for distances and indices
        if np.isscalar(distances):
            # Single nearest point case
            return self.elevation_points[int(indices)].altitude

        # Multiple points - inverse distance weighting interpolation
        weights = 1.0 / (distances + 1e-10)  # Add small epsilon to avoid division by zero
        total_weight = np.sum(weights)

        interpolated_z = (
            sum(weights[i] * self.elevation_points[int(idx)].altitude for i, idx in enumerate(indices)) / total_weight
        )
        return float(interpolated_z)

    def update_elements(self, assigment: AssingmentData) -> None:
        # Texts are assigned to elemtents and onbly the elements data are exported, which
        # means that texts are not updated here.
        for elements, config in assigment.assigned:
            for element in elements:
                if element.points:
                    element.points = self._update_elevation(element.points, config)
                if element.positions:
                    positions = self._update_elevation(element.positions, config)
                    element.positions = tuple(positions)

    def _update_elevation(self, points: Iterable[Point3D], config: MediumConfig) -> list[Point3D]:
        """Update Z coordinates for a list of points using elevation data.

        Parameters
        ----------
        points : list[Point3D]
            List of points to update with elevation data

        Returns
        -------
        list[Point3D]
            List of points with updated Z coordinates
        """
        updated_points = []

        for point in points:
            z_elevation = self.get_elevation(point.east, point.north)
            z_elevation = z_elevation - config.elevation_offset
            updated_point = Point3D(east=point.east, north=point.north, altitude=z_elevation)
            updated_points.append(updated_point)

        return updated_points

    def _extract_elevation_points(self, root: ET.Element) -> list[Point3D]:
        """Extract elevation points from LandXML root element.

        Parameters
        ----------
        root : etree._Element
            Root element of the LandXML document

        Returns
        -------
        list[Point3D]
            List of elevation points extracted from LandXML
        """
        elevation_points = self._extract_surface_points(root)
        if not elevation_points:
            elevation_points = self._extract_tin_faces(root)
        return elevation_points

    def _create_3d_point(self, coords_text: str) -> Point3D | None:
        """Create a Point3D object from coordinate text.

        Parameters
        ----------
        coords_text : str
            Text containing coordinates in the format "x y z" or "x,y,z"
        Returns
        -------
        Point3D | None
            Point3D object if coordinates are valid, None otherwise
        """
        coords_text = coords_text.strip()
        if "," in coords_text:
            coords = coords_text.split(",")
        else:
            coords = coords_text.split()

        if len(coords) < 3:
            return None
        return Point3D(
            north=float(coords[0]),
            east=float(coords[1]),
            altitude=float(coords[2]),
        )

    def _extract_surface_points(self, root: ET.Element) -> list[Point3D]:
        """Extract surface points from LandXML root element.

        Parameters
        ----------
        root : ET.Element
            Root element of the LandXML document
        Returns
        -------
        list[Point3D]
            List of surface points extracted from LandXML
        """
        surface_points = root.findall(".//xmlns:Pnts/xmlns:P", namespaces=self.LAND_XML_NS)

        elevation_points = []
        for point_elem in surface_points:
            if not point_elem.text:
                continue
            try:
                # Parse point coordinates - format is usually "x y z" or "x,y,z"
                point = self._create_3d_point(point_elem.text)
                if point is None:
                    continue
                elevation_points.append(point)
            except (ValueError, IndexError):
                continue
        return elevation_points

    def _extract_surface_point_lookup(self, root: ET.Element) -> dict[int, Point3D]:
        """Extract surface points and create a lookup dictionary.

        Parameters
        ----------
        root : ET.Element
            Root element of the LandXML document
        Returns
        -------
        list[Point3D]
            List of surface points extracted from LandXML with a lookup dictionary
        """
        point_lookup = {}
        point_refs = root.findall(".//xmlns:Pnts/xmlns:P", namespaces=self.LAND_XML_NS)
        for idx, point_elem in enumerate(point_refs):
            if not point_elem.text:
                continue
            try:
                point = self._create_3d_point(point_elem.text.strip())
                if point is None:
                    continue
                point_lookup[idx + 1] = point
            except (ValueError, IndexError):
                continue
        return point_lookup

    def _extract_tin_faces(self, root: ET.Element) -> list[Point3D]:
        """Extract TIN faces from LandXML root element.

        Parameters
        ----------
        root : ET.Element
            Root element of the LandXML document

        Returns
        -------
        list[Point3D]
            List of TIN faces extracted from LandXML
        """
        # Extract unique points from TIN faces
        unique_points = set()

        point_lookup = self._extract_surface_point_lookup(root)
        tin_faces = root.findall(".//xmlns:Faces/xmlns:F", namespaces=self.LAND_XML_NS)
        for face_elem in tin_faces:
            if not face_elem.text:
                continue
            try:
                # Face format is usually "p1 p2 p3" referencing point indices
                face_text = face_elem.text.strip()
                point_indices = [int(idx) for idx in face_text.split()]

                for idx in point_indices:
                    if idx not in point_lookup:
                        continue
                    point = point_lookup[idx]
                    unique_points.add((point.east, point.north, point.altitude))

            except (ValueError, IndexError):
                continue

        return [Point3D(east=east, north=north, altitude=altitude) for east, north, altitude in unique_points]
