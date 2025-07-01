"""Pipeline gradient adjustment for medium-compatible flow systems.

This module provides functionality to adjust pipeline elevations based on
connected manhole elevations, with configurable medium compatibility strategies.
"""

import logging
from typing import Protocol

log = logging.getLogger(__name__)


class IMediumCompatibilityStrategy(Protocol):
    """Protocol for medium compatibility checking strategies."""

    def are_compatible(self, medium1: str, medium2: str) -> bool:
        """Check if two mediums are compatible."""
        ...

    def get_group(self, medium: str) -> str:
        """Get the compatibility group identifier for a medium."""
        ...

    def get_description(self, medium1: str, medium2: str) -> str:
        """Describe the compatibility between two mediums."""
        ...


class PrefixBasedCompatibility(IMediumCompatibilityStrategy):
    """Medium compatibility based on prefix matching (current implementation)."""

    def __init__(self, separator: str = " ") -> None:
        """Initialize with separator for prefix extraction."""
        self.separator = separator

    def get_medium_prefix(self, medium: str) -> str:
        """Extract medium prefix for compatibility checking."""
        if self.separator in medium:
            return medium.split(self.separator)[0].strip()
        return medium.strip()

    def are_compatible(self, medium1: str, medium2: str) -> bool:
        """Check if two mediums are compatible based on prefix."""
        prefix1 = self.get_medium_prefix(medium1)
        prefix2 = self.get_medium_prefix(medium2)
        return prefix1.lower() == prefix2.lower()

    def get_group(self, medium: str) -> str:
        """Get the compatibility group (prefix) for a medium."""
        return self.get_medium_prefix(medium)

    def get_description(self, medium1: str, medium2: str) -> str:
        """Describe the compatibility between two mediums."""
        if medium1 == medium2:
            return f"exact match ({medium1})"
        elif self.are_compatible(medium1, medium2):
            return f"compatible prefix ({medium1} ↔ {medium2})"
        else:
            return f"incompatible ({medium1} ✗ {medium2})"


class ExplicitRulesCompatibility(IMediumCompatibilityStrategy):
    """Medium compatibility based on explicit rules configuration."""

    def __init__(self, compatibility_rules: dict[str, list[str]] | None = None) -> None:
        """Initialize with explicit compatibility rules.

        Parameters
        ----------
        compatibility_rules : dict[str, list[str]] | None
            Dictionary mapping medium names to lists of compatible mediums
            Example: {
                "Regenabwasser Gemeinde": ["Regenabwasser Privat"],
                "Regenabwasser Privat": ["Regenabwasser Gemeinde"],
                "Abwasser Gemeinde": ["Abwasser Privat"],
                "Abwasser Privat": ["Abwasser Gemeinde"]
            }
        """
        self.rules = compatibility_rules or {}

    def are_compatible(self, medium1: str, medium2: str) -> bool:
        """Check if two mediums are compatible based on explicit rules."""
        if medium1 == medium2:
            return True
        return medium2 in self.rules.get(medium1, [])

    def get_group(self, medium: str) -> str:
        """Get compatibility group by finding all connected mediums."""
        # For explicit rules, group is the medium itself and its compatible mediums
        compatible = self.rules.get(medium, [])
        all_in_group = [medium] + compatible
        return "|".join(sorted(all_in_group))

    def get_description(self, medium1: str, medium2: str) -> str:
        """Describe the compatibility between two mediums."""
        if medium1 == medium2:
            return f"exact match ({medium1})"
        elif self.are_compatible(medium1, medium2):
            return f"explicit rule ({medium1} → {medium2})"
        else:
            return f"no rule ({medium1} ✗ {medium2})"


class PatternBasedCompatibility(IMediumCompatibilityStrategy):
    """Medium compatibility based on configurable patterns."""

    def __init__(self, patterns: dict[str, list[str]] | None = None) -> None:
        """Initialize with pattern matching rules.

        Parameters
        ----------
        patterns : dict[str, list[str]] | None
            Dictionary mapping pattern names to medium patterns
            Example: {
                "regenabwasser": ["Regenabwasser*", "Regenwasser*"],
                "abwasser": ["Abwasser*", "Schmutzwasser*"]
            }
        """
        self.patterns = patterns or {}

    def _matches_pattern(self, medium: str, pattern: str) -> bool:
        """Check if medium matches a pattern (supports * wildcard)."""
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return medium.startswith(prefix)
        return medium == pattern

    def _get_pattern_group(self, medium: str) -> str | None:
        """Find which pattern group a medium belongs to."""
        for group_name, patterns in self.patterns.items():
            for pattern in patterns:
                if self._matches_pattern(medium, pattern):
                    return group_name
        return None

    def are_compatible(self, medium1: str, medium2: str) -> bool:
        """Check if two mediums are compatible based on pattern groups."""
        if medium1 == medium2:
            return True
        group1 = self._get_pattern_group(medium1)
        group2 = self._get_pattern_group(medium2)
        return group1 is not None and group1 == group2

    def get_group(self, medium: str) -> str:
        """Get the pattern group for a medium."""
        group = self._get_pattern_group(medium)
        return group if group is not None else medium

    def get_description(self, medium1: str, medium2: str) -> str:
        """Describe the compatibility between two mediums."""
        if medium1 == medium2:
            return f"exact match ({medium1})"
        elif self.are_compatible(medium1, medium2):
            group = self._get_pattern_group(medium1)
            return f"pattern group '{group}' ({medium1} ↔ {medium2})"
        else:
            return f"different groups ({medium1} ✗ {medium2})"
