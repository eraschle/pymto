# jrsin - JSON Revit Import Package

Ein Python-Paket zum Importieren von DXF-Daten aus JSON-Dateien in Autodesk Revit, kompatibel mit IronPython 2.7 und RevitPythonShell.

## Übersicht

Das `jrsin` Paket liest JSON-Daten aus der `revit_data.json` Datei und erstellt entsprechende Revit-Elemente mit automatischer Typerstellung und Parameterverwaltung.

## Funktionen

- **IronPython 2.7 Kompatibilität**: Vollständig kompatibel mit RevitPythonShell
- **Automatische Typerstellung**: Erstellt neue Family-Typen basierend auf Elementdimensionen
- **Parameter-Management**: Richtet Shared Parameters für DXF-Importdaten ein
- **Batch-Verarbeitung**: Effiziente Verarbeitung großer Datenmengen
- **Fehlerbehandlung**: Robuste Fehlerbehandlung und Fortschrittsberichterstattung

## Struktur

```
src/jrsin/
├── __init__.py                 # Paket-Initialisierung
├── data_models.py             # Datenmodelle für JSON-Parsing
├── revit_creator.py           # Revit-Element- und Typ-Erstellung
├── parameter_manager.py       # Shared Parameter Management
├── revit_import_script.py     # Hauptskript für RevitPythonShell
└── README.md                  # Diese Dokumentation
```

## Installation und Verwendung

### 1. Vorbereitung

1. Kopieren Sie das gesamte `src/jrsin/` Verzeichnis an einen zugänglichen Ort
2. Stellen Sie sicher, dass die `revit_data.json` Datei verfügbar ist

### 2. Konfiguration

Öffnen Sie `revit_import_script.py` und aktualisieren Sie:

```python
# Pfad zur JSON-Datei anpassen
JSON_FILE_PATH = r"C:\Pfad\zu\Ihrer\revit_data.json"

# Family-Mapping anpassen (optional)
CUSTOM_FAMILY_MAPPING = {
    "WATER_SPECIAL": {
        "family_name": "Ihre Custom Family",
        "type_name": "Spezieller Typ",
        "category": BuiltInCategory.OST_GenericModel
    }
}
```

### 3. Ausführung in RevitPythonShell

1. Öffnen Sie Revit und ein Projekt
2. Starten Sie RevitPythonShell
3. Führen Sie das Skript aus:

```python
# Option 1: Direkt die Datei ausführen
exec(open(r'C:\Pfad\zu\jrsin\revit_import_script.py').read())

# Option 2: Module importieren und custom verwenden
import sys
sys.path.append(r'C:\Pfad\zu\src')

from jrsin.revit_import_script import RevitImportController
controller = RevitImportController(doc, r'C:\Pfad\zu\revit_data.json')
elements = controller.run_import()
```

## Klassen-Referenz

### RevitDataReader

Liest und parst JSON-Daten:

```python
reader = RevitDataReader("pfad/zu/revit_data.json")
reader.load_data()
elements = reader.get_all_elements()
stats = reader.get_statistics()
```

### RevitElementCreator

Erstellt Revit-Elemente und Family-Typen:

```python
creator = RevitElementCreator(doc)
creator.start_transaction("Elemente erstellen")
element = creator.create_element_from_data(element_data, family_mapping)
creator.commit_transaction()
```

### RevitParameterManager

Verwaltet Shared Parameters:

```python
param_mgr = RevitParameterManager(doc)
created_params = param_mgr.setup_dxf_import_parameters()
param_mgr.apply_element_data_to_parameters(element, element_data)
```

### RevitImportController

Hauptcontroller für den Import-Prozess:

```python
controller = RevitImportController(doc, json_file_path)
elements = controller.run_import(family_mapping, setup_parameters=True)
```

## Standard-Parameter

Das System erstellt automatisch folgende Shared Parameters:

- **DXF_ObjectType**: Original DXF Objekttyp
- **DXF_LayerName**: Original DXF Layer-Name  
- **DXF_PointCount**: Anzahl der Punkte in der ursprünglichen Geometrie
- **DXF_Diameter/Radius/Width/Height**: Elementdimensionen
- **DXF_CenterX/Y/Z**: Zentrumskoordinaten
- **DXF_ImportDate**: Import-Datum

## Family-Mapping

Das System verwendet ein konfigurierbares Family-Mapping:

```python
family_mapping = {
    "OBJECT_TYPE": {
        "family_name": "Name der Revit Family",
        "type_name": "Typ-Name", 
        "category": BuiltInCategory.OST_Category
    }
}
```

Typ-Namen werden automatisch basierend auf Dimensionen generiert:
- `WATER_SPECIAL_D200` (Durchmesser 200)
- `SHAFT_W100_H200` (Breite 100, Höhe 200)

## Fehlerbehandlung

Das System bietet umfangreiche Fehlerbehandlung:

- Validierung der JSON-Datei
- Überprüfung der Revit-Dokumentzugänglichkeit
- Transaktions-Rollback bei Fehlern
- Detaillierte Fehler- und Fortschrittsberichte

## Anpassung

### Custom Family-Mapping

```python
custom_mapping = {
    "WATER_SPECIAL": {
        "family_name": "Meine Wasser Family",
        "type_name": "Speziell",
        "category": BuiltInCategory.OST_PipeAccessory
    }
}
```

### Custom Parameter

```python
custom_params = {
    "Mein_Parameter": {
        "type": SpecTypeId.String.Text,
        "is_instance": True,
        "description": "Benutzerdefinierter Parameter"
    }
}
param_mgr.create_project_parameters_for_elements(custom_params)
```

## Batch-Verarbeitung

Das System verarbeitet Elemente in Batches (standardmäßig 50 pro Batch) für optimale Performance:

```python
created_elements = creator.create_elements_from_data_list(
    elements_data, 
    family_mapping, 
    batch_size=100
)
```

## Troubleshooting

### Häufige Probleme

1. **"Revit API not available"**
   - Stellen Sie sicher, dass das Skript in RevitPythonShell läuft

2. **"JSON file not found"**
   - Überprüfen Sie den Pfad in `JSON_FILE_PATH`

3. **"No shared parameter file found"**
   - Erstellen Sie eine Shared Parameter Datei in Revit
   - Oder deaktivieren Sie Parameter-Setup: `setup_parameters=False`

4. **"Family not found"**
   - Laden Sie die benötigten Families in das Projekt
   - Oder passen Sie das Family-Mapping an verfügbare Families an

### Debug-Modus

Für Debugging können Sie einzelne Komponenten testen:

```python
# Data Reader testen
reader = test_data_reader()

# Einzelnes Element erstellen
element_data = reader.get_all_elements()[0]
creator = RevitElementCreator(doc)
creator.start_transaction()
element = creator.create_element_from_data(element_data)
creator.commit_transaction()
```

## Kompatibilität

- **IronPython 2.7** (RevitPythonShell)
- **Revit 2019+** (getestet)
- **Windows** Betriebssystem

## Lizenz

Dieses Projekt ist Teil des dxfto-Packages und folgt dessen Lizenzbestimmungen.