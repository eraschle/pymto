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
from .models import Unit
from .process.assigners import SpatialTextAssigner
from .process.creator import MediumObjectCreator
from .process.dimension import ParameterUpdater
from .process.dimension.conduit_bank_calculator import ConduitBankCalculator
from .process.revit_updater import RevitFamilyNameUpdater
from .processor import DXFProcessor
from .protocols import IDimensionCalculator, IExporter


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
    "land-xml",
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
    land_xml: Path,
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

    click.echo(f"Processing DXF: {dxf_file.name}")
    try:
        if verbose:
            click.echo(f"Loading configuration from: {config.resolve().as_posix()}")
        handler = ConfigurationHandler(config)
        handler.load_config()

        processor = DXFProcessor(handler)
        extrator = MediumObjectCreator(dxf_path=dxf_file)

        click.echo(f"Extracting mediums from DXF: {dxf_file.name}")
        processor.extract_mediums(extractor=extrator)

        if verbose:
            click.echo(f"Extracted mediums: {len(list(processor.mediums))} Mediums")

        click.echo(f"Assigning texts to elements with max distance: {max_text_distance} m")
        text_assigner = SpatialTextAssigner(max_distance=max_text_distance)
        processor.assign_texts_to_mediums(text_assigner)
        _print_assignment_statistic(processor)

        click.echo("Updating dimensions based on assigned texts...")
        param_updater = ParameterUpdater(target_unit=Unit.METER)
        processor.update_parameters(updater=param_updater)

        # Process LandXML if provided
        land_xml_reader = LandXMLReader(land_xml)
        land_xml_reader.load_file()
        click.echo("Updating points elevation from LandXML...")
        processor.update_points_elevation(updater=land_xml_reader)

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
            # shapely_analyzer.analyze_and_normalize_pipe_gradients()

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
        click.echo("Calculate dimensions for shafts and pipes...")
        # processor.calculate_shaft_height(gradient=gradient_analyzer)
        dimension_calculators: list[IDimensionCalculator] = [
            ConduitBankCalculator(max_pipes_per_row=4, cap_between_pipes=50),
            gradient_analyzer,
        ]
        processor.calculate_dimensions(calculators=dimension_calculators)

        revit_updater = RevitFamilyNameUpdater()
        click.echo("Update Family and Family Type names based on configuration...")
        processor.update_family_and_types(updater=revit_updater)
        click.echo("Adding parameters to elements based on configuration...")
        processor.add_config_parameters(updater=revit_updater)
        click.echo("Removing duplicate point objects...")
        removed_objects = processor.remove_duplicate_point_objects(updater=revit_updater)
        if removed_objects:
            _print_removed_duplicatre_statistic(removed_objects)

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
    header_line = f"{'Medium':<25} {'Total Elem.':>12} {'Total Text':>12} {'Elem. w/ Text':>15} {'% Assigned':>12}"
    header_length = len(header_line)
    click.echo("\n" + "=" * header_length)
    click.echo("TEXT ASSIGNMENT STATISTICS")
    click.echo("=" * header_length)
    click.echo(f"{'Medium':<25} {'Total Elem.':>12} {'Total Text':>12} {'Elem. w/ Text':>15} {'% Assigned':>12}")
    click.echo("-" * header_length)

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
    click.echo("-" * header_length)


def _print_removed_duplicatre_statistic(removed_objects: dict[str, tuple[list, list]]) -> None:
    header_line = f"{'Medium':<25} {'Total Elemment.':>12} {'Removed':>12} {'% Percentage':>11}"
    header_length = len(header_line)
    click.echo("\n" + "=" * header_length)
    click.echo("REMOVED DUPLICATE STATISTICS")
    click.echo("=" * header_length)
    click.echo(f"{'Medium':<25} {'Total Elemment.':>12} {'Removed':>12} {'% Percentage':>11}")
    click.echo("-" * header_length)

    for medium, statistics in removed_objects.items():
        elements, removed = statistics
        element_count = len(elements)
        removed_count = len(removed)

        export_perc = removed_count / element_count * 100
        export_perc = f"{export_perc:.1f}%"
        click.echo(f"{medium:<25} {element_count:>12} {removed_count:>12} {export_perc:>11}")

    click.echo("-" * header_length)


def _print_export_statistic(exporter: IExporter):
    header_line = f"{'Medium':<25} {'Total Elem.':>12} {'Exported':>12} {'Not Exported':>15} {'% Percentage':>11}"
    header_length = len(header_line)
    click.echo("\n" + "=" * header_length)
    click.echo("EXPORT STATISTICS")
    click.echo("=" * header_length)
    click.echo(f"{'Medium':<25} {'Total Elem.':>12} {'Exported':>12} {'Not Exported':>15} {'% Percentage':>11}")
    click.echo("-" * header_length)

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

    click.echo("-" * header_length)


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
