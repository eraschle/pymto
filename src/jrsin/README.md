# jrsin - JSON Revit Import Package

Eine vereinfachte PyRevit Extension zum Importieren von DXF-Daten aus JSON-Dateien in Autodesk Revit, kompatibel mit IronPython 3.

## Übersicht

Die `jrsin` Extension liest JSON-Daten aus der `revit_data.json` Datei und erstellt entsprechende Revit-Elemente als Generic Models.

## Funktionen

- **IronPython 3 Kompatibilität**: Vollständig kompatibel mit pyRevit
- **Einfache Implementierung**: Minimaler Code ohne komplexe Klassenhierarchien
- **Automatische Elementerstellung**: Erstellt Generic Model Instanzen an den angegebenen Koordinaten
- **Parameter-Support**: Setzt Parameter aus JSON-Daten auf erstellte Elemente

## Struktur

```
src/jrsin/DxfImporter.extension/
├── DxfImporter.tab/
│   └── Import.panel/
│       └── Import DXF Data.pushbutton/
│           ├── bundle.yaml
│           └── script.py              # Hauptskript (vereinfacht)
├── README.md                          # Diese Dokumentation  
└── __init__.py                        # Extension Initialisierung
```

## Installation und Verwendung

### 1. Installation

Die Extension ist bereits als pyRevit Extension strukturiert:

1. Die Extension wird automatisch von pyRevit erkannt
2. Starten Sie Revit neu, um die Extension zu laden
3. Das "Import DXF Data" Button erscheint im DxfImporter Tab

### 2. Verwendung

1. Öffnen Sie ein Revit-Projekt
2. Stellen Sie sicher, dass mindestens eine Generic Model Family geladen ist
3. Klicken Sie auf "Import DXF Data" 
4. Wählen Sie die `revit_data.json` Datei aus
5. Die Elemente werden automatisch importiert

## JSON-Datenformat

Die Extension erwartet folgendes JSON-Format:

```json
{
  "Kategorie Name": [
    {
      "object_type": "WATER_SPECIAL",
      "family": "family_name", 
      "family_type": "type_name",
      "dimensions": {
        "radius": 100.0,
        "diameter": 200.0
      },
      "line_points": [
        {
          "east": 2810860.018,
          "north": 1184014.392, 
          "altitude": 1440.609
        }
      ],
      "parameters": [
        {
          "name": "Durchmesser",
          "value": 200.0,
          "value_type": "float",
          "unit": "m"
        }
      ]
    }
  ]
}
```

## Implementierung

Die Extension verwendet eine einfache Klasse `SimpleRevitImporter`:

### Hauptfunktionen

- `load_json_data()`: Lädt JSON-Daten
- `get_generic_family_symbol()`: Findet Generic Model Family
- `create_xyz_from_point()`: Konvertiert Koordinaten zu Revit XYZ
- `create_element()`: Erstellt Revit-Element
- `import_data()`: Importiert alle Daten

### Koordinaten-Konvertierung

- East/North/Altitude werden von Metern zu Revit-internen Einheiten konvertiert
- Verwendet `UnitUtils.ConvertToInternalUnits()` mit `UnitTypeId.Meters`

### Parameter-Handling

- Versucht numerische Werte als `float` zu setzen
- Fallback auf `string` wenn numerische Konvertierung fehlschlägt
- Ignoriert schreibgeschützte Parameter

## Vereinfachungen gegenüber der alten Version

1. **Keine komplexen Datenmodelle**: Arbeitet direkt mit JSON-Dictionaries
2. **Keine Typ-Erstellung**: Verwendet vorhandene Generic Model Families
3. **Keine Shared Parameter**: Setzt nur vorhandene Parameter
4. **Keine Batch-Verarbeitung**: Alle Elemente in einer Transaktion
5. **Keine fehlerhafte Transaktions-Verschachtelung**: Einfache Transaction-Verwendung

## Fehlerbehandlung

- Überprüft auf aktives Revit-Dokument
- Validiert JSON-Dateiauswahl
- Überprüft Verfügbarkeit von Generic Model Families
- Try-catch für Parameter-Setzen

## Kompatibilität

- **IronPython 3** (pyRevit)
- **Revit 2019+** 
- **Windows** Betriebssystem
- **pyRevit** Framework

## Troubleshooting

### Häufige Probleme

1. **"No Generic Model family found"**
   - Laden Sie eine Generic Model Family in das Projekt

2. **"No file selected"**
   - Stellen Sie sicher, dass die JSON-Datei existiert und zugänglich ist

3. **Elemente werden nicht erstellt**
   - Überprüfen Sie das JSON-Format
   - Stellen Sie sicher, dass `line_points` nicht leer ist

4. **Parameter werden nicht gesetzt**
   - Parameter müssen bereits in der Family definiert sein
   - Extension erstellt keine neuen Parameter

## Entwicklung

Die Extension ist bewusst einfach gehalten:
- Ein einzelnes Script-File
- Minimale Klassenhierarchie
- Direkte JSON-Verarbeitung
- Standard pyRevit-Patterns