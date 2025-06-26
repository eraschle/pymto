#!/usr/bin/env python3
"""Test script for the ObjectData factory with test DXF file."""

import logging
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

import ezdxf.filemanagement as ezdxf

from dxfto.models import ObjectType
from dxfto.process.objectdata_factory import ObjectDataFactory

log = logging.getLogger(__name__)


def test_factory():
    """Test the ObjectData factory with the test DXF file."""

    # Load test DXF file
    dxf_path = Path(__file__).parent / "test_entities.dxf"
    if not dxf_path.exists():
        log.error(f"Test DXF file not found: {dxf_path}")
        return

    log.info(f"Loading DXF file: {dxf_path}")
    doc = ezdxf.readfile(str(dxf_path))

    # Create factory
    factory = ObjectDataFactory(doc)

    # Process all entities in modelspace
    elements = []
    lines = []

    log.info("\n=== Processing Entities ===")
    for entity in doc.modelspace():
        entity_type = entity.dxftype()
        layer = getattr(entity.dxf, "layer", "0")

        log.info(f"\nEntity: {entity_type} on layer '{layer}'")

        # Classify entity
        is_element = factory.should_process_as_element(entity)
        log.info(f"  Classification: {'Element' if is_element else 'Line'}")

        # Create ObjectData
        object_type = ObjectType.SHAFT if is_element else ObjectType.PIPE_WASTEWATER
        obj_data = factory.create_from_entity(
            medium="test",
            entity=entity,
            object_type=object_type,
        )
        if obj_data is None:
            log.error("  Failed to create ObjectData")
            continue

        # Display results
        log.info(f"  Dimensions: {obj_data.dimensions}")
        if obj_data.positions:
            log.info(f"  Position: {obj_data.positions[0]}")
        if obj_data.points:
            log.info(f"  Points: {len(obj_data.points)} points")

        # Add to appropriate list
        if is_element:
            elements.append(obj_data)
        else:
            lines.append(obj_data)

    log.info("\n=== Summary ===")
    log.info(f"Elements created: {len(elements)}")
    log.info(f"Lines created: {len(lines)}")

    # Display element details
    log.info("\n=== Elements Detail ===")
    for i, element in enumerate(elements, 1):
        dim = element.dimensions
        if hasattr(dim, "diameter"):
            log.info(f"  {i}. Round element - Diameter: {dim.diameter:.1f}mm")
        else:
            log.info(f"  {i}. Rectangular element - {dim.length:.1f}x{dim.width:.1f}mm")

    log.info("\n=== Lines Detail ===")
    for i, line in enumerate(lines, 1):
        dim = line.dimensions
        log.info(f"  {i}. Line - Diameter: {dim.diameter:.1f}mm, Points: {len(line.points)}")


if __name__ == "__main__":
    test_factory()
