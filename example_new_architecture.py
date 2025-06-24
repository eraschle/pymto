#!/usr/bin/env python3
"""Example demonstrating the new DXF processing architecture.

This script shows how to use the clean separation of concerns:
- DXFReader for file I/O
- DXFEntityExtractor for entity extraction
- ObjectDataFactory for object creation
- DXFProcessor as orchestrator
"""

import sys
from pathlib import Path

import click

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from dxfto.io import DXFProcessor
from dxfto.models import AssignmentConfig, LayerData, Medium


def demonstrate_new_architecture():
    """Demonstrate the new clean architecture."""

    click.echo("🏗️  DXF Processing with Clean Architecture")
    click.echo("=" * 50)

    # Path to test DXF file
    dxf_path = Path("test_entities.dxf")
    if not dxf_path.exists():
        click.echo(f"❌ Test DXF file not found: {dxf_path}")
        click.echo("   Run test_dxf_factory.py first to create it.")
        return

    click.echo(f"📁 Processing DXF file: {dxf_path}")

    # 1. Initialize processor (orchestrator)
    processor = DXFProcessor(dxf_path)
    click.echo("✅ DXFProcessor initialized")

    # 2. Load file (automatically initializes all components)
    processor.load_file()
    click.echo("✅ DXF file loaded and components initialized")

    # 3. Get statistics
    stats = processor.get_statistics()
    click.echo(f"📊 Statistics:")
    click.echo(f"   - Total entities: {stats['total_entities']}")
    click.echo(f"   - Available layers: {stats['available_layers']}")
    click.echo(f"   - Layer names: {stats['layer_names']}")

    # 4. Create medium configuration
    geometry_layers = [LayerData(name="0", color=(255, 0, 0))]
    text_layers = [LayerData(name="TEXT", color=(0, 0, 0))]

    elements_config = AssignmentConfig(geometry=geometry_layers, text=text_layers)
    lines_config = AssignmentConfig(geometry=geometry_layers, text=text_layers)

    test_medium = Medium(name="Test Medium", elements=elements_config, lines=lines_config)

    mediums = {"test": test_medium}
    click.echo("✅ Medium configuration created")

    # 5. Process mediums (complete pipeline)
    processor.process_mediums(mediums)
    click.echo("✅ Mediums processed")

    # 6. Display results
    click.echo(f"\n📋 Results for medium '{test_medium.name}':")
    click.echo(f"   - Elements: {len(test_medium.element_data.elements)}")
    click.echo(f"   - Lines: {len(test_medium.line_data.elements)}")
    click.echo(f"   - Texts: {len(test_medium.element_data.texts)}")

    # 7. Show detailed object information
    click.echo(f"\n🔍 Element Details:")
    for i, element in enumerate(test_medium.element_data.elements[:5], 1):  # Show first 5
        dim = element.dimensions
        if hasattr(dim, "diameter"):
            click.echo(f"   {i}. Round element - Ø{dim.diameter:.1f}mm on layer '{element.layer}'")
        else:
            click.echo(f"   {i}. Rectangular element - {dim.length:.1f}x{dim.width:.1f}mm on layer '{element.layer}'")

    if len(test_medium.element_data.elements) > 5:
        click.echo(f"   ... and {len(test_medium.element_data.elements) - 5} more elements")

    click.echo(f"\n🔗 Line Details:")
    for i, line in enumerate(test_medium.line_data.elements[:3], 1):  # Show first 3
        dim = line.dimensions
        click.echo(f"   {i}. Line - Ø{dim.diameter:.1f}mm, {len(line.points)} points on layer '{line.layer}'")

    if len(test_medium.line_data.elements) > 3:
        click.echo(f"   ... and {len(test_medium.line_data.elements) - 3} more lines")


def compare_architectures():
    """Compare old vs new architecture usage."""

    click.echo("\n🔄 Architecture Comparison")
    click.echo("=" * 30)

    click.echo("📜 OLD Architecture (monolithic):")
    click.echo("""
    from dxfto.io import LegacyDXFReader

    reader = LegacyDXFReader(dxf_path)
    reader.load_file()
    reader.extract_data(mediums)  # Does everything internally
    """)

    click.echo("🆕 NEW Architecture (clean separation):")
    click.echo("""
    from dxfto.io import DXFProcessor

    processor = DXFProcessor(dxf_path)  # Orchestrator
    processor.load_file()               # File I/O
    processor.process_mediums(mediums)  # Entity extraction + Object creation
    """)

    click.echo("✨ Benefits of new architecture:")
    click.echo("   • Single Responsibility Principle")
    click.echo("   • Better testability")
    click.echo("   • Easier to extend")
    click.echo("   • Factory pattern for object creation")
    click.echo("   • Clear separation of concerns")


def show_internal_components():
    """Show how to use individual components."""

    click.echo("\n🔧 Individual Components")
    click.echo("=" * 25)

    click.echo("If you need fine-grained control:")
    click.echo("""
    from dxfto.io import DXFReader, DXFEntityExtractor
    from dxfto.process import ObjectDataFactory

    # 1. File I/O only
    reader = DXFReader(dxf_path)
    reader.load_file()

    # 2. Entity extraction only
    extractor = DXFEntityExtractor(reader)
    entities = extractor.extract_entities(config)

    # 3. Object creation only
    factory = ObjectDataFactory(reader.document)
    objects = [factory.create_from_entity(e) for e in entities['elements']]
    """)


if __name__ == "__main__":
    demonstrate_new_architecture()
    compare_architectures()
    show_internal_components()

    click.echo("\n🎉 Demonstration complete!")
    click.echo("   The new architecture provides clean separation of concerns")
    click.echo("   while maintaining the same simple API for users.")
