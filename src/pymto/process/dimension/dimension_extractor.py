"""Dimension extraction utilities for parsing dimension information from text.

This module provides functions to extract dimensional information from text strings,
supporting both round (circular) and rectangular dimensions with various formats
and unit specifications.
"""

import re

from pymto.models import Unit

ROUND_DIMENSION_PATTERNS = [
    r"[ØøΦφ]\s*(\d+(?:[.,]\d+)?)\s*(mm|cm|m)?",  # Ø123mm, ø123, Φ123cm, φ123
    r"DN\s*(\d+(?:[.,]\d+)?)\s*(mm|cm|m)?",  # DN123, DN123mm
    r"D\s*(\d+(?:[.,]\d+)?)\s*(mm|cm|m)?",  # D123, D123cm
    r"^(\d+(?:[.,]\d+)?)\s*(mm|cm|m)?$",  # 123mm, 123, 123cm
]

UNIT_CONVERSIONS = {
    "mm": Unit.MILLIMETER,
    "cm": Unit.CENTIMETER,
    "m": Unit.METER,
}


def _get_unit_from_text(text: str | None) -> Unit:
    if text is None:
        return Unit.UNKNOWN
    unit_str = text.strip().lower()
    return UNIT_CONVERSIONS.get(unit_str, Unit.UNKNOWN)


def extract_round(text: str) -> tuple[float, Unit] | None:
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

    for pattern in ROUND_DIMENSION_PATTERNS:
        match_result = re.search(pattern, text_clean, re.IGNORECASE)
        if not match_result:
            continue
        diameter_str = match_result.group(1).replace(",", ".")
        unit = match_result.group(2).lower() if match_result.group(2) else None
        unit = _get_unit_from_text(unit)

        # Zusätzliche Validierung: Stelle sicher, dass es eine gültige Zahl ist
        if diameter_str.startswith(".") or diameter_str.endswith("."):
            continue

        diameter = float(diameter_str)
        return (diameter, unit)
    return None


RECT_DIMENSION_PATTERNS = [
    r"(\d+(?:[.,]\d+)?)\s*x\s*(\d+(?:[.,]\d+)?)\s*(mm|cm|m)?",  # 100x200mm
    r"(\d+(?:[.,]\d+)?)\s*×\s*(\d+(?:[.,]\d+)?)\s*(mm|cm|m)?",  # 100×200cm
    r"(\d+(?:[.,]\d+)?)\s*,\s*(\d+(?:[.,]\d+)?)\s*(mm|cm|m)?",  # 100,200m
    r"(\d+(?:[.,]\d+)?)\s*\*\s*(\d+(?:[.,]\d+)?)\s*(mm|cm|m)?",  # 100*200mm
    r"(\d+(?:[.,]\d+)?)\s*/\s*(\d+(?:[.,]\d+)?)\s*(mm|cm|m)?",  # 100/200cm
]


def extract_rectangular(text: str) -> tuple[tuple[float, float], Unit] | None:
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

    for pattern in RECT_DIMENSION_PATTERNS:
        match_result = re.search(pattern, text_clean, re.IGNORECASE)
        if match_result is None:
            continue
        try:
            length_str = match_result.group(1).replace(",", ".")
            width_str = match_result.group(2).replace(",", ".")
            unit = match_result.group(3).lower() if match_result.group(3) else None
            unit = _get_unit_from_text(unit)

            if length_str.startswith("."):
                length_str = length_str[1:]  # Remove leading dot
            if length_str.endswith("."):
                length_str = length_str[:-1]  # Remove trailing dot
            if width_str.startswith("."):
                width_str = width_str[1:]  # Remove leading dot
            if width_str.endswith("."):
                width_str = width_str[:-1]  # Remove trailing dot

            length = float(length_str)
            width = float(width_str)

            return ((length, width), unit)
        except ValueError:
            continue
    return None


def convert_to_unit(value: float, unit: Unit, target_unit: Unit) -> float:
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
    # Conversion factors to mm
    to_mm = {Unit.MILLIMETER: 1.0, Unit.CENTIMETER: 10.0, Unit.METER: 1000.0}

    # Conversion factors from mm
    from_mm = {Unit.MILLIMETER: 1.0, Unit.CENTIMETER: 0.1, Unit.METER: 0.001}

    # Convert to mm first, then to target unit
    value_in_mm = value * to_mm.get(unit, 1.0)
    return value_in_mm * from_mm.get(target_unit, 1.0)
