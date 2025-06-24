# TASK

Die Leitungen und Schächte aus einer DXF Datei prozessieren und die Daten zum Modellieren der Leitungen und Schächte in einem Revit Modell verwenden.

Prozessierung:

1. DXF Datei importieren
2. LandXML Datei (DGM) importieren
3. Geometrie der Leitungen, Schächte und Texten verarbeiten
4. Gruppieren der DXF Objekte (Leitungen, Schächte, Text) pro Medium
   - Anhand Farben: Gleiche Medien haben den gleichen Farbton (rot, blau, ...)
   - Anhand User Angaben: CLI Argumente mit JSON Datei im folgenden Format
     { 
        "Abwasserleitung": {
          "Leitung": {
            "Layer": <LayerLeitung>,
            "Farbe": <RGB> (OPTIONAL)
          },
          "Schacht": {
            "Layer": <LayerLeitung>,
            "Farbe": <RGB> (OPTIONAL)
          },
          "Text": {
            "Layer": <LayerLeitung>,
            "Farbe": <RGB> (OPTIONAL)
          }
        },
        "<Anderes_Medium>": {
          "Leitung": {
            ...
          },
          "Schacht": {
            ...
          },
          "Text": {
            ...
          },
        }
     }
4. Zuordnung von Texten zu den Leitungen.
   - Texte enthalten die Dimensionen von Leitungen und Kabelkanälen. 
   - CLI Argumente haben eine höhere Priorität als die automatische farbliche Zuordnung
   - Räumliche Zuordung von Texten zu Leitungen pro Gruppe von DXF Elemente.
     - Die Zuordnung von einem Text pro Leitung ist Optional
     - Gültigkeit einer Zuordnung ist zwischen Schächten oder Abzweigungen
5. Export der Daten in JSON Dateien:
   {
     "Medium": [
       {
         "Informationen pro Element"
       }
     ]
   }

## Schächte

Die folgenden Daten werden für die Schächte benötigt:

- Form (Rechteckig, Rund)
- Position (X, Y, Z)
  - X / Y Koordinaten aus der DXF Datei
  - Z Koordinate aus LandXML Datei (DGM)
- Dimensionen
  - Rechteckig
    - Länge
    - Breite
    - Winkel
    - Höhe (OPTIONAL)
  - Rund
    - Durchmesser
    - Höhe (OPTIONAL)
- Layernamen

## Leitungen

Die folgenden Daten werden für die Leitungen benötigt:

- Form (Rechteckig, Rund)
- Position (X, Y, Z) aller Punkte der DXF Geometrie
  - X / Y Koordinaten aus der DXF Datei
  - Z Koordinate aus LandXML Datei (DGM)
- Dimensionen
  - Rechteckig
    - Breite
    - Höhe (OPTIONAL)
  - Rund
    - Durchmesser

## Dependencies

Für die verwandten Python-Packate und deren Installation wird `uv` verwendet.
In der *pyprojekt.toml* werden die Abhängigkeiten aufgelistet. 
Zudem sollen in dieser Datei auch die Konfigurationen für ruff (FORMATTER) und pyright (TYPE CHECKER) hinterlegt werden.

Das Skript soll in Python geschrieben werden und die folgenden Bibliotheken verwenden:

- `ezdxf` zum Lesen der DXF Datei (mozman/ezdxf)
- `lxml` zum Lesen der LandXML Datei (lxml/lxml)
- `json` zum Exportieren der Daten in JSON Dateien
- `numpy` für mathematische Operationen (numpy/numpy)
- `scipy.spatial` für räumliche Nähe und Zuordnung von Texten zu Leitungen (scipy/scipy)
- `click` für die Kommandozeilen-Schnittstelle und Ausgaben (pallets/click)

- Wenn Zufriff auf MCP Server von Context7 vorhanden ist, dann kann die Dokumentation der Bibliotheken anhand 
  der ID in Klammer bei den Angaben zu den verwendeten Packages entnommen werden.
- Verwende den python 3.13 Syntax: Also *list anstatt List*, *dict anstatt Dict*, usw.
- Python docstring sollen in englisch geschrieben werden und das *NumPy style docstrings* verwenden

## Anforderungen

- Das Programm soll modular aufgebaut und anhand sein von Ordnern strukturiert werden. 
- Grundlegende Angaben für das Programm sollen über CLI Argument und Optionen verändert werden können.
- Code Grundlagen wie SOLID und das Anwenden von geeigneten Pattern sind ein muss
  - Protocol zum Austauschen der Logik für Gruppierung und Zuordnung
- Die Daten und Logik sollen in separaten Modulen und Klassen (dataclass oder pydantic) organisiert werden. 
- Die Logik zur Verarbeitung der DXF wie zum Beispiel 
  - Zuordnen von Texten zu Leitungen 
  - Gruppieren von Geometrien soll austauschbar sein.  
    Zu Implementieren ist:
    - Gruppierung anhand der Angaben pro Medium und deren Layername 
    - Gruppierung anhand dem gleichen Farbton von Leitungen, Schächten und Text
      - Zum Beispiel: 
        Gruppieren von:
        - Schachte in Dunkelblau, Leitungen in Blau und Text in Hellblau.
        - Schachte in Dunkelorange, Leitungen in Rot und Text in Orange.
    Logik soll durch eine gut gewählte Architektur einfach auszutauschen sein

## Erstellung

Bei der Erstellung soll das Framework *TDD* angewendet werden.
Für die Tests soll `pytest` verwendet werden. Die Tests sollen in einem separaten Verzeichnis `tests/` und die gleichen Struktur wie der Code aufweisen.
Unit Test alle Bereiche des Programm abdecken, jedoch im Speziellenn die Zuordung und Gruppierung ausführlicher.
Beim Schreiben der Test soll möglichst auf MOCK Objekte verzichtet werden und stattdessen mit Beispiel Daten gearbeitet werden.
