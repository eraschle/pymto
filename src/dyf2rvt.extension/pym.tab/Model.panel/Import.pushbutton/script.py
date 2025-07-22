# -*- coding: utf-8 -*-
"""
Import DXF Data - pyRevit Button Script
Simple extension to read revit_data.json and create elements in Revit
"""

import json
from pathlib import Path

from Autodesk.Revit.DB import (
    XYZ,
    AdaptiveComponentInstanceUtils,
    BasePoint,
    BuiltInCategory,
    Document,
    Element,
    ElementId,
    FamilySymbol,
    FilteredElementCollector,
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
from pyrevit.revit.db.transaction import Transaction


def get_length_value(value, unit=None):
    # type: (float, str | None) -> float
    """Convert length value to internal units based on unit type"""
    if unit is None or unit.lower() == "m":
        return value  # No conversion needed
    if unit.lower() == "mm":
        return value * 0.001
    if unit.lower() == "cm":
        return value * 0.01
    else:
        raise ValueError(f"Unknown unit type: {unit}")


def get_shared_project_point(document: Document):
    base_point = BasePoint.GetProjectBasePoint(document)
    position = base_point.SharedPosition
    return {
        "east": UnitUtils.ConvertFromInternalUnits(position.X, UnitTypeId.Meters),
        "north": UnitUtils.ConvertFromInternalUnits(position.Y, UnitTypeId.Meters),
        "altitude": UnitUtils.ConvertFromInternalUnits(position.Z, UnitTypeId.Meters),
    }


class ElementData(object):
    """Represents element data from JSON with support for both point-based and line-based elements"""

    def __init__(self, json_data):
        # type: (dict) -> None
        """Initialize ElementData from JSON dictionary"""
        self.object_type = json_data.get("object_type", "")
        self.family = json_data.get("family", "")
        self.family_type = json_data.get("family_type", "")
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


class RevitImporter(object):
    """Simple importer for DXF data from JSON"""

    def __init__(self, document: Document):
        # type: (Document, dict) -> None
        self.document = document

    def load_json_data(self, json_path):
        # type: (str) -> dict
        """Load JSON data from file"""
        with open(json_path) as f:
            return json.load(f)

    def get_family_collector(self):
        # type: () -> FilteredElementCollector
        """Get collector for Generic Model families"""
        collector = FilteredElementCollector(self.document)
        collector = collector.OfCategory(BuiltInCategory.OST_GenericModel)  # pyright: ignore[reportArgumentType]
        return collector.OfClass(FamilySymbol)

    def get_first_family_symbol(self, family: str):
        # type: (str) -> FamilySymbol | None
        """Get first available Generic Model family symbol"""
        collector = self.get_family_collector()
        for symbol in collector.ToElements():
            if not isinstance(symbol, FamilySymbol):
                continue
            if symbol.FamilyName != family:
                continue
            return symbol
        return None

    def get_or_create_symbol(self, element_data: ElementData):
        # type: (dict) -> FamilySymbol | None
        """Get first available Generic Model family symbol"""
        collector = self.get_family_collector()
        family_symbol = None
        for symbol in collector.ToElements():
            if not isinstance(symbol, FamilySymbol):
                continue
            if symbol.FamilyName != element_data.family:
                continue
            family_symbol = symbol
            if symbol.Name != element_data.family_type:
                continue
            if not symbol.IsActive:
                symbol.Activate()
            return symbol
        if family_symbol is None:
            family_name = element_data.family
            type_name = element_data.family_type
            raise ValueError(f"Family symbol not found: {family_name}, {type_name}")
        family_symbol = family_symbol.Duplicate(element_data.family_type)
        if not isinstance(family_symbol, FamilySymbol):
            family_name = element_data.family
            type_name = element_data.family_type
            raise ValueError(f"Failed to duplicate family symbol: {family_name}, {type_name}")
        if not family_symbol.IsActive:
            family_symbol.Activate()
        return family_symbol

    def create_xyz_from_point(self, point_data):
        # type: (dict) -> XYZ
        """Convert point data to Revit XYZ"""
        project_zero = get_shared_project_point(self.document)
        coords = []
        for attr, value in point_data.items():
            coord = point_data.get(attr, 0.0) - project_zero.get(attr, 0.0)
            if attr != 0:
                coord = UnitUtils.ConvertToInternalUnits(value, UnitTypeId.Meters)
            coords.append(coord)
        return XYZ(*coords)

    def create_element(self, element_data: ElementData, family_symbol: FamilySymbol):
        # type: (ElementData, FamilySymbol) -> list[Element]
        """Create Revit element from ElementData"""
        if element_data.is_point_based():
            return self.create_point_based_element(element_data, family_symbol)
        elif element_data.is_line_based():
            return self.create_line_based_element(element_data, family_symbol)
        raise ValueError(f"Element is neither point or line-based, got: {element_data.object_type}")

    def create_point_based_element(self, element_data: ElementData, family_symbol: FamilySymbol):
        # type: (ElementData, FamilySymbol) -> list[Element]
        """Create point-based element (normal FamilyInstance)"""
        if element_data.insert_point is None:
            raise ValueError("ElementData is not point-based, Did you check is_point_based() first?")

        position = self.create_xyz_from_point(element_data.insert_point)
        instance = self.document.Create.NewFamilyInstance(  # pyright: ignore[reportAttributeAccessIssue]
            position, family_symbol, StructuralType.NonStructural
        )

        return [instance]

    def _get_reference_point(self, element_id: ElementId):
        # type: (ElementId) -> ReferencePoint
        """Get reference point from element ID"""
        ref_point = self.document.GetElement(element_id)
        if not isinstance(ref_point, ReferencePoint):
            raise ValueError(f"ElementId {element_id} is not a ReferencePoint")
        return ref_point

    def create_line_based_element(self, element_data: ElementData, family_symbol: FamilySymbol):
        # type: (ElementData, FamilySymbol) -> list[Element]
        """Create line-based element (AdaptiveComponent)"""
        instances = []
        all_points = element_data.get_all_points()
        if len(all_points) < 2:
            raise ValueError(
                "ElementData is not line-based, Did you check is_line_based() first? "
                f"Expected at least 2 points, got: {len(all_points)}"
            )
        for idx, point in enumerate(all_points):
            if idx == 0:
                continue
            instance = AdaptiveComponentInstanceUtils.CreateAdaptiveComponentInstance(self.document, family_symbol)
            adaptive_points = AdaptiveComponentInstanceUtils.GetInstancePlacementPointElementRefIds(instance)

            start_point = self.create_xyz_from_point(all_points[idx - 1])
            end_point = self.create_xyz_from_point(point)
            try:
                start_ref = self._get_reference_point(adaptive_points[0])
                start_ref.Position = start_point

                end_ref = self._get_reference_point(adaptive_points[1])
                end_ref.Position = end_point
            except Exception as ex:
                print(
                    f"Failed to set adaptive points for {element_data.family} - {element_data.family_type} ({len(all_points)}): {ex}"
                )
                continue

            instances.append(instance)
        return instances

    def _get_parameter_value(self, parameter: Parameter, parameter_data):
        # type: (Parameter, dict) -> str | int | float | None
        """Set parameter value with unit conversion if needed"""
        value = parameter_data["value"]
        if value is None:
            return None

        if parameter.StorageType == StorageType.ElementId:
            raise NotImplementedError("ElementId parameters are not supported in this script")
        unit_type = parameter_data.get("unit", "").lower()
        if parameter.StorageType == StorageType.Double:
            if unit_type is None:
                return float(value)
            if unit_type in ["mm", "cm", "m"]:
                value = get_length_value(value, unit=unit_type)
                return UnitUtils.ConvertToInternalUnits(float(value), UnitTypeId.Meters)
            if unit_type in ["degree", "grad"]:
                return UnitUtils.ConvertToInternalUnits(float(value), UnitTypeId.Degrees)
            raise ValueError(f"Unknown unit type: {unit_type}")
        if parameter.StorageType == StorageType.Integer:
            if parameter_data.get("value_type", None) == "BOOLEAN":
                return 1 if value else 0
            return int(value)
        return str(value)

    def _set_parameter_value(self, parameter: Parameter, parameter_data):
        # type: (Parameter, dict) -> None
        """Set parameter value with unit conversion if needed"""
        value = self._get_parameter_value(parameter=parameter, parameter_data=parameter_data)
        if value is None:
            return
        try:
            parameter.Set(value)  # pyright: ignore[reportArgumentType]
        except Exception as ex:
            print(f"Failed to set parameter {parameter.Definition.Name}: {ex}")

    def set_element_parameters(self, element: Element, element_data: ElementData):
        # type: (Element, ElementData) -> None
        """Set parameters on element instance"""
        for parameter_data in element_data.parameters:
            parameter = element.LookupParameter(parameter_data["name"])
            if parameter is None or parameter.IsReadOnly:
                continue
            self._set_parameter_value(parameter=parameter, parameter_data=parameter_data)

    def import_data(self, json_path):
        # type: (str) -> int
        """Import all data from JSON file"""
        json_data = self.load_json_data(json_path)

        created_count = 0
        for medium, elements in json_data.items():
            # Process each category
            print(f"Processing medium: {medium} with {len(elements)} elements")
            with Transaction(doc=self.document, name=f"Import {medium}") as tx:
                for element in elements:
                    # Create ElementData object from JSON
                    element_data = ElementData(element)
                    family_symbol = self.get_or_create_symbol(element_data)
                    if family_symbol is None:
                        print(f"Family symbol not found for {element_data.family} - {element_data.family_type}")
                        continue

                    self.set_element_parameters(family_symbol, element_data)
                    instances = self.create_element(element_data, family_symbol)
                    for instance in instances:
                        self.set_element_parameters(instance, element_data)
                    created_count += len(instances)

        return created_count


def main():
    # type: () -> None
    """Main function"""
    doc = __revit__.ActiveUIDocument.Document

    if doc is None:
        forms.alert("No active Revit document found")
        return

    # Select JSON file
    json_file = forms.pick_file(file_ext="json", title="JSON Datei mit Element Daten auswählen")
    if isinstance(json_file, list):
        json_file = json_file[0]

    if json_file is None:
        forms.alert("Keine JSON Datei ausgewählt")
        return

    importer = RevitImporter(document=doc)
    count = importer.import_data(json_file)

    forms.alert(f"Import completed! Created {count} elements")


if __name__ == "__main__":
    main()
