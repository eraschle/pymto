"""Command-line interface for DXF processing and Revit export.

This module provides the main CLI interface using Click for processing
DXF files with optional LandXML elevation data and exporting to JSON
format suitable for Revit modeling.
"""

from pathlib import Path

import click

from .config import ConfigurationHandler
from .io import DXFReader, JsonExporter, LandXMLReader
from .process.assigners import SpatialTextAssigner
from .process.creator import MediumObjectCreator
from .process.dimension import DimensionUpdater
from .process.dimension_mapper import DimensionMapper
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
@click.argument(
    "landxml",
    type=click.Path(exists=True, path_type=Path),
)
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output JSON file path",
)
@click.option(
    "--max-text-distance",
    type=float,
    default=1.0,
    help="Maximum distance for text-to-pipe assignment",
)
def process_dxf(
    dxf_file: Path,
    config: Path,
    landxml: Path,
    output: Path | None,
    max_text_distance: float,
) -> None:
    """Process DXF file and export pipe/shaft data for Revit modeling.

    This tool processes DXF files containing pipes and shafts, extracts
    geometry information, groups elements by medium, assigns texts to pipes,
    and exports the data in JSON format suitable for Revit import.

    Arguments:
        DXF_FILE: Path to the DXF file to process
        CONFIG: JSON configuration with assignment rules
    """

    # Set default output path if not provided
    if output is None:
        output = dxf_file.with_suffix(".json")

    try:
        # Load configuration file
        handler = ConfigurationHandler(config)
        handler.load_config()

        processor = DXFProcessor(handler)
        extrator = MediumObjectCreator(dxf_path=dxf_file)
        processor.extract_mediums(extractor=extrator)

        text_assigner = SpatialTextAssigner(max_distance=max_text_distance)
        click.echo("Assigning texts to elements...")
        processor.assign_texts_to_mediums(text_assigner)

        click.echo("Updating dimensions based on assigned texts...")
        dim_mapper = DimensionMapper()
        dimension_updater = DimensionUpdater(target_unit="m", dimension_mapper=dim_mapper)
        processor.update_dimensions(dimension_updater)

        # Process LandXML if provided
        if landxml:
            landxml_reader = LandXMLReader(landxml)
            landxml_reader.load_file()

            click.echo("Updating points elevation from LandXML...")
            processor.update_points_elevation(landxml_reader)

        exporter = JsonExporter(output)
        processor.export_data(exporter)

        click.echo(f"Processed {dxf_file}")
        click.echo(f"Output: {output}")
        _orint_statistic(processor)

    except Exception as e:
        raise click.ClickException(f"Processing failed: {e}") from e


def _orint_statistic(processor: DXFProcessor):
    click.echo("\n" + "=" * 85)
    click.echo("TEXT ASSIGNMENT STATISTICS")
    click.echo("=" * 85)
    click.echo(
        f"{'Medium':<25} {'Total Elem.':>12} {'Total Text':>12} {'Elem. w/ Text':>15} {'% Assigned':>12}"
    )
    click.echo("-" * 85)

    for medium in processor.mediums:
        elem_stats = medium.get_point_statistics()
        line_stats = medium.get_line_statistics()

        total_elems = elem_stats["elements"] + line_stats["elements"]
        total_texts = elem_stats["texts"] + line_stats["texts"]
        assigned_elems = elem_stats["assigned"] + line_stats["assigned"]
        assigned_perc = (assigned_elems / total_texts * 100) if total_elems > 0 else 0

        click.echo(
            f"{medium.name:<25} "
            f"{total_elems:>12} "
            f"{total_texts:>12} "
            f"{assigned_elems:>15} "
            f"{assigned_perc:>11.1f}%"
        )
    click.echo("-" * 85)

    click.echo(f"Total Objects: {sum([medium.get_point_total() for medium in processor.mediums])}")
    click.echo(f"Total Lines: {sum([medium.get_line_total() for medium in processor.mediums])}")


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
@click.option(
    "--dxf-file",
    "-d",
    type=click.Path(exists=True, path_type=Path),
    help="DXF file to create JSON config output from",
)
def create_config(config_file: Path, dxf_file: Path | None) -> None:
    """Create a sample configuration file for layer-based grouping.

    Parameters
    ----------
    config_file
        Path to the JSON configuration file
    dxf
        DXF file to create JSON config output from

    """
    sample_config = {
        "Abwasserleitung": {
            "Leitung": [
                {
                    "Unit": "mm",
                    "Category": "water",
                    "Family": "FAMILY-NAME",
                    "FamilyType": "FAMILY-TYPE-NAME",
                    "Geometrie": [
                        {
                            "Name": "PIPE_SEWER",
                            "Farbe": "Braun",
                        },
                        {
                            "Name": "SHAFT_SEWER_2",
                            "Farbe": "Farbe 15",
                            "Block": "Block name",
                        },
                    ],
                    "Text": [
                        {
                            "Name": "TEXT_PIPE_DIMENSION",
                        }
                    ],
                }
            ],
            "Element": [
                {
                    "Unit": "mm",
                    "Category": "water",
                    "Family": "FAMILY-NAME",
                    "FamilyType": "FAMILY-TYPE-NAME",
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
                }
            ],
        },
    }
    if dxf_file:
        reader = DXFReader(dxf_path=dxf_file)
        object_layers = reader.get_layer_names()
        text_layers = reader.get_layer_names()
        block_names = reader.get_layer_names()
        sample_config["Abwasserleitung"]["Element"].append({"Dxf": dxf_file})

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
