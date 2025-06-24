#!/usr/bin/env python3
"""Create test DXF file with various entity types for testing the ObjectData factory."""

import logging
from pathlib import Path

import ezdxf.filemanagement as ezdxf

log = logging.getLogger(__name__)


def create_test_dxf():
    """Create a comprehensive test DXF file with various entity types."""

    # Create new DXF document
    doc = ezdxf.new("R2010")
    msp = doc.modelspace()

    # 1. Simple Circle (round shaft)
    msp.add_circle((10, 10), radius=2.5)  # 5m diameter

    # 2. Large Circle (main shaft)
    msp.add_circle((20, 10), radius=4.0)  # 8m diameter

    # 3. Rectangular polyline (4 corners)
    rect_points = [(30, 5), (35, 5), (35, 15), (30, 15), (30, 5)]
    msp.add_lwpolyline(rect_points, close=True)

    # 4. Rectangular polyline with diagonal cross
    rect_points_2 = [(45, 5), (50, 5), (50, 15), (45, 15), (45, 5)]
    msp.add_lwpolyline(rect_points_2, close=True)
    # Add diagonal cross lines
    msp.add_line((45, 5), (50, 15))
    msp.add_line((45, 15), (50, 5))

    # 5. Complex polygon (hexagon)
    import math

    hex_center = (60, 10)
    hex_radius = 3
    hex_points = []
    for i in range(6):
        angle = i * math.pi / 3
        x = hex_center[0] + hex_radius * math.cos(angle)
        y = hex_center[1] + hex_radius * math.sin(angle)
        hex_points.append((x, y))
    hex_points.append(hex_points[0])  # Close polygon
    msp.add_lwpolyline(hex_points, close=True)

    # 6. Octagon (8 corners)
    oct_center = (75, 10)
    oct_radius = 2.5
    oct_points = []
    for i in range(8):
        angle = i * math.pi / 4
        x = oct_center[0] + oct_radius * math.cos(angle)
        y = oct_center[1] + oct_radius * math.sin(angle)
        oct_points.append((x, y))
    oct_points.append(oct_points[0])  # Close polygon
    msp.add_lwpolyline(oct_points, close=True)

    # 7. Create block with circle (round shaft block)
    round_block = doc.blocks.new(name="ROUND_SHAFT")
    round_block.add_circle((0, 0), radius=1.5)  # 3m diameter
    msp.add_blockref("ROUND_SHAFT", (10, 25))

    # 8. Create block with two circles (shaft with inner circle)
    double_circle_block = doc.blocks.new(name="DOUBLE_CIRCLE_SHAFT")
    double_circle_block.add_circle((0, 0), radius=2.0)  # Outer circle 4m
    double_circle_block.add_circle((0, 0), radius=1.0)  # Inner circle 2m
    msp.add_blockref("DOUBLE_CIRCLE_SHAFT", (20, 25))

    # 9. Create block with rectangle
    rect_block = doc.blocks.new(name="RECT_SHAFT")
    rect_block.add_lwpolyline([(-2, -1.5), (2, -1.5), (2, 1.5), (-2, 1.5), (-2, -1.5)], close=True)
    msp.add_blockref("RECT_SHAFT", (30, 25))

    # 10. Create block with rectangle and diagonal cross
    rect_cross_block = doc.blocks.new(name="RECT_CROSS_SHAFT")
    rect_cross_block.add_lwpolyline([(-2.5, -2), (2.5, -2), (2.5, 2), (-2.5, 2), (-2.5, -2)], close=True)
    rect_cross_block.add_line((-2.5, -2), (2.5, 2))  # Diagonal 1
    rect_cross_block.add_line((-2.5, 2), (2.5, -2))  # Diagonal 2
    msp.add_blockref("RECT_CROSS_SHAFT", (45, 25))

    # 11. Line segments (pipes)
    msp.add_line((5, 30), (15, 30))
    msp.add_line((15, 30), (25, 35))
    msp.add_line((25, 35), (35, 30))

    # 12. Polyline with 3 points (pipe segment)
    pipe_points = [(40, 30), (45, 32), (50, 30)]
    msp.add_lwpolyline(pipe_points, close=False)

    # 13. Text elements
    msp.add_text("SHAFT_1", dxfattribs={"layer": "TEXT", "insert": (10, 5)})
    msp.add_text("SHAFT_2", dxfattribs={"layer": "TEXT", "insert": (20, 5)})
    msp.add_text("RECT_1", dxfattribs={"layer": "TEXT", "insert": (32, 2)})
    msp.add_text("HEX_1", dxfattribs={"layer": "TEXT", "insert": (60, 5)})

    # Save DXF file
    output_path = Path("/home/elyo/workspace/work/dxfto/test_entities.dxf")
    doc.saveas(output_path)
    log.info(f"Test DXF file created: {output_path}")

    return output_path


if __name__ == "__main__":
    create_test_dxf()
