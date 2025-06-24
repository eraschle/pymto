"""Command-line interface for DXF processing and Revit export.

This module provides the main CLI interface using Click for processing
DXF files with optional LandXML elevation data and exporting to JSON
format suitable for Revit modeling.
"""

from pathlib import Path

import click

from .io.dxf_reader import DXFReader
from .groupers import ColorBasedGrouper, LayerBasedGrouper
from .exporter import JSONExporter, RevitJSONExporter
from .io.landxml_reader import LandXMLReader
from .assigners import SpatialTextAssigner, ZoneBasedTextAssigner


@click.command()
@click.argument("dxf_file", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--landxml",
    "-l",
    type=click.Path(exists=True, path_type=Path),
    help="LandXML file for elevation data (DGM)",
)
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output JSON file path")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, path_type=Path),
    help="JSON configuration file for layer-based grouping",
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
    default=50.0,
    help="Maximum distance for text-to-pipe assignment",
)
@click.option(
    "--color-tolerance", type=float, default=30.0, help="Color tolerance for color-based grouping"
)
@click.option("--revit-format", is_flag=True, help="Export in Revit-specific JSON format")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def process_dxf(
    dxf_file: Path,
    landxml: Path | None,
    output: Path | None,
    config: Path | None,
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
    ad exports the data in JSON format suitable for Revit import.

    DXF_FILE: Path to the DXF file to process
    """
    if verbose:
        click.echo(f"Processing DXF file: {dxf_file}")

    # Set default output path if not provided
    if output is None:
        output = dxf_file.with_suffix(".json")

    try:
        # Load and process DXF file
        if verbose:
            click.echo("Loading DXF file...")

        dxf_reader = DXFReader(dxf_file)
        dxf_reader.load_file()

        pipes = dxf_reader.extract_pipes()
        shafts = dxf_reader.extract_shafts()
        texts = dxf_reader.extract_texts()

        if verbose:
            click.echo(f"Extracted {len(pipes)} pipes, {len(shafts)} shafts, {len(texts)} texts")

        # Process LandXML if provided
        if landxml:
            if verbose:
                click.echo(f"Loading LandXML file: {landxml}")

            landxml_reader = LandXMLReader(landxml)
            landxml_reader.load_file()

            # Update Z coordinates for all elements
            for pipe in pipes:
                pipe.points = landxml_reader.update_points_elevation(pipe.points)

            for shaft in shafts:
                shaft.position = landxml_reader.update_points_elevation([shaft.position])[0]

            for text in texts:
                text.position = landxml_reader.update_points_elevation([text.position])[0]

            if verbose:
                click.echo("Updated Z coordinates from LandXML")

        # Group elements by medium
        if verbose:
            click.echo(f"Grouping elements using {grouping} strategy...")

        if grouping.lower() == "layer":
            if config is None:
                raise click.ClickException("Layer-based grouping requires --config option")

            grouper = LayerBasedGrouper(config)
            grouper.load_config()
        else:
            grouper = ColorBasedGrouper(color_tolerance=color_tolerance)

        media = grouper.group_elements(pipes, shafts, texts)

        if verbose:
            click.echo(f"Created {len(media)} media groups")

        # Assign texts to pipes
        if verbose:
            click.echo(f"Assigning texts using {text_assignment} strategy...")

        if text_assignment.lower() == "zone":
            text_assigner = ZoneBasedTextAssigner(max_distance=max_text_distance)
        else:
            text_assigner = SpatialTextAssigner(max_distance=max_text_distance)

        for medium in media:
            medium.pipes = text_assigner.assign_texts_to_pipes(medium.pipes, medium.texts)

        # Count successful text assignments
        total_assigned = sum(
            sum(1 for pipe in medium.pipes if pipe.assigned_text is not None) for medium in media
        )

        if verbose:
            click.echo(f"Assigned {total_assigned} texts to pipes")

        # Export to JSON
        if verbose:
            click.echo(f"Exporting to JSON: {output}")

        if revit_format:
            exporter = RevitJSONExporter(output)
        else:
            exporter = JSONExporter(output)

        exporter.export_media(media)

        if verbose:
            click.echo("Processing completed successfully!")

        # Summary output
        click.echo(f"Processed {dxf_file}")
        click.echo(f"Output: {output}")
        click.echo(f"Media: {len(media)}")
        click.echo(f"Pipes: {sum(len(m.pipes) for m in media)}")
        click.echo(f"Shafts: {sum(len(m.shafts) for m in media)}")
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
            "Leitung": {"Layer": "PIPE_SEWER", "Farbe": [255, 0, 0]},
            "Schacht": {"Layer": "SHAFT_SEWER", "Farbe": [200, 0, 0]},
            "Text": {"Layer": "TEXT_SEWER", "Farbe": [255, 100, 100]},
        },
        "Wasserleitung": {
            "Leitung": {"Layer": "PIPE_WATER", "Farbe": [0, 0, 255]},
            "Schacht": {"Layer": "SHAFT_WATER", "Farbe": [0, 0, 200]},
            "Text": {"Layer": "TEXT_WATER", "Farbe": [100, 100, 255]},
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
