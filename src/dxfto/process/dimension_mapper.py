#!/usr/bin/env python

import bisect
from dataclasses import dataclass

from dxfto.models import ObjectType


@dataclass
class DimensionStandard:
    """Domain-Model für Infrastruktur-Standardmaße"""

    name: str
    description: str
    dimensions: list[int]
    tolerance_factor: float = 0.10  # 10% Standard-Toleranz


# Standard-Dimensionen für Infrastruktur
INFRASTRUCTURE_STANDARDS = {
    # SCHÄCHTE (Rund und eckig)
    ObjectType.SHAFT: DimensionStandard(
        name="Schächte",
        description="Revisionsschächte, Kontrollschächte",
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
        tolerance_factor=0.05,  # Schächte haben engere Toleranzen
    ),
    # ABWASSERLEITUNGEN
    ObjectType.PIPE_WASTEWATER: DimensionStandard(
        name="Abwasserleitungen",
        description="Schmutzwasser, Regenwasser, Mischwasser",
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
    ObjectType.PIPE_WATER: DimensionStandard(
        name="Wasserleitungen",
        description="Trinkwasserverteilung",
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
    ObjectType.PIPE_GAS: DimensionStandard(
        name="Gasleitungen",
        description="Gasverteilungsnetze",
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
        tolerance_factor=0.05,  # Gas hat engere Toleranzen
    ),
    # KABELKANÄLE
    ObjectType.CABLE_DUCT: DimensionStandard(
        name="Kabelkanäle",
        description="Elektro- und Telekommunikationskanäle",
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
        max_deviation = best_match * standard.tolerance_factor
        if abs(best_match - measured_value) <= max_deviation:
            return best_match
        else:
            return measured_value  # Außerhalb Toleranz

    def round_dimension(self, value: float) -> float:
        """Rundet Dimension auf 5er-Schritte"""
        value_in_cm = value * 100
        value_in_cm = round(value_in_cm / 5) * 5
        return value_in_cm / 100
