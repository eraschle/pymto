"""Command-line interface for DXF processing and Revit export.

This module provides the main CLI interface using Click for processing
DXF files with optional LandXML elevation data and exporting to JSON
format suitable for Revit modeling.
"""

from pathlib import Path

import click

from dxfto.config import ConfigurationHandler

from .assigners import SpatialTextAssigner, ZoneBasedTextAssigner
from .io.dxf_reader import DXFReader
from .io.json_exporter import AsIsDataJsonExporter, JsonExporter
from .io.landxml_reader import LandXMLReader


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
    "--revit-format",
    is_flag=True,
    help="Export in Revit-specific JSON format",
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
    revit_format: bool,
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

        dxf_reader = DXFReader(dxf_file)
        dxf_reader.load_file()

        dxf_reader.extract_data(handler.medium_configs)

        if verbose:
            click.echo(f"{len(handler.medium_configs)}: Verschiedene Mediums gefunden")
            click.echo(f"Extracted {handler.element_count} Elements, {handler.text_count} Text")

        # Process LandXML if provided
        if landxml:
            if verbose:
                click.echo(f"Loading LandXML file: {landxml}")

            landxml_reader = LandXMLReader(landxml)
            landxml_reader.load_file()

            # Update Z coordinates for all elements
            for medium in handler.medium_configs.values():
                # Update elements points/positions
                for element in medium.element_data.elements:
                    if element.points:
                        element.points = landxml_reader.update_points_elevation(element.points)
                    if element.positions:
                        element.positions = landxml_reader.update_points_elevation(element.positions)

                for element in medium.line_data.elements:
                    if element.points:
                        element.points = landxml_reader.update_points_elevation(element.points)
                    if element.positions:
                        element.positions = landxml_reader.update_points_elevation(element.positions)

                # Update text positions
                for text in medium.element_data.texts:
                    text.position = landxml_reader.update_points_elevation([text.position])[0]

                for text in medium.line_data.texts:
                    text.position = landxml_reader.update_points_elevation([text.position])[0]

            if verbose:
                click.echo("Updated Z coordinates from LandXML")

        # Group elements by medium (already handled by config loading)
        if verbose:
            click.echo("Using configuration-based grouping...")

        media = list(handler.medium_configs.values())

        if verbose:
            click.echo(f"Found {len(media)} configured media groups")

        # Assign texts to elements
        if verbose:
            click.echo(f"Assigning texts using {text_assignment} strategy...")

        if text_assignment.lower() == "zone":
            text_assigner = ZoneBasedTextAssigner(max_distance=max_text_distance)
        else:
            text_assigner = SpatialTextAssigner(max_distance=max_text_distance)

        for medium in media:
            # Assign texts to elements
            assigned_elements = text_assigner.assign_texts_to_point_based(
                medium.element_data.elements,
                medium.element_data.texts,
            )
            medium.element_data.elements.clear()
            medium.element_data.elements.extend(assigned_elements)

            # Assign texts to lines (pipes)
            assigned_lines = text_assigner.assign_texts_to_line_based(
                medium.line_data.elements,
                medium.line_data.texts,
            )
            medium.line_data.elements.clear()
            medium.line_data.elements.extend(assigned_lines)

        # Count successful text assignments
        total_assigned = 0
        for medium in media:
            total_assigned += sum(
                1 for element in medium.element_data.elements if element.assigned_text is not None
            )
            total_assigned += sum(
                1 for element in medium.line_data.elements if element.assigned_text is not None
            )

        if verbose:
            click.echo(f"Assigned {total_assigned} texts to pipes")

        # Export to JSON
        if verbose:
            click.echo(f"Exporting to JSON: {output}")

        if revit_format:
            exporter = AsIsDataJsonExporter(output)
        else:
            exporter = JsonExporter(output)

        exporter.export_media(media)

        if verbose:
            click.echo("Processing completed successfully!")

        # Summary output
        click.echo(f"Processed {dxf_file}")
        click.echo(f"Output: {output}")
        click.echo(f"Media: {len(media)}")
        click.echo(f"Lines: {sum(len(m.line_data.elements) for m in media)}")
        click.echo(f"Elements: {sum(len(m.element_data.elements) for m in media)}")
        click.echo(f"Text assignments: {total_assigned}")

    except Exception as e:
        raise click.ClickException(f"Processing failed: {e}") from e


@click.group()
@click.version_option()
def main() -> None:
    """DXF processor for pipes and shafts with Revit export.

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
