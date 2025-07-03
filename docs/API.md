# API Dokumentation - pymto

Diese Dokumentation beschreibt die öffentlichen APIs und Schnittstellen der pymto-Bibliothek.

## Inhaltsverzeichnis

- [Kernmodule](#kernmodule)
  - [DXF Reader](#dxf-reader)
  - [LandXML Reader](#landxml-reader)
  - [Groupers](#groupers)
  - [Text Assigners](#text-assigners)
  - [JSON Exporter](#json-exporter)
- [Datenmodelle](#datenmodelle)
- [Protokolle](#protokolle)
- [Verwendungsbeispiele](#verwendungsbeispiele)

## Kernmodule

### DXF Reader

**Modul**: [`src/pymto/dxf_reader.py`](../src/pymto/dxf_reader.py)

Die `DXFReader`-Klasse verarbeitet DXF-Dateien und extrahiert Rohrleitungen, Schächte und Textelemente.

#### Klasse: DXFReader

```python
class DXFReader:
    def __init__(self, dxf_path: Path) -> None
    def load_file(self) -> None
    def extract_pipes(self) -> list[Pipe]
    def extract_shafts(self) -> list[Shaft]
    def extract_texts(self) -> list[DXFText]
```

**Beispiel:**
```python
from pathlib import Path
from pymto.dxf_reader import DXFReader

reader = DXFReader(Path("input.dxf"))
reader.load_file()

pipes = reader.extract_pipes()
shafts = reader.extract_shafts()
texts = reader.extract_texts()
```

**Exceptions:**
- `FileNotFoundError`: DXF-Datei nicht gefunden
- `ezdxf.DXFError`: DXF-Datei kann nicht gelesen werden
- `RuntimeError`: Datei nicht geladen (load_file() nicht aufgerufen)

### LandXML Reader

**Modul**: [`src/pymto/landxml_reader.py`](../src/pymto/landxml_reader.py)

Die `LandXMLReader`-Klasse verarbeitet LandXML-Dateien für Höhendaten-Integration.

#### Klasse: LandXMLReader

```python
class LandXMLReader:
    def __init__(self, landxml_path: Path) -> None
    def load_file(self) -> None
    def update_points_elevation(self, points: list[Point3D]) -> list[Point3D]
```

**Beispiel:**
```python
from pymto.landxml_reader import LandXMLReader

landxml_reader = LandXMLReader(Path("terrain.xml"))
landxml_reader.load_file()

# Höhendaten zu Punkten hinzufügen
updated_points = landxml_reader.update_points_elevation(pipe.points)
```

### Groupers

**Modul**: [`src/pymto/groupers.py`](../src/pymto/groupers.py)

Implementiert verschiedene Strategien zur Gruppierung von DXF-Elementen.

#### Klasse: LayerBasedGrouper

```python
class LayerBasedGrouper:
    def __init__(self, config_path: Path) -> None
    def load_config(self) -> None
    def group_elements(self, pipes: list[Pipe], shafts: list[Shaft], texts: list[DXFText]) -> list[Medium]
```

**Konfigurationsformat:**
```json
{
  "Medium_Name": {
    "Leitung": {"Layer": "LAYER_NAME", "Farbe": [255, 0, 0]},
    "Schacht": {"Layer": "SHAFT_LAYER", "Farbe": [200, 0, 0]},
    "Text": {"Layer": "TEXT_LAYER", "Farbe": [255, 100, 100]}
  }
}
```

#### Klasse: ColorBasedGrouper

```python
class ColorBasedGrouper:
    def __init__(self, color_tolerance: float = 30.0) -> None
    def group_elements(self, pipes: list[Pipe], shafts: list[Shaft], texts: list[DXFText]) -> list[Medium]
```

**Beispiel:**
```python
from pymto.groupers import ColorBasedGrouper, LayerBasedGrouper

# Farbbasierte Gruppierung
color_grouper = ColorBasedGrouper(color_tolerance=25.0)
media = color_grouper.group_elements(pipes, shafts, texts)

# Layer-basierte Gruppierung
layer_grouper = LayerBasedGrouper(Path("config.json"))
layer_grouper.load_config()
media = layer_grouper.group_elements(pipes, shafts, texts)
```

### Text Assigners

**Modul**: [`src/pymto/text_assigners.py`](../src/pymto/text_assigners.py)

Implementiert Strategien zur Zuordnung von Textelementen zu Rohrleitungen.

#### Klasse: SpatialTextAssigner

```python
class SpatialTextAssigner:
    def __init__(self, max_distance: float = 50.0) -> None
    def assign_texts_to_pipes(self, pipes: list[Pipe], texts: list[DXFText]) -> list[Pipe]
```

#### Klasse: ZoneBasedTextAssigner

```python
class ZoneBasedTextAssigner:
    def __init__(self, max_distance: float = 50.0, zone_buffer: float = 10.0) -> None
    def assign_texts_to_pipes(self, pipes: list[Pipe], texts: list[DXFText]) -> list[Pipe]
```

**Beispiel:**
```python
from pymto.text_assigners import SpatialTextAssigner, ZoneBasedTextAssigner

# Räumliche Zuordnung
spatial_assigner = SpatialTextAssigner(max_distance=40.0)
assigned_pipes = spatial_assigner.assign_texts_to_pipes(pipes, texts)

# Zonenbasierte Zuordnung
zone_assigner = ZoneBasedTextAssigner(max_distance=40.0, zone_buffer=15.0)
assigned_pipes = zone_assigner.assign_texts_to_pipes(pipes, texts)
```

### JSON Exporter

**Modul**: [`src/pymto/json_exporter.py`](../src/pymto/json_exporter.py)

Exportiert verarbeitete Daten in JSON-Format für Revit-Kompatibilität.

#### Klasse: JSONExporter

```python
class JSONExporter:
    def __init__(self, output_path: Path) -> None
    def export_media(self, media: list[Medium]) -> None
```

#### Klasse: RevitJSONExporter

```python
class RevitJSONExporter(JSONExporter):
    def export_media(self, media: list[Medium]) -> None
```

**Beispiel:**
```python
from pymto.json_exporter import JSONExporter, RevitJSONExporter

# Standard Export
exporter = JSONExporter(Path("output.json"))
exporter.export_media(media)

# Revit-spezifischer Export
revit_exporter = RevitJSONExporter(Path("revit_output.json"))
revit_exporter.export_media(media)
```

**Revit JSON-Format:**
```json
{
  "version": "1.0",
  "format": "revit_compatible",
  "units": "mm",
  "media": {
    "Medium_Name": {
      "pipes": [...],
      "shafts": [...],
      "metadata": {
        "pipe_count": 10,
        "shaft_count": 3,
        "text_count": 8
      }
    }
  }
}
```

## Datenmodelle

**Modul**: [`src/pymto/models.py`](../src/pymto/models.py)

### Point3D

```python
@dataclass
class Point3D:
    x: float
    y: float
    z: float
```

### Pipe

```python
@dataclass
class Pipe:
    shape: ShapeType
    points: list[Point3D]
    dimensions: RectangularDimensions | RoundDimensions
    layer: str
    color: tuple[int, int, int]
    assigned_text: DXFText | None = None
```

### Shaft

```python
@dataclass
class Shaft:
    shape: ShapeType
    position: Point3D
    dimensions: RectangularDimensions | RoundDimensions
    layer: str
    color: tuple[int, int, int]
```

### DXFText

```python
@dataclass
class DXFText:
    content: str
    position: Point3D
    layer: str
    color: tuple[int, int, int]
```

### Medium

```python
@dataclass
class Medium:
    name: str
    pipes: list[Pipe]
    shafts: list[Shaft]
    texts: list[DXFText]
```

### Dimensionen

```python
@dataclass
class RoundDimensions:
    diameter: float
    height: float | None = None

@dataclass
class RectangularDimensions:
    length: float
    width: float
    angle: float
    height: float | None = None
```

### Enumerationen

```python
class ShapeType(Enum):
    ROUND = "round"
    RECTANGULAR = "rectangular"
```

## Protokolle

**Modul**: [`src/pymto/protocols.py`](../src/pymto/protocols.py)

### GroupingStrategy

```python
@runtime_checkable
class GroupingStrategy(Protocol):
    def group_elements(self, pipes: list[Pipe], shafts: list[Shaft], texts: list[DXFText]) -> list[Medium]:
        ...
```

### TextAssignmentStrategy

```python
@runtime_checkable
class TextAssignmentStrategy(Protocol):
    def assign_texts_to_pipes(self, pipes: list[Pipe], texts: list[DXFText]) -> list[Pipe]:
        ...
```

## Verwendungsbeispiele

### Vollständige Verarbeitungspipeline

```python
from pathlib import Path
from pymto.dxf_reader import DXFReader
from pymto.landxml_reader import LandXMLReader
from pymto.groupers import LayerBasedGrouper
from pymto.text_assigners import SpatialTextAssigner
from pymto.json_exporter import RevitJSONExporter

# 1. DXF-Datei laden
dxf_reader = DXFReader(Path("input.dxf"))
dxf_reader.load_file()

pipes = dxf_reader.extract_pipes()
shafts = dxf_reader.extract_shafts()
texts = dxf_reader.extract_texts()

# 2. Höhendaten integrieren (optional)
landxml_reader = LandXMLReader(Path("terrain.xml"))
landxml_reader.load_file()

for pipe in pipes:
    pipe.points = landxml_reader.update_points_elevation(pipe.points)

for shaft in shafts:
    shaft.position = landxml_reader.update_points_elevation([shaft.position])[0]

# 3. Elemente gruppieren
grouper = LayerBasedGrouper(Path("config.json"))
grouper.load_config()
media = grouper.group_elements(pipes, shafts, texts)

# 4. Texte zuordnen
text_assigner = SpatialTextAssigner(max_distance=50.0)
for medium in media:
    medium.pipes = text_assigner.assign_texts_to_pipes(medium.pipes, medium.texts)

# 5. Exportieren
exporter = RevitJSONExporter(Path("output.json"))
exporter.export_media(media)
```

### Custom Grouping Strategy

```python
from pymto.protocols import GroupingStrategy
from pymto.models import Medium, Pipe, Shaft, DXFText

class CustomGrouper:
    def group_elements(self, pipes: list[Pipe], shafts: list[Shaft], texts: list[DXFText]) -> list[Medium]:
        # Custom grouping logic here
        return [Medium(name="Custom", pipes=pipes, shafts=shafts, texts=texts)]

# Usage
grouper = CustomGrouper()
media = grouper.group_elements(pipes, shafts, texts)
```

### Error Handling

```python
try:
    dxf_reader = DXFReader(Path("input.dxf"))
    dxf_reader.load_file()
except FileNotFoundError:
    print("DXF file not found")
except ezdxf.DXFError as e:
    print(f"DXF parsing error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

---

[← Zurück zur README](../README.md)
