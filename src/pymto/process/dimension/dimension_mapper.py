#!/usr/bin/env python

import bisect
from dataclasses import dataclass

from pymto.config import Unit
from pymto.models import ObjectType


@dataclass
class DimensionStandard:
    """Domain-Model für Infrastruktur-Standardmaße"""

    name: str
    description: str
    dimensions: list[int]
    tolerance: float
    unit: Unit = Unit.MILLIMETER  # Standard-Einheit ist Millimeter


# Standard-Dimensionen für Infrastruktur
INFRASTRUCTURE_STANDARDS = {
    # SCHÄCHTE (Rund und eckig)
    ObjectType.SHAFT_ROUND: DimensionStandard(
        name="Schächte",
        description="Revisionsschächte, Kontrollschächte",
        tolerance=100,
        dimensions=[
            600,
            800,
            1000,
            1200,
            1500,
            2000,
            2500,
            3000,
        ],
    ),
    # ABWASSERLEITUNGEN
    ObjectType.PIPE: DimensionStandard(
        name="Abwasserleitungen",
        description="Schmutzwasser, Regenwasser, Mischwasser",
        tolerance=5,
        dimensions=[
            # Hausanschlüsse
            100,
            110,
            125,
            150,
            160,
            # Sammelleitungen
            200,
            225,
            250,
            300,
            350,
            400,
            450,
            500,
            # Hauptsammler
            600,
            700,
            800,
            900,
            1000,
            1100,
            1200,
            # Große Kanäle
            1400,
            1500,
            1600,
            1800,
            2000,
            2200,
            2400,
            2500,
            3000,
        ],
    ),
    # WASSERLEITUNGEN (Trinkwasser)
    ObjectType.PIPE: DimensionStandard(
        name="Wasserleitungen",
        description="Trinkwasserverteilung",
        tolerance=2,
        dimensions=[
            # Hausanschlüsse
            20,
            25,
            32,
            40,
            50,
            # Verteilnetz
            63,
            75,
            80,
            90,
            100,
            110,
            125,
            140,
            150,
            160,
            # Versorgungsleitungen
            200,
            225,
            250,
            280,
            300,
            315,
            350,
            400,
            450,
            500,
            # Transportleitungen
            600,
            630,
            700,
            800,
            900,
            1000,
            1200,
            1400,
            1600,
        ],
    ),
    # GASLEITUNGEN
    ObjectType.PIPE: DimensionStandard(
        name="Gasleitungen",
        description="Gasverteilungsnetze",
        tolerance=2,
        dimensions=[
            # Hausanschlüsse
            25,
            32,
            40,
            50,
            # Niederdrucknetz
            63,
            75,
            90,
            110,
            125,
            140,
            160,
            180,
            200,
            # Mittel-/Hochdrucknetz
            225,
            250,
            280,
            315,
            355,
            400,
            450,
            500,
            560,
            630,
        ],
    ),
    # KABELKANÄLE
    ObjectType.DUCT: DimensionStandard(
        name="Kabelkanäle",
        description="Elektro- und Telekommunikationskanäle",
        tolerance=5,
        dimensions=[
            # Einzelleerrohre
            40,
            50,
            63,
            75,
            90,
            110,
            125,
            140,
            160,
            # Kabelschutzrohre
            200,
            250,
            300,
            400,
            500,
            600,
            # Kabelkanäle (Breite bei rechteckigen)
            200,
            300,
            400,
            500,
            600,
            800,
            1000,
            1200,
        ],
    ),
}


class DimensionMapper:
    """
    Wie ein erfahrener Tiefbauingenieur, der sofort die richtige Norm-Dimension erkennt.
    Analogie: Ein Magnet-System mit verschiedenen 'Kraftfeldern' je nach Infrastruktur-Typ.
    """

    def __init__(self, standards: dict[ObjectType, DimensionStandard] | None = None):
        self.standards = standards or INFRASTRUCTURE_STANDARDS

    def snap_dimension(self, measured_value: float, infra_type: ObjectType) -> float:
        """Snappt zu nächster Standard-Dimension"""

        standard = self.standards.get(infra_type)
        if not standard:
            return measured_value
        dimensions = standard.dimensions
        if not dimensions:
            return measured_value

        # Finde nächstliegende Dimensionen
        pos = bisect.bisect_left(dimensions, measured_value)

        candidates = []
        if pos > 0:
            candidates.append(dimensions[pos - 1])
        if pos < len(dimensions):
            candidates.append(dimensions[pos])

        # Wähle nächstliegende
        best_match = min(candidates, key=lambda x: abs(x - measured_value))

        # Prüfe Toleranz
        if abs(best_match - measured_value) <= standard.tolerance:
            return best_match
        else:
            return measured_value  # Außerhalb Toleranz

    def round_dimension(self, value: float, round_to: int) -> float:
        """Rundet Dimension auf 5er-Schritte"""
        value_in_cm = value * 100
        value_in_cm = round(value_in_cm / round_to) * round_to
        return value_in_cm / 100
