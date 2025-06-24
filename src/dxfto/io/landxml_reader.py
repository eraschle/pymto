"""LandXML file reader for extracting Z coordinates from DGM data.

This module handles reading LandXML files using the lxml library to
extract elevation data that will be used to set Z coordinates for
DXF points based on spatial interpolation.
"""

from pathlib import Path

import numpy as np
from lxml import etree
from scipy.spatial import cKDTree

from ..models import Point3D


class LandXMLReader:
    """Reader for LandXML files to extract elevation data (DGM).

    This class processes LandXML files and extracts elevation points
    that are used to determine Z coordinates for DXF elements through
    spatial interpolation.
    """

    def __init__(self, landxml_path: Path) -> None:
        """Initialize LandXML reader with file path.

        Parameters
        ----------
        landxml_path : Path
            Path to the LandXML file to process
        """
        self.landxml_path = landxml_path
        self.elevation_points: list[Point3D] = []
        self._kdtree: cKDTree | None = None

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
            tree = etree.parse(str(self.landxml_path))
            root = tree.getroot()

            # Extract elevation points from LandXML
            self.elevation_points = self._extract_elevation_points(root)

            # Build KDTree for efficient spatial queries
            if self.elevation_points:
                xy_points = np.array([(p.x, p.y) for p in self.elevation_points])
                self._kdtree = cKDTree(xy_points)

        except etree.XMLSyntaxError as e:
            raise etree.XMLSyntaxError(f"Cannot parse LandXML file {self.landxml_path}: {e}") from e

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
            return 0.0

        # Find nearest elevation points
        query_point = np.array([x, y])
        distances, indices = self._kdtree.query(query_point, k=min(4, len(self.elevation_points)))

        if isinstance(indices, int):
            # Single nearest point
            return self.elevation_points[indices].z

        # Inverse distance weighting interpolation
        weights = 1.0 / (distances + 1e-10)  # Add small epsilon to avoid division by zero
        total_weight = np.sum(weights)

        interpolated_z = (
            sum(weights[i] * self.elevation_points[idx].z for i, idx in enumerate(indices))
            / total_weight
        )

        return float(interpolated_z)

    def update_points_elevation(self, points: list[Point3D]) -> list[Point3D]:
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
            z_elevation = self.get_elevation(point.x, point.y)
            updated_point = Point3D(x=point.x, y=point.y, z=z_elevation)
            updated_points.append(updated_point)

        return updated_points

    def _extract_elevation_points(self, root: etree._Element) -> list[Point3D]:
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
        elevation_points = []

        # Find namespace
        namespace = root.nsmap.get(None, "")
        ns = {"": namespace} if namespace else {}

        # Look for surface points in various LandXML structures
        # This is a simplified implementation - real LandXML files can have
        # different structures for elevation data

        # Try to find surface definition points
        surface_points = root.xpath(".//Definition/Pnts/P", namespaces=ns)

        for point_elem in surface_points:
            try:
                # Parse point coordinates - format is usually "x y z" or "x,y,z"
                coords_text = point_elem.text.strip()

                # Handle different coordinate separators
                if "," in coords_text:
                    coords = coords_text.split(",")
                else:
                    coords = coords_text.split()

                if len(coords) >= 3:
                    x = float(coords[0])
                    y = float(coords[1])
                    z = float(coords[2])
                    elevation_points.append(Point3D(x=x, y=y, z=z))

            except (ValueError, IndexError):
                continue

        # Alternative: look for TIN (Triangulated Irregular Network) faces
        if not elevation_points:
            tin_faces = root.xpath(".//Faces/F", namespaces=ns)
            point_refs = root.xpath(".//Pnts/P", namespaces=ns)

            # Create lookup for point references
            point_lookup = {}
            for i, point_elem in enumerate(point_refs):
                try:
                    coords_text = point_elem.text.strip()
                    if "," in coords_text:
                        coords = coords_text.split(",")
                    else:
                        coords = coords_text.split()

                    if len(coords) >= 3:
                        x = float(coords[0])
                        y = float(coords[1])
                        z = float(coords[2])
                        point_lookup[i + 1] = Point3D(x=x, y=y, z=z)

                except (ValueError, IndexError):
                    continue

            # Extract unique points from TIN faces
            unique_points = set()
            for face_elem in tin_faces:
                try:
                    # Face format is usually "p1 p2 p3" referencing point indices
                    face_text = face_elem.text.strip()
                    point_indices = [int(idx) for idx in face_text.split()]

                    for idx in point_indices:
                        if idx in point_lookup:
                            point = point_lookup[idx]
                            unique_points.add((point.x, point.y, point.z))

                except (ValueError, IndexError):
                    continue

            elevation_points = [Point3D(x=x, y=y, z=z) for x, y, z in unique_points]

        return elevation_points
