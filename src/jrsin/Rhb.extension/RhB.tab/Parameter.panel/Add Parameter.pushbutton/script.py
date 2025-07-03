# -*- coding: utf-8 -*-
__title__ = "Set Parameter Data"
__author__ = "Erich Raschle"
__doc__ = """Version = 1.0
Date    = 03.07.2025
__________________________________________________________________
Description:
Fügt die Shared Parameter aus der Shared Parameter Datei
als Projektparameter in das aktuelle Revit-Projekt ein.
__________________________________________________________________
How-to:
Selektieren Sie die CSV-Datei mit den Parametern Definitionen.
Durch OK wird der Vorgang gestartet.
__________________________________________________________________
Prerequisite:
- Keine
__________________________________________________________________
Last update:
- [03.07.2025] Initial version
__________________________________________________________________
"""

from Autodesk.Revit.DB import (
    BuiltInCategory,
    Document,
    Element,
    FamilyInstance,
    FilteredElementCollector,
    StorageType,
)
from pyrevit import forms
from pyrevit.revit import Transaction, TransactionGroup


def _read_csv(file_path):
    with open(file_path, mode="r", encoding="utf-8") as csvfile:
        data = csvfile.read().strip().splitlines()
        headers = [str(hdr).strip() for hdr in data[0].split(";")]
        rows = []
        for row in data[1:]:
            values = row.split(";")
            rows.append(dict(zip(headers, values)))  # noqa [B905}
    return rows


def _get_family_instances(document: Document, categories):
    # type: (Document, list[BuiltInCategory]) -> list[Element]
    collector = FilteredElementCollector(document)
    for category in categories:
        collector = collector.OfCategory(category)
    collector = collector.OfClass(FamilyInstance)
    return collector.ToElements()


def _get_parameter_value(element: Element, param_name: str):
    # type: (Element, str) -> str | None
    param = element.LookupParameter(param_name)
    if param is None or not param.HasValue:
        return None
    if param.StorageType == StorageType.String:
        return param.AsString()
    return param.AsValueString()


def _elements_grouped_by(document: Document, group_param: str, categories=None):
    # type: (Document, str, list | None) -> dict[str, list[FamilyInstance]]
    if categories is None or not categories:
        categories = [BuiltInCategory.OST_GenericModel]
    fdk_groups = {}
    for instance in _get_family_instances(document, categories):
        fdk_id = _get_parameter_value(instance, group_param)
        if fdk_id is None or len(fdk_id.strip()) == 0:
            continue
        if fdk_id not in fdk_groups:
            fdk_groups[fdk_id] = []
        fdk_groups[fdk_id].append(instance)
    return fdk_groups


def _set_parameter_value(element: Element, param_dict):
    # type: (Document, dict[str, object]) -> None
    for param_name, value in param_dict.items():
        param = element.LookupParameter(param_name)
        if param is None:
            print(f"Parameter {param_name} not found in element {element.Id}")
            continue
        if param.StorageType == StorageType.String:
            param.Set(str(value))
        elif param.StorageType == StorageType.Double:
            try:
                param.Set(float(str(value)))  # pyright: ignore[reportArgumentType]
            except ValueError:
                print(f"Invalid value for double parameter {param_name}: {value}")
        elif param.StorageType == StorageType.Integer:
            try:
                param.Set(int(str(value)))  # pyright: ignore[reportArgumentType]
            except ValueError:
                print(f"Invalid value for integer parameter {param_name}: {value}")
        else:
            print(f"Unsupported {param_name} Value {value} in element {element.Id}")


def import_data(document: Document, data_file: str, fdk_param: str) -> int:
    fdk_groups = _elements_grouped_by(document, group_param="FDK_ID", categories=None)
    parameter_data = _read_csv(data_file)
    updated_elements = 0
    for param_row in parameter_data:
        fdk_id = param_row.get(fdk_param, None)
        if fdk_id is None:
            continue
        if fdk_id not in fdk_groups:
            print(f"FDK_ID {fdk_id}: No elements found in document")
            continue
        with Transaction(doc=document, name=f"Set Parameters for FDK_ID {fdk_id}"):
            for instance in fdk_groups[fdk_id]:
                _set_parameter_value(instance, param_row)
                updated_elements += 1
    return updated_elements


def main():
    doc = __revit__.ActiveUIDocument.Document
    if doc is None:
        forms.alert("No active Revit document found")
        return

    # Select JSON file
    parameter_data = forms.pick_file(file_ext="csv", title="Datei mit Parameter Daten auswählen")
    if isinstance(parameter_data, list):
        parameter_data = parameter_data[0]

    if parameter_data is None:
        forms.alert("Keine Datei mit Parameter Daten ausgewählt")
        return

    updated_elements = 0
    fdk_parameter = "FDK_Objektnummer"
    with TransactionGroup(doc=doc, name="Import Parameter Data"):
        updated_elements = import_data(doc, parameter_data, fdk_parameter)

    if updated_elements == 0:
        forms.alert(
            title="Import Result",
            msg="No elements updated. Please check the FDK_IDs in the CSV file.",
        )
    else:
        forms.alert(
            title="Import Result",
            msg=f"Import completed! Updated {updated_elements} elements",
        )


if __name__ == "__main__":
    main()
