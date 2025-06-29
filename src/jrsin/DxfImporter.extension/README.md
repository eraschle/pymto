# DXF Importer pyRevit Extension

Eine pyRevit Extension zum Importieren von DXF-Daten aus JSON-Dateien in Autodesk Revit.

## Übersicht

Diese Extension ermöglicht den Import von DXF-Geometriedaten, die zuvor von der `dxfto` Anwendung in JSON-Format exportiert wurden, direkt in Revit als native Revit-Elemente.

## Features

- **Benutzerfreundliche UI**: Integriert sich nahtlos in die Revit Ribbon-Oberfläche
- **Automatische Elementerstellung**: Erstellt Revit Family Instances basierend auf DXF-Geometrie
- **Intelligente Typerstellung**: Generiert automatisch Family-Typen basierend auf Elementdimensionen
- **Parameter-Management**: Erstellt Shared Parameters für DXF-Metadaten
- **Batch-Verarbeitung**: Effiziente Verarbeitung großer Datenmengen
- **IronPython 2.7 Kompatibilität**: Vollständig kompatibel mit Revit's Python-Umgebung

## Installation

1. **pyRevit installieren**: Stellen Sie sicher, dass pyRevit in Ihrem Revit installiert ist
2. **Extension kopieren**: Kopieren Sie den gesamten `DxfImporter.extension` Ordner in einen der folgenden Verzeichnisse:
   - `%APPDATA%\pyRevit\Extensions\` (Benutzer-spezifisch)
   - `%PROGRAMDATA%\pyRevit\Extensions\` (System-weit)
3. **pyRevit neu laden**: Starten Sie Revit neu oder verwenden Sie `pyRevit → Reload pyRevit`

## Nutzung

### 1. Extension aktivieren
Nach der Installation erscheint ein neuer "DXF Importer" Tab in der Revit Ribbon.

### 2. JSON-Datei vorbereiten
Verwenden Sie die `dxfto` Anwendung, um DXF-Dateien in das erforderliche JSON-Format zu konvertieren.

### 3. Import durchführen
1. Klicken Sie auf "Import DXF Data" im DXF Importer Tab
2. Wählen Sie die JSON-Datei aus
3. Konfigurieren Sie die Import-Einstellungen:
   - **Setup shared parameters**: Erstellt automatisch Shared Parameters für DXF-Daten
   - **Skip parameter setup**: Überspringt die Parameter-Erstellung
4. Klicken Sie "OK" um den Import zu starten

## Verzeichnisstruktur

```
DxfImporter.extension/
├── __init__.py                     # Extension Metadaten
├── README.md                       # Diese Dokumentation
├── DxfImporter.tab/               # Ribbon Tab
│   ├── bundle.yaml                # Tab Konfiguration
│   └── Import.panel/              # Ribbon Panel
│       ├── bundle.yaml            # Panel Konfiguration
│       └── Import DXF Data.pushbutton/  # Hauptbutton
│           ├── bundle.yaml        # Button Konfiguration
│           └── script.py          # Hauptskript
└── lib/                           # Bibliotheks-Module
    ├── __init__.py                # Modul Initialisierung
    ├── data_models.py             # JSON Datenmodelle
    ├── revit_creator.py           # Revit Element Erstellung
    └── parameter_manager.py       # Parameter Management
```

## Konfiguration

### Family Mapping

Die Extension verwendet ein konfigurierbares Family-Mapping in `script.py`:

```python
family_mapping = {
    "WATER_SPECIAL": {
        "family_name": "Generic Model",
        "type_name": "Water Special",
        "category": "OST_GenericModel",
    },
    "WATER_PIPE": {
        "family_name": "Generic Model", 
        "type_name": "Water Pipe",
        "category": "OST_GenericModel",
    },
    "SHAFT": {
        "family_name": "Generic Model",
        "type_name": "Shaft", 
        "category": "OST_GenericModel",
    },
}
```

### Standard Parameter

Die Extension erstellt automatisch folgende Shared Parameters:

- **DXF_ObjectType**: Original DXF Objekttyp
- **DXF_LayerName**: Original DXF Layer-Name  
- **DXF_PointCount**: Anzahl der Punkte in der ursprünglichen Geometrie
- **DXF_Diameter/Radius/Width/Height**: Elementdimensionen
- **DXF_CenterX/Y/Z**: Zentrumskoordinaten
- **DXF_ImportDate**: Import-Datum

## Troubleshooting

### Häufige Probleme

1. **"No active Revit document found"**
   - Stellen Sie sicher, dass ein Revit-Projekt geöffnet ist

2. **"No file selected"**
   - Wählen Sie eine gültige JSON-Datei aus

3. **"Failed to create shared parameter group"**
   - Erstellen Sie eine Shared Parameter Datei in Revit
   - Oder wählen Sie "Skip parameter setup"

4. **"Family not found"**
   - Laden Sie die benötigten Families in das Projekt
   - Oder passen Sie das Family-Mapping an verfügbare Families an

### Debug-Informationen

Die Extension nutzt pyRevit's Output Window für detaillierte Fortschritts- und Fehlerinformationen. Öffnen Sie das Output Window über `pyRevit → Output` für detaillierte Logs.

## Technische Details

### IronPython Kompatibilität

- Verwendet `# type: (...) -> ...` Kommentare für Type Hints
- Kompatibel mit IronPython 2.7
- Keine externen Dependencies außer Revit API und pyRevit

### Performance

- Batch-Verarbeitung in 50er-Gruppen
- Transaktions-basierte Element-Erstellung
- Progress-Reporting über pyRevit UI

## Lizenz

Dieses Projekt ist Teil des dxfto-Packages und folgt dessen Lizenzbestimmungen.

## Support

Für Fragen und Support besuchen Sie das [dxfto Repository](https://github.com/your-repo/dxfto).