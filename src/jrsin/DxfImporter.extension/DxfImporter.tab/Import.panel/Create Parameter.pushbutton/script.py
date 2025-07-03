# -*- coding: utf-8 -*-
import os

from Autodesk.Revit.DB import (
    BuiltInCategory,
    Category,
    CategorySet,
    Definition,
    DefinitionFile,
    DefinitionGroup,
    Document,
    ExternalDefinitionCreationOptions,
    ForgeTypeId,
    GroupTypeId,
    SpecTypeId,
    Transaction,
)
from pyrevit import forms


def _read_csv(file_path):
    """
    Reads a CSV file and returns a list of dictionaries.
    Each dictionary represents a row in the CSV file.
    """
    with open(file_path, mode="r", encoding="utf-8") as csvfile:
        data = csvfile.read().strip().splitlines()
        headers = [str(hdr).strip() for hdr in data[0].split(";")]
        rows = []
        for row in data[1:]:
            values = row.split(";")
            rows.append(dict(zip(headers, values, strict=True)))
    return rows


def _get_data_type(data_type) -> ForgeTypeId:
    data_type = data_type.strip().lower()
    if data_type == "integer":
        return SpecTypeId.Int.Integer
    elif data_type == "double":
        return SpecTypeId.Number
    elif data_type == "boolean":
        return SpecTypeId.Boolean.YesNo
    elif data_type == "length":
        return SpecTypeId.Length
    elif data_type == "angle":
        return SpecTypeId.Angle
    elif data_type == "string":
        return SpecTypeId.String.Text
    raise ValueError(f"Unsupported data type: {data_type}")


def _create_external_definition_options(definition_rows) -> list[ExternalDefinitionCreationOptions]:
    definitions = []
    for line in definition_rows:
        name = line["Name"]
        data_type = _get_data_type(line["Datentyp"])
        options = ExternalDefinitionCreationOptions(name=name.strip(), dataType=data_type)
        options.HideWhenNoValue = bool(line.get("HideWhenNoValue", "False"))
        options.UserModifiable = bool(line.get("UserModifiable", "True"))
        definitions.append(options)
    return definitions


def _create_shared_parameter_file(document: Document, definitions_file: str):
    previous_file = document.Application.SharedParametersFilename  # pyright: ignore[reportFunctionMemberAccess]
    try:
        if not os.path.exists(definitions_file):
            with open(definitions_file, "w", encoding="utf-8") as f:
                f.write("")
        document.Application.SharedParametersFilename = definitions_file  # pyright: ignore[reportFunctionMemberAccess]
        return definitions_file
    except Exception as e:
        forms.alert(f"Error creating shared parameter file: {e}")
        document.Application.SharedParametersFilename = previous_file  # pyright: ignore[reportFunctionMemberAccess]
        return previous_file


def _get_definition_or_none(definition_file: DefinitionFile, definition_name: str):
    # type: (DefinitionFile, str) -> Definition | None
    for group in definition_file.Groups.GetEnumerator():
        for definition in group.Definitions.GetEnumerator():
            if definition.Name != definition_name:
                continue
            return definition
    return None


def _get_or_create_group(definition_file: DefinitionFile, group_name: str = "Default") -> DefinitionGroup:
    for group in definition_file.Groups.GetEnumerator():
        if group.Name != group_name:
            continue
        return group
    return definition_file.Groups.Create("Default")


def _get_or_create_shared_parameter(
    definition_file: DefinitionFile,
    definition: ExternalDefinitionCreationOptions,
    group_name: str = "Default",
) -> Definition:
    # type: (DefinitionFile, ExternalDefinitionCreationOptions, str) -> Definition
    existing_definition = _get_definition_or_none(definition_file, definition.Name)
    if existing_definition:
        return existing_definition
    group = _get_or_create_group(definition_file, group_name)
    return group.Definitions.Create(definition)


def _create_shared_parameter(document: Document, definitions_rows: list):
    # type: (Document, list) -> list[Definition]
    shared_file = document.PathName.replace(".rvt", ".txt")
    previous_file = _create_shared_parameter_file(document, shared_file)
    if shared_file != previous_file:
        forms.alert(f"Error creating shared parameter file: {shared_file}")
        return []
    definitions_file = document.Application.OpenSharedParameterFile()  # pyright: ignore[reportFunctionMemberAccess]
    definition_options = _create_external_definition_options(definitions_rows)
    definitions = []
    for option in definition_options:
        definition = _get_or_create_shared_parameter(definitions_file, option, group_name="pyRevit")
        definitions.append(definition)

    return definitions


def _create_category_set(document, categories: list) -> CategorySet:
    category_set = document.Application.Create.NewCategorySet()  # pyright: ignore[reportFunctionMemberAccess]
    for bic in categories:
        category = Category.GetCategory(document, bic)  # pyright: ignore[reportAttributeAccessIssue]
        category_set.Insert(category)
    return category_set


def create_parameter_definitions(document: Document, definitions_file: str):
    # type: (Document, str) -> list[Definition]
    dict_lines = _read_csv(definitions_file)
    definition_rows = [line for line in dict_lines if line["Name"] and line["Datentyp"]]
    definitions = _create_shared_parameter(document, definition_rows)
    if len(definitions) == 0:
        return []
    categories = [BuiltInCategory.OST_GenericModel]
    category_set = _create_category_set(document, categories)
    category_names = [cat.Name for cat in category_set.GetEnumerator() if cat is not None]
    print(f"Create Project Parameters for Categories: {', '.join(category_names)}")
    app = document.Application  # pyright: ignore[reportFunctionMemberAccess]
    tx = Transaction(document, "Create Project Parameters")
    tx.Start()
    try:
        binding_map = document.ParameterBindings
        for definition in definitions:
            if binding_map.Contains(definition):
                print(f"Parameter already exists: {definition.Name} [{definition.GetDataType()}]")
                continue
            binding = app.Create.NewInstanceBinding(category_set)  # pyright: ignore[reportFunctionMemberAccess]
            binding_map.Insert(definition, binding, GroupTypeId.Data)
            print(f"Created parameter: {definition.Name} [{definition.GetDataType()}]")
        tx.Commit()
        return definitions
    except Exception as e:
        tx.RollBack()
        forms.alert(f"Error creating project parameters: {e}")
        return []


def main():
    # type: () -> None
    """Main function"""
    doc = __revit__.ActiveUIDocument.Document

    if doc is None:
        forms.alert("No active Revit document found")
        return

    # Select JSON file
    parameter_definition = forms.pick_file(file_ext="csv", title="Parameter Definitionen Datei auswählen")
    if isinstance(parameter_definition, list):
        parameter_definition = parameter_definition[0]
    if parameter_definition is None:
        forms.alert("Keine Datei mit Parameter Definitionen ausgewählt")
        return

    created_parameters = create_parameter_definitions(doc, parameter_definition)
    if not created_parameters:
        forms.alert("Keine Parameter erstellt. Überprüfen Sie das CSV-Dateiformat.")
    else:
        forms.alert(f"{len(created_parameters)} Parameter erfolgreich erstellt.")


if __name__ == "__main__":
    main()
