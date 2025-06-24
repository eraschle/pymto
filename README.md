# DXFto - DXF Processing Tool for Revit Export

[![Python 3.13](https://img.shields.io/badge/python-3.13-blue.svg)](https://www.python.org/downloads/)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv)

Ein Python-Tool zur Verarbeitung von DXF-Dateien mit Rohrleitungen und Schächten für den Export nach Revit. Das Tool extrahiert Geometrieinformationen, gruppiert Elemente nach Medien und exportiert die Daten in ein Revit-kompatibles JSON-Format.

## Inhaltsverzeichnis

- [Features](#features)
- [Installation](#installation)
- [Entwicklersetup](#entwicklersetup)
- [Verwendung](#verwendung)
  - [Grundlegende Verwendung](#grundlegende-verwendung)
  - [Erweiterte Optionen](#erweiterte-optionen)
  - [Konfigurationsdateien](#konfigurationsdateien)
- [Projektstruktur](#projektstruktur)
- [Entwicklung](#entwicklung)
- [Architektur](#architektur)
- [Beispiele](#beispiele)
- [API Dokumentation](#api-dokumentation)
- [Detaillierte API Referenz](docs/API.md)

## Features

- **DXF-Dateien verarbeiten**: Extraktion von Rohrleitungen, Schächten und Textelementen
- **LandXML-Integration**: Höhenangaben aus DGM-Daten übernehmen
- **Flexible Gruppierung**: Layer-basiert oder farbbasiert
- **Textzuordnung**: Räumliche oder zonenbasierte Zuordnung von Texten zu Rohrleitungen
- **Revit-Export**: JSON-Format optimiert für Revit-Import
- **CLI-Interface**: Benutzerfreundliche Kommandozeilen-Schnittstelle
- **Modulare Architektur**: SOLID-Prinzipien und austauschbare Strategien

## Installation

### Voraussetzungen

- Python 3.13 oder höher
- [uv](https://docs.astral.sh/uv/) Package Manager

### Installation mit uv

```bash
# Repository klonen
git clone <repository-url>
cd dxfto

# Dependencies installieren
uv sync

# Tool testen
uv run python -m dxfto.cli --help
```

### Alternative Installation (pip)

```bash
# Virtual Environment erstellen
python -m venv venv
source venv/bin/activate  # Linux/macOS
# oder
venv\Scripts\activate  # Windows

# Dependencies installieren
pip install -r requirements.txt
```

## Entwicklersetup

### Mit uv (empfohlen)

```bash
# Entwicklungsumgebung einrichten
uv sync --dev

# Code-Qualität Tools
uv run ruff check          # Linting
uv run ruff format         # Code-Formatierung
uv run isort .             # Import-Sortierung
uv run pyright            # Type-Checking

# Tests ausführen
uv run pytest             # Alle Tests
uv run pytest tests/      # Spezifisches Verzeichnis
uv run pytest -v          # Verbose Output
```

### Pre-commit Hooks (optional)

```bash
# Pre-commit installieren
uv add --dev pre-commit

# Hooks einrichten
uv run pre-commit install

# Manuell ausführen
uv run pre-commit run --all-files
```

## Verwendung

### Grundlegende Verwendung

```bash
# Einfache DXF-Verarbeitung
uv run python -m dxfto.cli input.dxf

# Mit Output-Datei spezifizieren
uv run python -m dxfto.cli input.dxf --output output.json

# Mit LandXML für Höhendaten
uv run python -m dxfto.cli input.dxf --landxml terrain.xml

# Verbose Output
uv run python -m dxfto.cli input.dxf --verbose
```

### Erweiterte Optionen

```bash
# Layer-basierte Gruppierung mit Konfigurationsdatei
uv run python -m dxfto.cli input.dxf \
  --grouping layer \
  --config config.json

# Farbbasierte Gruppierung mit Toleranz
uv run python -m dxfto.cli input.dxf \
  --grouping color \
  --color-tolerance 25.0

# Zonbasierte Textzuordnung
uv run python -m dxfto.cli input.dxf \
  --text-assignment zone \
  --max-text-distance 30.0

# Revit-spezifisches Format
uv run python -m dxfto.cli input.dxf \
  --revit-format \
  --output revit_export.json
```

### Konfigurationsdateien

#### Sample-Konfiguration erstellen

```bash
# Beispiel-Konfiguration generieren
uv run python -m dxfto.cli create-config sample_config.json
```

#### Konfigurationsformat

```json
{
  "Abwasserleitung": {
    "Leitung": {"Layer": "PIPE_SEWER", "Farbe": [255, 0, 0]},
    "Schacht": {"Layer": "SHAFT_SEWER", "Farbe": [200, 0, 0]},
    "Text": {"Layer": "TEXT_SEWER", "Farbe": [255, 100, 100]}
  },
  "Wasserleitung": {
    "Leitung": {"Layer": "PIPE_WATER", "Farbe": [0, 0, 255]},
    "Schacht": {"Layer": "SHAFT_WATER", "Farbe": [0, 0, 200]},
    "Text": {"Layer": "TEXT_WATER", "Farbe": [100, 100, 255]}
  }
}
```

## Projektstruktur

```
dxfto/
├── src/dxfto/              # Hauptanwendung
│   ├── __init__.py         # Package-Initialisierung
│   ├── cli.py              # → [CLI Interface](src/dxfto/cli.py)
│   ├── models.py           # → [Datenmodelle](src/dxfto/models.py)
│   ├── protocols.py        # → [Interface-Definitionen](src/dxfto/protocols.py)
│   ├── dxf_reader.py       # → [DXF-Verarbeitung](src/dxfto/dxf_reader.py)
│   ├── landxml_reader.py   # → [LandXML-Verarbeitung](src/dxfto/landxml_reader.py)
│   ├── groupers.py         # → [Gruppierungsstrategien](src/dxfto/groupers.py)
│   ├── text_assigners.py   # → [Textzuordnung](src/dxfto/text_assigners.py)
│   ├── json_exporter.py    # → [JSON-Export](src/dxfto/json_exporter.py)
│   └── main.py             # → [Haupteinstiegspunkt](src/dxfto/main.py)
├── tests/                  # → [Test-Suite](tests/)
├── docs/                   # Dokumentation
│   └── API.md              # → [API Dokumentation](docs/API.md)
├── specs/                  # Projektspezifikationen
│   └── task.md             # → [Anforderungen](specs/task.md)
├── pyproject.toml          # → [Projekt-Konfiguration](pyproject.toml)
├── CLAUDE.md               # → [Entwickler-Anweisungen](CLAUDE.md)
└── README.md               # Diese Datei
```

## Entwicklung

### Code-Qualität

Das Projekt verwendet moderne Python-Standards:

- **Type Hints**: Python 3.13 Union-Syntax (`str | None`)
- **Dataclasses**: Für strukturierte Datenmodelle
- **Protocols**: Für Interface-Definitionen
- **SOLID-Prinzipien**: Modulare, austauschbare Architektur

### Testing

```bash
# Alle Tests ausführen
uv run pytest

# Mit Coverage
uv run pytest --cov=src/dxfto

# Spezifische Tests
uv run pytest tests/test_dxf_reader.py -v
```

### Code-Formatierung

```bash
# Automatische Formatierung
uv run ruff format

# Linting mit Auto-Fix
uv run ruff check --fix

# Import-Sortierung
uv run isort .
```

## Architektur

### Kernkomponenten

1. **[DXF Reader](src/dxfto/dxf_reader.py)**: Extraktion von Geometrien aus DXF-Dateien
2. **[LandXML Reader](src/dxfto/landxml_reader.py)**: Höhendaten-Integration
3. **[Groupers](src/dxfto/groupers.py)**: Layer- und farbbasierte Gruppierung
4. **[Text Assigners](src/dxfto/text_assigners.py)**: Räumliche Textzuordnung
5. **[JSON Exporter](src/dxfto/json_exporter.py)**: Export für Revit

### Design Patterns

- **Strategy Pattern**: Austauschbare Gruppierungs- und Zuordnungsstrategien
- **Protocol Pattern**: Interface-Definitionen für Flexibilität
- **Factory Pattern**: Objekterstellung basierend auf Konfiguration

## Beispiele

### Vollständiges Beispiel

```bash
# Kompletttes Beispiel mit allen Features
uv run python -m dxfto.cli beispiel.dxf \
  --landxml gelaende.xml \
  --config medien_config.json \
  --grouping layer \
  --text-assignment zone \
  --max-text-distance 40.0 \
  --revit-format \
  --output projekt_export.json \
  --verbose
```

### Python API

```python
from pathlib import Path
from dxfto.dxf_reader import DXFReader
from dxfto.groupers import LayerBasedGrouper
from dxfto.json_exporter import RevitJSONExporter

# DXF laden
reader = DXFReader(Path("input.dxf"))
reader.load_file()

pipes = reader.extract_pipes()
shafts = reader.extract_shafts()
texts = reader.extract_texts()

# Gruppieren
grouper = LayerBasedGrouper(Path("config.json"))
grouper.load_config()
media = grouper.group_elements(pipes, shafts, texts)

# Exportieren
exporter = RevitJSONExporter(Path("output.json"))
exporter.export_media(media)
```

## API Dokumentation

### Hauptklassen

- **[DXFReader](src/dxfto/dxf_reader.py)**: DXF-Datei Verarbeitung
- **[LandXMLReader](src/dxfto/landxml_reader.py)**: Terrain-Daten Integration
- **[LayerBasedGrouper](src/dxfto/groupers.py)**: Layer-basierte Elementgruppierung
- **[ColorBasedGrouper](src/dxfto/groupers.py)**: Farbbasierte Elementgruppierung
- **[SpatialTextAssigner](src/dxfto/text_assigners.py)**: Räumliche Textzuordnung
- **[ZoneBasedTextAssigner](src/dxfto/text_assigners.py)**: Zonenbasierte Textzuordnung
- **[JSONExporter](src/dxfto/json_exporter.py)**: Standard JSON-Export
- **[RevitJSONExporter](src/dxfto/json_exporter.py)**: Revit-spezifischer Export

### Datenmodelle

Siehe [models.py](src/dxfto/models.py) für vollständige Definitionen:

- `Pipe`: Rohrleitung mit Geometrie und Eigenschaften
- `Shaft`: Schacht mit Position und Dimensionen
- `DXFText`: Textelement mit Position und Inhalt
- `Medium`: Gruppierung von zusammengehörigen Elementen

**Detaillierte API-Dokumentation**: [docs/API.md](docs/API.md)

## CLI Referenz

### Hauptkommando

```bash
uv run python -m dxfto.cli [OPTIONS] DXF_FILE
```

### Optionen

| Option | Beschreibung | Standard |
|--------|--------------|----------|
| `--landxml, -l` | LandXML-Datei für Höhenangaben | - |
| `--output, -o` | Output JSON-Datei | `{input}.json` |
| `--config, -c` | Konfigurationsdatei für Layer-Gruppierung | - |
| `--grouping` | Gruppierungsstrategie (`layer`/`color`) | `color` |
| `--text-assignment` | Textzuordnung (`spatial`/`zone`) | `spatial` |
| `--max-text-distance` | Max. Distanz für Textzuordnung | `50.0` |
| `--color-tolerance` | Farbtoleranz für Farbgruppierung | `30.0` |
| `--revit-format` | Revit-spezifisches JSON-Format | `False` |
| `--verbose, -v` | Detaillierte Ausgabe | `False` |

### Weitere Kommandos

```bash
# Beispiel-Konfiguration erstellen
uv run python -m dxfto.cli create-config config.json
```

## Spezialfälle und erweiterte Funktionen

### Block-Referenzen (INSERT Entities)

Das Tool unterstützt die Verarbeitung von DXF Block-Referenzen (INSERT Entities), die häufig für standardisierte Elemente wie Schächte verwendet werden.

#### Unterstützte Block-Typen

- **Runde Schächte**: Blocks mit "round", "circle" oder "rund" im Namen
- **Rechteckige Schächte**: Blocks mit "rect", "square" oder "eckig" im Namen
- **Generische Blocks**: Werden als runde Schächte mit Standardmaßen behandelt

#### Block-Verarbeitung

```bash
# DXF mit Block-Referenzen verarbeiten
uv run python -m dxfto.cli input_with_blocks.dxf --verbose
```

Das Tool:
1. **Erkennt INSERT Entities** automatisch als Elemente (nicht als Linien)
2. **Extrahiert Block-Geometrie** aus den Block-Definitionen
3. **Wendet Transformationen an** (Position, Maßstab, Rotation)
4. **Analysiert Block-Namen** für automatische Typ-Erkennung
5. **Erstellt punkt-basierte Elemente** mit Positions-Informationen

#### Block-Namenskonventionen

Für optimale Erkennung sollten Block-Namen beschreibende Begriffe enthalten:

```
# Runde Schächte
SCHACHT_RUND_600    → RoundDimensions(diameter=600.0)
ROUND_MANHOLE       → RoundDimensions(diameter=600.0)
KREIS_SCHACHT       → RoundDimensions(diameter=600.0)

# Rechteckige Schächte
SCHACHT_ECKIG_80x80 → RectangularDimensions(length=600.0, width=600.0)
RECT_SHAFT          → RectangularDimensions(length=600.0, width=600.0)
QUADRAT_SCHACHT     → RectangularDimensions(length=600.0, width=600.0)

# Unbekannte Blocks
CUSTOM_BLOCK        → RoundDimensions(diameter=800.0) # Fallback
```

### Kreis-Entities (CIRCLE)

Kreise werden automatisch als runde Schächte erkannt:

```python
# Automatische Konvertierung
CIRCLE Entity → ObjectData(
    shape=ShapeType.ROUND,
    dimensions=RoundDimensions(diameter=radius*2),
    positions=[center_point]
)
```

### Komplexe Polylinien

Polylinien mit 4 oder mehr Punkten werden als rechteckige Elemente klassifiziert:

```python
# Klassifizierung
POLYLINE mit >= 4 Punkten → Rechteckiges Element
POLYLINE mit < 4 Punkten  → Linien-Element
LINE Entity              → Linien-Element
```

### Element vs. Linien Klassifizierung

Das Tool unterscheidet automatisch zwischen:

| Entity Typ | Bedingung | Klassifizierung | Verarbeitung |
|------------|-----------|-----------------|-------------|
| INSERT | Immer | Element | Point-basiert |
| CIRCLE | Immer | Element | Point-basiert |
| POLYLINE | ≥4 Punkte | Element | Point-basiert |
| POLYLINE | <4 Punkte | Linie | Line-basiert |
| LINE | Immer | Linie | Line-basiert |

### Textzuordnung für verschiedene Element-Typen

#### Point-basierte Elemente (Schächte)
```python
# Zuordnung basiert auf Distanz zu Element-Position
distance = text_position.distance_2d(element.positions[0])
if distance <= max_distance:
    element.assigned_text = text
```

#### Line-basierte Elemente (Rohrleitungen)
```python
# Zuordnung basiert auf Distanz zu Liniensegmenten
for segment in element_segments:
    distance = point_to_line_distance(text_position, segment)
    if distance <= max_distance:
        element.assigned_text = text
```

### Konfiguration für spezielle Fälle

#### Block-spezifische Konfiguration

```json
{
  "Schachtmedium": {
    "Schacht": {
      "Layer": "SCHACHT_LAYER",
      "Farbe": [255, 0, 0],
      "BlockNamen": ["SCHACHT_*", "MANHOLE_*"]
    }
  }
}
```

#### Erweiterte Optionen

```bash
# Angepasste Distanzen für verschiedene Element-Typen
uv run python -m dxfto.cli input.dxf \
  --max-text-distance 30.0 \
  --zone-buffer 10.0        # Nur für ZoneBasedTextAssigner
```

### Debugging und Entwicklung

#### Block-Verarbeitung debuggen

```bash
# Verbose Mode für detaillierte Block-Informationen
uv run python -m dxfto.cli input.dxf --verbose 2>&1 | grep -i block
```

#### Logs analysieren

```python
import logging
logging.basicConfig(level=logging.DEBUG)

# Detaillierte Logs für:
# - Block-Definition-Extraktion
# - Geometrie-Transformation
# - Element-Klassifizierung
```

#### Neue Block-Typen hinzufügen

```python
# In _analyze_block_shape() erweitern:
block_name = insert_entity.dxf.name.lower()
if 'custom_type' in block_name:
    return ShapeType.ROUND, RoundDimensions(diameter=1000.0)
```

### Performance-Optimierung

- **Block-Definitionen werden gecacht** für mehrfache Verwendung
- **Geometrie-Extraktion erfolgt lazy** nur bei Bedarf
- **Transformation wird nur einmal berechnet** pro Block-Instanz

### Limitierungen

1. **Verschachtelte Blocks**: Werden derzeit nicht vollständig unterstützt
2. **Komplexe Transformationen**: Nur Translation implementiert (TODO: Scaling/Rotation)
3. **Attribut-Extraktion**: Vereinfacht implementiert
4. **3D-Geometrie**: Z-Koordinaten werden auf 0.0 gesetzt

## Troubleshooting

### Häufige Probleme

1. **DXF-Datei kann nicht gelesen werden**
   ```bash
   # Prüfen ob Datei existiert und gültig ist
   uv run python -c "import ezdxf; ezdxf.readfile('input.dxf')"
   ```

2. **LandXML-Verarbeitung fehlgeschlagen**
   ```bash
   # XML-Struktur prüfen
   xmllint --format terrain.xml | head -20
   ```

3. **Keine Elemente extrahiert**
   ```bash
   # Mit verbose Mode Details anzeigen
   uv run python -m dxfto.cli input.dxf --verbose
   ```

4. **Import-Fehler**
   ```bash
   # Dependencies neu installieren
   uv sync --reinstall-package dxfto
   ```

## Beitragen

1. Repository forken
2. Feature-Branch erstellen (`git checkout -b feature/amazing-feature`)
3. Änderungen committen (`git commit -m 'Add amazing feature'`)
4. Branch pushen (`git push origin feature/amazing-feature`)
5. Pull Request erstellen

### Development Workflow

```bash
# Setup
uv sync --dev

# Tests vor Commit
uv run pytest
uv run ruff check
uv run pyright

# Pre-commit hooks
uv run pre-commit run --all-files
```

## Lizenz

[Lizenz-Information hier einfügen]

## Kontakt & Support

- **Issues**: [Repository Issues](../../issues)
- **Dokumentation**: Diese README und [API-Dokumentation](docs/API.md)
- **Spezifikationen**: [Task Specifications](specs/task.md)
- **Entwickler-Setup**: [CLAUDE.md](CLAUDE.md)

## Changelog

### Version 1.0.0
- Initiale Implementierung
- DXF-Reader mit ezdxf
- LandXML-Integration
- Layer- und farbbasierte Gruppierung
- Räumliche Textzuordnung
- JSON-Export für Revit
- CLI-Interface mit Click
- Umfassende Test-Suite

---

*Entwickelt mit Python 3.13 und uv Package Manager*