# ObjectData Factory - Code Impact Analysis

## Übersicht

Die neue ObjectData Factory vereinfacht und verbessert die Erstellung von ObjectData-Instanzen aus DXF-Entitäten erheblich. Diese Dokumentation beschreibt die Auswirkungen auf den bestehenden Code und empfohlene Änderungen.

## Neue Module

### 1. `pymto/process/entity_handler.py`

- **Zweck**: Funktionen zur Analyse und Klassifizierung von DXF-Entitäten
- **Hauptfunktionen**:
  - `is_element_entity()`: Bestimmt, ob eine Entität als Element oder Linie verarbeitet werden soll
  - `detect_shape_type()`: Erkennt Geometrietyp (rechteckig, rund, mehrseitig)
  - `is_rectangular_shape()`: Prüft, ob 4 Punkte ein Rechteck bilden
  - `is_near_circular_shape()`: Erkennt annähernd kreisförmige Polygone
  - `has_diagonal_cross()`: Erkennt diagonale Kreuzlinien in Verteilern
  - Verschiedene Berechnungsfunktionen für Dimensionen und Mittelpunkte

### 2. `pymto/process/objectdata_factory.py`

- **Zweck**: Factory-Pattern für ObjectData-Erstellung
- **Hauptklasse**: `ObjectDataFactory`
- **Unterstützte Entitätstypen**:
  - `INSERT` (Blöcke): Schächte als Blockreferenzen
  - `CIRCLE`: Runde Schächte
  - `POLYLINE/LWPOLYLINE`: Rechteckige Schächte, Verteiler, komplexe Formen
  - `LINE`: Leitungssegmente

## Auswirkungen auf bestehenden Code

### 1. `pymto/io/dxf_reader.py`

#### Aktueller Zustand

- Enthält bereits ähnliche Funktionalität, aber weniger strukturiert
- Gemischte Verantwortlichkeiten in einer Klasse
- Teilweise inkonsistente Geometrieerkennung

#### Empfohlene Änderungen

```python
# Alte Implementierung ersetzen
class DXFReader:
    def __init__(self, dxf_path: Path) -> None:
        self.dxf_path = dxf_path
        self._doc: Drawing | None = None
        self._factory: ObjectDataFactory | None = None  # NEU

    def load_file(self) -> None:
        # Bestehende Logik
        if not self.dxf_path.exists():
            raise FileNotFoundError(f"DXF file not found: {self.dxf_path}")

        try:
            self._doc = ezdxf.readfile(str(self.dxf_path))
            self._factory = ObjectDataFactory(self._doc)  # NEU
        except DXFError as e:
            raise DXFError(f"Cannot read DXF file {self.dxf_path}: {e}") from e

    def _extract_elements(self, config: AssignmentConfig) -> list[ObjectData]:
        """Vereinfachte Implementierung mit Factory."""
        if self._factory is None:
            raise RuntimeError("DXF file not loaded. Call load_file() first.")

        elements = []
        for entity in self._query_modelspace(config.geometry):
            # Verwende Factory für Klassifizierung
            if not self._factory.should_process_as_element(entity):
                continue

            # Verwende Factory für ObjectData-Erstellung
            element = self._factory.create_from_entity(entity)
            if element is None:
                log.error(f"Failed to create object from entity: {entity.dxftype()}")
                continue
            elements.append(element)
        return elements
```

#### Zu entfernende Methoden

Diese Methoden können entfernt werden, da sie von der Factory übernommen werden:

- `_should_process_as_element()`
- `_create_element_from_entity()`
- `_create_object_from_insert()`
- `_create_round_from()`
- `_create_rectangular_from()`
- `_is_rectangular_shape()`
- `_get_bbox_dimension()`
- `_get_rect_dimension()`
- `_get_rectangular_dimension()`
- `_get_rectangular_center()`
- `_extract_block_points()`
- `_apply_block_transformation()`
- `_analyze_block_shape()`

### 2. Verbesserte Unterstützung für verschiedene Schachttypen

#### Runde Schächte

- **Einfache Kreise**: Automatische Durchmessererkennung
- **Blöcke mit Kreisen**: Erkennung des größten Kreises als Außendurchmesser
- **Doppelkreis-Schächte**: Äußerer Kreis wird als maßgebend betrachtet

#### Rechteckige Verteiler

- **4-Eck-Geometrie**: Präzise Längen-/Breitenberechnung
- **Mit Diagonalkreuz**: Erkennung von Kreuzlinien (implementiert aber nicht vollständig genutzt)
- **Begrenzungsrahmen**: Fallback für komplexe Formen

#### Mehrseitige Elemente

- **Polygone >4 Ecken**: Automatische Erkennung
- **Annähernd runde Formen**: Polygone mit vielen Seiten werden als rund behandelt
- **Unregelmäßige Formen**: Begrenzungsrahmen-Dimensionen

### 3. `pymto/models.py`

#### Mögliche Erweiterungen

```python
@dataclass
class ShapeAnalysis:
    """Erweiterte Forminformationen für komplexe Geometrien."""
    shape_type: str  # 'rectangular', 'round', 'multi_sided', 'linear'
    complexity: int  # Anzahl der Eckpunkte
    has_cross_pattern: bool  # Enthält Diagonalkreuz
    regularity_score: float  # 0-1, wie regelmäßig die Form ist

@dataclass
class ObjectData:
    # Bestehende Felder...
    shape_analysis: ShapeAnalysis | None = None  # NEU: Erweiterte Formanalyse
```

### 4. Performance-Verbesserungen

#### Block-Caching

Die Factory implementiert Caching für Blockdefinitionen:

```python
class ObjectDataFactory:
    def __init__(self, dxf_document: Drawing):
        self.doc = dxf_document
        self._block_cache = {}  # Cache für Blockdefinitionen
```

#### Parallele Verarbeitung (zukünftig)

Die modulare Struktur ermöglicht einfache Parallelisierung:

```python
from concurrent.futures import ThreadPoolExecutor

def process_entities_parallel(entities: List[DXFEntity], factory: ObjectDataFactory):
    with ThreadPoolExecutor() as executor:
        results = list(executor.map(factory.create_from_entity, entities))
    return [r for r in results if r is not None]
```

## Migration Strategy

### Phase 1: Integration der Factory

1. Neue Module `entity_handler.py` und `objectdata_factory.py` hinzufügen
2. `DXFReader` um Factory-Unterstützung erweitern
3. Tests für neue Funktionalität

### Phase 2: Code-Bereinigung

1. Alte Methoden in `DXFReader` entfernen
2. Duplicate Code eliminieren
3. Bestehende Tests anpassen

### Phase 3: Erweiterte Features

1. Vollständige Unterstützung für Diagonalkreuz-Erkennung
2. Erweiterte Transformationen für Blöcke (Skalierung, Rotation)
3. Zusätzliche Geometrietypen

## Vorteile der neuen Architektur

### 1. Separation of Concerns

- **Entity Handler**: Reine Geometrieanalyse
- **Factory**: ObjectData-Erstellung
- **DXF Reader**: Koordination und Dateiverarbeitung

### 2. Erweiterbarkeit

- Neue Entitätstypen können einfach hinzugefügt werden
- Modulare Funktionen ermöglichen granulare Tests
- Factory-Pattern erlaubt verschiedene Erstellungsstrategien

### 3. Wartbarkeit

- Klare Verantwortlichkeiten
- Weniger Code-Duplizierung
- Bessere Testbarkeit

### 4. Robustheit

- Umfassende Fehlerbehandlung
- Fallback-Mechanismen für unbekannte Geometrien
- Logging für Debugging

## Potenzielle Risiken

### 1. Breaking Changes

- Bestehende Tests müssen angepasst werden
- API-Änderungen in `DXFReader`

### 2. Performance

- Zusätzliche Indirektion durch Factory
- Möglicher Memory-Overhead durch Caching

### 3. Komplexität

- Mehr Module zu verwalten
- Abhängigkeiten zwischen Modulen

## Empfohlene nächste Schritte

[ ] **Tests erweitern**: Umfassende Tests für alle Geometrietypen
[ ] **Integration testen**: Mit realen DXF-Dateien testen
[ ] **Performance messen**: Benchmarks vor und nach Migration
[ ] **Dokumentation**: API-Dokumentation für neue Module
[ ] **Graduelle Migration**: Schrittweise Umstellung ohne Breaking Changes
