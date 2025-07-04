"""Tests for pipeline gradient adjustment with medium compatibility."""

from pymto.analyze import (
    ExplicitRulesCompatibility,
    PatternBasedCompatibility,
    PrefixBasedCompatibility,
)


class TestMediumCompatibilityStrategies:
    """Test different medium compatibility strategies."""

    def test_prefix_based_compatibility(self):
        """Test prefix-based compatibility checking."""
        strategy = PrefixBasedCompatibility(separator=" ")

        # Same prefix - compatible
        assert strategy.are_compatible("Regenabwasser Gemeinde", "Regenabwasser Privat")
        assert strategy.are_compatible("Abwasser Gemeinde", "Abwasser Privat")

        # Different prefix - incompatible
        assert not strategy.are_compatible("Regenabwasser Gemeinde", "Abwasser Privat")
        assert not strategy.are_compatible("Wasser Gemeinde", "Gas Privat")

        # Exact match - compatible
        assert strategy.are_compatible("Wasser", "Wasser")

        # Prefix extraction
        assert strategy.get_medium_prefix("Regenabwasser Gemeinde") == "Regenabwasser"
        assert strategy.get_medium_prefix("Wasser") == "Wasser"
        assert strategy.get_group("Regenabwasser Privat") == "Regenabwasser"

    def test_explicit_rules_compatibility(self):
        """Test explicit rules-based compatibility."""
        rules = {
            "Regenabwasser Gemeinde": ["Regenabwasser Privat"],
            "Regenabwasser Privat": ["Regenabwasser Gemeinde"],
            "Abwasser Gemeinde": ["Abwasser Privat"],
            "Abwasser Privat": ["Abwasser Gemeinde"],
        }

        strategy = ExplicitRulesCompatibility(rules)

        # Rule-based compatibility
        assert strategy.are_compatible("Regenabwasser Gemeinde", "Regenabwasser Privat")
        assert strategy.are_compatible("Abwasser Privat", "Abwasser Gemeinde")

        # No rule - incompatible
        assert not strategy.are_compatible("Regenabwasser Gemeinde", "Abwasser Privat")
        assert not strategy.are_compatible("Wasser", "Gas")

        # Exact match always compatible
        assert strategy.are_compatible("Wasser", "Wasser")

    def test_pattern_based_compatibility(self):
        """Test pattern-based compatibility."""
        patterns = {
            "regenabwasser": ["Regenabwasser*", "Regenwasser*"],
            "abwasser": ["Abwasser*", "Schmutzwasser*"],
            "wasser": ["Wasser*"],
        }

        strategy = PatternBasedCompatibility(patterns)

        # Pattern group compatibility
        assert strategy.are_compatible("Regenabwasser Gemeinde", "Regenabwasser Privat")
        assert strategy.are_compatible("Regenabwasser Test", "Regenwasser ABC")
        assert strategy.are_compatible("Abwasser A", "Schmutzwasser B")

        # Different groups - incompatible
        assert not strategy.are_compatible("Regenabwasser Test", "Abwasser Test")
        assert not strategy.are_compatible("Wasser Test", "Gas Test")

        # Group identification
        assert strategy.get_group("Regenabwasser Gemeinde") == "regenabwasser"
        assert strategy.get_group("Regenwasser Test") == "regenabwasser"
        assert strategy.get_group("Unknown Medium") == "Unknown Medium"
