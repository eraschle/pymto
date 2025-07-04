"""Command-line interface for DXF processing and Revit export.

This module provides the main CLI interface using Click for processing
DXF files with optional LandXML elevation data and exporting to JSON
format suitable for Revit modeling.
"""

import traceback
from pathlib import Path
from pprint import pp

import click

from .analyze import (
    ConnectionAnalyzerShapely,
    GradientAdjustmentParams,
    PipelineGradientAdjuster,
    PrefixBasedCompatibility,
)
from .config import ConfigurationHandler
from .io import JsonExporter, LandXMLReader
from .process.assigners import SpatialTextAssigner
from .process.creator import MediumObjectCreator
from .process.dimension import DimensionMapper, DimensionUpdater
from .process.revit_updater import RevitFamilyNameUpdater
from .processor import DXFProcessor, IExporter


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
    default=5.0,
    help="Maximum distance for text-to-pipe assignment",
)
@click.option(
    "--adjust-gradient",
    type=bool,
    is_flag=True,
    flag_value=True,
    help="Process gradient adjustment on pipes. (Default False)",
)
@click.option(
    "--verbose",
    "-v",
    type=bool,
    is_flag=True,
    flag_value=True,
    help="Process gradient adjustment on pipes. (Default False)",
)
def process_dxf(
    dxf_file: Path,
    config: Path,
    landxml: Path,
    output: Path | None,
    max_text_distance: float,
    adjust_gradient: bool,
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

    # Set default output path if not provided
    if output is None:
        output = dxf_file.with_suffix(".json")

    try:
        handler = ConfigurationHandler(config)
        handler.load_config()

        processor = DXFProcessor(handler)
        extrator = MediumObjectCreator(dxf_path=dxf_file)
        processor.extract_mediums(extractor=extrator)

        text_assigner = SpatialTextAssigner(max_distance=max_text_distance)
        click.echo("Assigning texts to elements...")
        processor.assign_texts_to_mediums(text_assigner)
        _print_assignment_statistic(processor)

        click.echo("Updating dimensions based on assigned texts...")
        dim_mapper = DimensionMapper()
        dimension_updater = DimensionUpdater(target_unit="m", dimension_mapper=dim_mapper)
        processor.update_dimensions(updater=dimension_updater)

        # Process LandXML if provided
        landxml_reader = LandXMLReader(landxml)
        landxml_reader.load_file()
        click.echo("Updating points elevation from LandXML...")
        processor.update_points_elevation(updater=landxml_reader)

        compatibility = PrefixBasedCompatibility(separator=" ")
        if adjust_gradient:
            # Handle gradient processing
            click.echo("Normalizing pipe gradients using shapely-based analysis...")
            shapely_analyzer = ConnectionAnalyzerShapely(
                tolerance=0.1,
                compatibility=compatibility,
                elevation_threshold=0.0,  # 5.0% gradient threshold
            )
            shapely_analyzer.load_multiple_mediums(processor.mediums)
            shapely_analyzer.analyze_and_normalize_pipe_gradients()

        params = GradientAdjustmentParams(
            manhole_search_radius=1,
            min_gradient_percent=1.0,
            gradient_break_threshold=5,
        )
        gradient_analyzer = PipelineGradientAdjuster(
            mediums=processor.mediums,
            params=params,
            compatibility=compatibility,
        )
        click.echo("Calculated cover to pipe heights on every shaft:")
        processor.calculate_cover_to_pipe_height(gradient=gradient_analyzer)

        click.echo("Adjusting and round parameter values...")
        processor.round_parameter_values(updater=dimension_updater)

        revit_updater = RevitFamilyNameUpdater()
        processor.update_family_and_types(updater=revit_updater)

        exporter = JsonExporter(output)
        processor.export_data(exporter=exporter)
        _print_export_statistic(exporter)
        if not verbose or not exporter.has_not_exported_elements():
            return
        click.echo("Not exported elements:")
        for medium, elements in exporter.not_exported_elements.items():
            if len(elements) == 0:
                continue
            click.echo(f"Medium: {medium}")
            click.echo("-" * 85)
            for element in elements:
                # params = [pp(param.to_dict()) for param in element.get_parameters()]
                click.echo(f"{pp(element)}")
            click.echo("")

    except Exception as e:
        message = f"Processing failed: {e}"
        if verbose:
            message += "\n" + traceback.format_exc()
        raise click.ClickException(message) from e


def _print_assignment_statistic(processor: DXFProcessor):
    click.echo("\n" + "=" * 85)
    click.echo("TEXT ASSIGNMENT STATISTICS")
    click.echo("=" * 85)
    click.echo(f"{'Medium':<25} {'Total Elem.':>12} {'Total Text':>12} {'Elem. w/ Text':>15} {'% Assigned':>12}")
    click.echo("-" * 85)

    for medium in processor.mediums:
        elem_stats = medium.get_point_statistics()
        line_stats = medium.get_line_statistics()

        total_elems = elem_stats["elements"] + line_stats["elements"]
        total_texts = elem_stats["texts"] + line_stats["texts"]
        assigned_elems = elem_stats["assigned"] + line_stats["assigned"]
        if total_texts == 0:
            assigned_perc = "~"
        else:
            assigned_perc = (assigned_elems / total_texts * 100) if total_elems > 0 else 0
            assigned_perc = f"{assigned_perc:.1f}%"

        click.echo(f"{medium.name:<25} {total_elems:>12} {total_texts:>12} {assigned_elems:>15} {assigned_perc:>11}")
    click.echo("-" * 85)


def _print_export_statistic(exporter: IExporter):
    click.echo("\n" + "=" * 85)
    click.echo("EXPORT STATISTICS")
    click.echo("=" * 85)
    click.echo(f"{'Medium':<25} {'Total Elem.':>12} {'Exported':>12} {'Not Exported':>15} {'% Percentage':>11}")
    click.echo("-" * 85)

    for medium, statistics in exporter.get_exported_statistics().items():
        exported = statistics["exported"]
        not_exported = statistics["not_exported"]
        total = statistics["total"]
        if total == 0:
            export_perc = "~"
        else:
            export_perc = (exported / total * 100) if total > 0 else 0
            export_perc = f"{export_perc:.1f}%"
        click.echo(f"{medium:<25} {total:>12} {exported:>12} {not_exported:>15} {export_perc:>11}")

    click.echo("-" * 85)


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
    config = {
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
        # reader = DXFReader(dxf_path=dxf_file)
        # object_layers = reader.get_layer_names()
        # text_layers = reader.get_layer_names()
        # block_names = reader.get_layer_names()
        config["Abwasserleitung"]["Element"].append({"Dxf": dxf_file})

    try:
        import json

        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        click.echo(f"Sample configuration created: {config_file}")
        click.echo("Edit this file to match your DXF layer structure.")

    except OSError as e:
        raise click.ClickException(f"Cannot create configuration file: {e}") from e


# Add the process_dxf command to the main group
main.add_command(process_dxf)


if __name__ == "__main__":
    main()
