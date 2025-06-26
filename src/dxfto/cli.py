"""Command-line interface for DXF processing and Revit export.

This module provides the main CLI interface using Click for processing
DXF files with optional LandXML elevation data and exporting to JSON
format suitable for Revit modeling.
"""

from pathlib import Path

import click

from dxfto.config import ConfigurationHandler

from .assigners import SpatialTextAssigner, ZoneBasedTextAssigner
from .io import DXFReader, JsonExporter, LandXMLReader
from .process.dimension import DimensionUpdater
from .processor import DXFProcessor


@click.command()
@click.argument(
    "dxf_file",
    type=click.Path(exists=True, path_type=Path),
)
@click.argument(
    "config",
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--landxml",
    "-l",
    type=click.Path(exists=True, path_type=Path),
    help="LandXML file for elevation data (DGM)",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output JSON file path",
)
@click.option(
    "--grouping",
    type=click.Choice(["layer", "color"], case_sensitive=False),
    default="color",
    help="Grouping strategy: layer or color",
)
@click.option(
    "--text-assignment",
    type=click.Choice(["spatial", "zone"], case_sensitive=False),
    default="spatial",
    help="Text assignment strategy: spatial or zone",
)
@click.option(
    "--max-text-distance",
    type=float,
    default=1.0,
    help="Maximum distance for text-to-pipe assignment",
)
@click.option(
    "--color-tolerance",
    type=float,
    default=30.0,
    help="Color tolerance for color-based grouping",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Verbose output",
)
def process_dxf(
    dxf_file: Path,
    config: Path,
    landxml: Path | None,
    output: Path | None,
    grouping: str,
    text_assignment: str,
    max_text_distance: float,
    color_tolerance: float,
    verbose: bool,
) -> None:
    """Process DXF file and export pipe/shaft data for Revit modeling.

    This tool processes DXF files containing pipes and shafts, extracts
    geometry information, groups elements by medium, assigns texts to pipes,
    and exports the data in JSON format suitable for Revit import.

    Arguments:
        DXF_FILE: Path to the DXF file to process
        CONFIG: JSON configuration with assignment rules
    """
    if verbose:
        click.echo(f"Processing DXF file: {dxf_file}")

    # Set default output path if not provided
    if output is None:
        output = dxf_file.with_suffix(".json")

    try:
        # Load configuration file
        handler = ConfigurationHandler(config)
        handler.load_config()

        # Load and process DXF file
        if verbose:
            click.echo("Loading DXF file...")

        reader = DXFReader(dxf_file)
        reader.load_file()

        processor = DXFProcessor(handler)
        processor.extract_mediums(reader)

        if verbose:
            e_count, t_count = processor.element_count()
            click.echo(f"{len(handler.mediums)}: Verschiedene Mediums gefunden")
            click.echo(f"Extracted {e_count}/{t_count} point based elements")
            e_count, t_count = processor.line_count()
            click.echo(f"Extracted {e_count}/{t_count} line based elements")

        # Group elements by medium (already handled by config loading)
        if verbose:
            click.echo("Using configuration-based grouping...")

        if text_assignment.lower() == "zone":
            text_assigner = ZoneBasedTextAssigner(max_distance=max_text_distance)
        else:
            text_assigner = SpatialTextAssigner(max_distance=max_text_distance)

        click.echo("Assigning texts to elements...")
        processor.assign_texts_to_mediums(text_assigner)

        click.echo("Updating dimensions based on assigned texts...")
        dimension_updater = DimensionUpdater(target_unit="m")
        processor.update_dimensions(dimension_updater)

        # Process LandXML if provided
        if landxml:
            landxml_reader = LandXMLReader(landxml)

            if verbose:
                click.echo(f"Loading LandXML file: {landxml}")
            landxml_reader.load_file()

            click.echo("Updating points elevation from LandXML...")
            processor.update_points_elevation(landxml_reader)

        # Assign texts to elements
        if verbose:
            click.echo(f"Assigning texts using {text_assignment} strategy...")

        # Count successful text assignments
        total_assigned = 0
        for medium in processor.mediums:
            total_assigned += sum(
                1 for element in medium.element_data.elements if element.assigned_text is not None
            )
            total_assigned += sum(
                1 for element in medium.line_data.elements if element.assigned_text is not None
            )

        if verbose:
            click.echo(f"Assigned {total_assigned} texts to pipes")

        click.echo(f"Exporting to JSON: {output}")
        exporter = JsonExporter(output)
        processor.export_data(exporter)

        if verbose:
            click.echo("Processing completed successfully!")

        # Summary output
        click.echo(f"Processed {dxf_file}")
        click.echo(f"Output: {output}")
        click.echo(f"Lines: {sum(len(m.line_data.elements) for m in processor.mediums)}")
        click.echo(f"Elements: {sum(len(m.element_data.elements) for m in processor.mediums)}")
        click.echo(f"Text assignments: {total_assigned}")

    except Exception as e:
        raise click.ClickException(f"Processing failed: {e}") from e


@click.group()
@click.version_option()
def main() -> None:
    """DXF processor for Revit modeling.

    This tool processes DXF files containing infrastructure elements
    (pipes and shafts) and exports them in JSON format suitable for
    Revit modeling workflows.
    """
    pass


@main.command()
@click.argument("config_file", type=click.Path(path_type=Path))
def create_config(config_file: Path) -> None:
    """Create a sample configuration file for layer-based grouping.

    CONFIG_FILE: Path where the configuration file will be created
    """
    sample_config = {
        "Abwasserleitung": {
            "Leitung": {
                "Geometrie": [
                    {
                        "Name": "PIPE_SEWER",
                        "Farbe": "Braun",
                    },
                    {
                        "Name": "SHAFT_SEWER_2",
                        "Farbe": "Farbe 15",
                    },
                ],
                "Text": [
                    {
                        "Name": "TEXT_PIPE_DIMENSION",
                        "Farbe": [255, 100, 100],
                    }
                ],
            },
            "Element": {
                "Geometrie": [
                    {
                        "Name": "SHAFT_SEWER",
                        "Farbe": [200, 0, 0],
                    },
                    {
                        "Name": "SHAFT_SEWER_2",
                        "Farbe": "Farbe 15",
                    },
                ],
                "Text": [
                    {
                        "Name": "TEXT_SEWER",
                        "Farbe": [255, 100, 100],
                    }
                ],
            },
        },
        "Wasserleitung": {
            "Leitung": {
                "Geometrie": [
                    {
                        "Layer": "PIPE_WATER",
                        "Farbe": [0, 0, 255],
                    }
                ],
                "Text": [
                    {
                        "Layer": "TEXT_WATER",
                        "Farbe": [100, 100, 255],
                    }
                ],
            },
            "Element": {
                "Geometrie": [
                    {
                        "Layer": "SHAFT_WATER",
                        "Farbe": [0, 0, 200],
                    }
                ],
                "Text": [],
            },
        },
    }

    try:
        import json

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(sample_config, f, indent=2, ensure_ascii=False)

        click.echo(f"Sample configuration created: {config_file}")
        click.echo("Edit this file to match your DXF layer structure.")

    except OSError as e:
        raise click.ClickException(f"Cannot create configuration file: {e}") from e


# Add the process_dxf command to the main group
main.add_command(process_dxf)


if __name__ == "__main__":
    main()
