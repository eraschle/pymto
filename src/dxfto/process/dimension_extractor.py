"""Dimension extraction utilities for parsing dimension information from text.

This module provides functions to extract dimensional information from text strings,
supporting both round (circular) and rectangular dimensions with various formats
and unit specifications.
"""

import re


def extract_round(text: str) -> tuple[float, str | None] | None:
    """Extract round dimension from text.

    Parameters
    ----------
    text : str
        Text to extract dimension from

    Returns
    -------
    tuple[float, str | None] | None
        Extracted (diameter_value, unit) or None if not found
        Unit can be 'mm', 'cm', 'm' or None if no unit specified
    """
    text_clean = text.strip().upper()

    # Pattern für runde Dimensionen mit optionalen Zeichen und Einheiten
    patterns = [
        r"[ØøΦφ]\s*(\d+(?:[.,]\d+)?)\s*(mm|cm|m)?",  # Ø123mm, ø123, Φ123cm, φ123
        r"DN\s*(\d+(?:[.,]\d+)?)\s*(mm|cm|m)?",  # DN123, DN123mm
        r"D\s*(\d+(?:[.,]\d+)?)\s*(mm|cm|m)?",  # D123, D123cm
        r"^(\d+(?:[.,]\d+)?)\s*(mm|cm|m)?$",  # 123mm, 123, 123cm
    ]

    for pattern in patterns:
        match_result = re.search(pattern, text_clean, re.IGNORECASE)
        if match_result:
            try:
                diameter_str = match_result.group(1).replace(",", ".")
                unit = match_result.group(2).lower() if match_result.group(2) else None

                # Zusätzliche Validierung: Stelle sicher, dass es eine gültige Zahl ist
                if diameter_str.startswith(".") or diameter_str.endswith("."):
                    continue

                diameter = float(diameter_str)
                return (diameter, unit)
            except ValueError:
                continue
    return None


def extract_rectangular(text: str) -> tuple[tuple[float, float], str | None] | None:
    """Extract rectangular dimensions from text.

    Parameters
    ----------
    text : str
        Text to extract dimensions from

    Returns
    -------
    tuple[tuple[float, float], str | None] | None
        Extracted ((width, height), unit) or None if not found
        Unit can be 'mm', 'cm', 'm' or None if no unit specified
    """
    text_clean = text.strip()

    # Pattern für rechteckige Dimensionen mit verschiedenen Trennzeichen und Einheiten
    patterns = [
        r"(\d+(?:[.,]\d+)?)\s*x\s*(\d+(?:[.,]\d+)?)\s*(mm|cm|m)?",  # 100x200mm
        r"(\d+(?:[.,]\d+)?)\s*×\s*(\d+(?:[.,]\d+)?)\s*(mm|cm|m)?",  # 100×200cm
        r"(\d+(?:[.,]\d+)?)\s*,\s*(\d+(?:[.,]\d+)?)\s*(mm|cm|m)?",  # 100,200m
        r"(\d+(?:[.,]\d+)?)\s*\*\s*(\d+(?:[.,]\d+)?)\s*(mm|cm|m)?",  # 100*200mm
        r"(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)\s*(mm|cm|m)?",  # 100/200cm
    ]

    for pattern in patterns:
        match_result = re.search(pattern, text_clean, re.IGNORECASE)
        if match_result:
            try:
                width_str = match_result.group(1).replace(",", ".")
                height_str = match_result.group(2).replace(",", ".")
                unit = match_result.group(3).lower() if match_result.group(3) else None

                # Zusätzliche Validierung: Stelle sicher, dass es gültige Zahlen sind
                if (
                    width_str.startswith(".")
                    or width_str.endswith(".")
                    or height_str.startswith(".")
                    or height_str.endswith(".")
                ):
                    continue

                width = float(width_str)
                height = float(height_str)

                return ((width, height), unit)
            except ValueError:
                continue

    return None


def convert_to_unit(value: float, unit: str | None, target_unit: str = "mm") -> float:
    """Convert dimension value to standard unit.

    Parameters
    ----------
    value : float
        The dimension value to convert
    unit : str | None
        The current unit ('mm', 'cm', 'm') or None
    target_unit : str, default 'mm'
        The target unit to convert to

    Returns
    -------
    float
        Converted value in target unit
    """
    if unit is None:
        # Assume mm if no unit specified
        unit = "mm"

    # Conversion factors to mm
    to_mm = {"mm": 1.0, "cm": 10.0, "m": 1000.0}

    # Conversion factors from mm
    from_mm = {"mm": 1.0, "cm": 0.1, "m": 0.001}

    # Convert to mm first, then to target unit
    value_in_mm = value * to_mm.get(unit.lower(), 1.0)
    return value_in_mm * from_mm.get(target_unit.lower(), 1.0)
