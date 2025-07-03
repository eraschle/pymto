"""Pytest configuration and fixtures for pymto tests."""

import sys
from pathlib import Path

import pytest

# Add src directory to Python path
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture(scope="session")
def project_root():
    """Return the project root directory."""
    return Path(__file__).parent.parent


@pytest.fixture(scope="session")
def src_dir(project_root):
    """Return the src directory."""
    return project_root / "src"


@pytest.fixture(scope="session")
def test_dxf_file(project_root):
    """Return path to the test DXF file."""
    return project_root / "test_entities.dxf"


@pytest.fixture
def sample_points():
    """Return sample Point3D objects for testing."""
    from pymto.models import Point3D

    return [
        Point3D(east=0.0, north=0.0, altitude=0.0),
        Point3D(east=10.0, north=0.0, altitude=0.0),
        Point3D(east=10.0, north=5.0, altitude=0.0),
        Point3D(east=0.0, north=5.0, altitude=0.0),
    ]


@pytest.fixture
def rectangular_points():
    """Return points forming a perfect rectangle."""
    from pymto.models import Point3D

    return [
        Point3D(east=0.0, north=0.0, altitude=0.0),
        Point3D(east=10.0, north=0.0, altitude=0.0),
        Point3D(east=10.0, north=5.0, altitude=0.0),
        Point3D(east=0.0, north=5.0, altitude=0.0),
    ]


@pytest.fixture
def circular_points():
    """Return points forming a regular octagon (near-circular)."""
    import math

    from pymto.models import Point3D

    center = (0.0, 0.0)
    radius = 5.0
    points = []

    for i in range(8):
        angle = i * 2 * math.pi / 8
        x = center[0] + radius * math.cos(angle)
        y = center[1] + radius * math.sin(angle)
        points.append(Point3D(east=x, north=y, altitude=0.0))

    return points


@pytest.fixture
def irregular_points():
    """Return points forming an irregular polygon."""
    from pymto.models import Point3D

    return [
        Point3D(east=0.0, north=0.0, altitude=0.0),
        Point3D(east=8.0, north=2.0, altitude=0.0),
        Point3D(east=10.0, north=8.0, altitude=0.0),
        Point3D(east=3.0, north=10.0, altitude=0.0),
        Point3D(east=-2.0, north=5.0, altitude=0.0),
    ]
