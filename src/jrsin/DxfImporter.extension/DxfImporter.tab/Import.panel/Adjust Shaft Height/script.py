# -*- coding: utf-8 -*-
"""
Import DXF Data - pyRevit Button Script
Simple extension to read revit_data.json and create elements in Revit
IronPython 3 compatible
"""

import json

from Autodesk.Revit.DB import (
    XYZ,
    AdaptiveComponentInstanceUtils,
    BoundingBoxIntersectsFilter,
    BoundingBoxXYZ,
    BuiltInCategory,
    Document,
    Element,
    ElementId,
    Family,
    FamilyInstance,
    FamilySymbol,
    FilteredElementCollector,
    Outline,
    Parameter,
    ReferencePoint,
    StorageType,
    UnitTypeId,
    UnitUtils,
)
from Autodesk.Revit.DB.Structure import (
    StructuralType,
)
from pyrevit import forms
from pyrevit.revit import Transaction


class ElementData(object):
    """Represents element data from JSON with support for both point-based and line-based elements"""

    def __init__(self, json_data):
        # type: (dict) -> None
        """Initialize ElementData from JSON dictionary"""
        self.object_type = json_data.get("object_type", "")
        self.family = json_data.get("family", "")
        self.family_type = json_data.get("family_type", "")
        self.dimensions = json_data.get("dimensions", {})
        self.parameters = json_data.get("parameters", [])

        # Handle both insert_point and line_points
        self.insert_point = json_data.get("insert_point")
        self.line_points = json_data.get("line_points", [])
        self.json_data = json_data

    def is_point_based(self):
        # type: () -> bool
        """Check if element is point-based (uses insert_point)"""
        return self.insert_point is not None

    def is_line_based(self):
        # type: () -> bool
        """Check if element is line-based (uses line_points for AdaptiveComponent)"""
        return len(self.line_points) > 1

    def get_all_points(self):
        # type: () -> list
        """Get all points for line-based elements"""
        return self.line_points if self.line_points else []


def get_family_collector(document: Document) -> FilteredElementCollector:
    # type: (Document) -> FilteredElementCollector
    """Get collector for Generic Model families"""
    collector = FilteredElementCollector(document)
    collector = collector.OfCategory(BuiltInCategory.OST_GenericModel)  # pyright: ignore[reportArgumentType]
    return collector.OfClass(FamilySymbol)


def contains_family_name(element: Element, family_names: list):
    if not isinstance(element, FamilySymbol):
        return False
    family_name = element.FamilyName
    return any(name in family_name for name in family_names)


def get_shaft_instance_elements_contains(document: Document, family_names: list):
    # type: (Document, list[str]) -> list[FamilySymbol]
    """Get first available Generic Model family symbol"""
    symbols = []
    collector = get_family_collector(document)
    for symbol in collector.ToElements():
        if not contains_family_name(symbol, family_names):
            continue
        symbols.append(symbol)
    return symbols


def get_family_instance_collector(document: Document, outline: Outline) -> FilteredElementCollector:
    # type: (Document, Outline) -> FilteredElementCollector
    """Get collector for Generic Model families"""
    collector = FilteredElementCollector(document)
    collector = collector.OfCategory(BuiltInCategory.OST_GenericModel)  # pyright: ignore[reportArgumentType]

    element_filter = BoundingBoxIntersectsFilter(outline)
    return collector.OfClass(FamilyInstance).WherePasses(element_filter)


def adjust_shaft_height(document: Document, symbol: FamilySymbol):
    for symbol in get_shaft_instances(document, symbol):
        myOutLn = Outline(XYZ(0, 0, 0), XYZ(100, 100, 100))


def main():
    # type: () -> None
    """Main function"""
    doc = __revit__.ActiveUIDocument.Document

    if doc is None:
        forms.alert("No active Revit document found")
        return

    # Select JSON file
    json_file = forms.pick_file(file_ext="json", title="revit_data.json Datei auswählen")
    if isinstance(json_file, list):
        json_file = json_file[0]

    if json_file is None:
        forms.alert("Keine JSON Datei ausgewählt")
        return

    # Select JSON file
    project_zero_path = forms.pick_file(file_ext="json", title="Project Koordinaten Datei auswählen")
    if isinstance(project_zero_path, list):
        project_zero_path = project_zero_path[0]

    if project_zero_path is None:
        forms.alert("Keine Projekt Koordinaten Datei ausgewählt")
        return

    project_zero = json.loads(open(project_zero_path, "r").read())
    project_zero = project_zero["Projektnullpunkt"]

    importer = RevitImporter(document=doc, project_zero=project_zero)
    count = importer.import_data(json_file)

    forms.alert("Import completed! Created {} elements".format(count))


if __name__ == "__main__":
    main()
