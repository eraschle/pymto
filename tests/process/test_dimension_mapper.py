#!/usr/bin/env python

from pymto.process.dimension import DimensionMapper


class TestDimensionMapper:
    """Tests for DimensionMapper class"""

    def test_round_dimension_exact_5_steps(self):
        """Test rounding to exact 5cm steps"""
        mapper = DimensionMapper()

        # Test exact 5cm values (should remain unchanged)
        assert mapper.round_dimension(1.0) == 1.0  # 100cm
        assert mapper.round_dimension(1.05) == 1.05  # 105cm
        assert mapper.round_dimension(1.10) == 1.10  # 110cm

    def test_round_dimension_rounding_up(self):
        """Test rounding up to nearest 5cm"""
        mapper = DimensionMapper()

        # Values that should round up
        assert mapper.round_dimension(1.03) == 1.05  # 103cm -> 105cm
        assert mapper.round_dimension(1.08) == 1.10  # 108cm -> 110cm
        assert mapper.round_dimension(0.53) == 0.55  # 53cm -> 55cm

    def test_round_dimension_rounding_down(self):
        """Test rounding down to nearest 5cm"""
        mapper = DimensionMapper()

        # Values that should round down
        assert mapper.round_dimension(1.02) == 1.00  # 102cm -> 100cm
        assert mapper.round_dimension(1.07) == 1.05  # 107cm -> 105cm
        assert mapper.round_dimension(0.52) == 0.50  # 52cm -> 50cm

    def test_round_dimension_midpoint(self):
        """Test rounding at midpoint (2.5cm from 5cm step)"""
        mapper = DimensionMapper()

        # 2.5cm offset should round to nearest even (standard Python rounding)
        assert mapper.round_dimension(1.025) == 1.0  # 102.5cm -> 100cm
        assert mapper.round_dimension(1.075) == 1.10  # 107.5cm -> 110cm

    def test_round_dimension_small_values(self):
        """Test rounding for small values"""
        mapper = DimensionMapper()

        assert mapper.round_dimension(0.03) == 0.05  # 3cm -> 5cm
        assert mapper.round_dimension(0.02) == 0.0  # 2cm -> 0cm
        assert mapper.round_dimension(0.08) == 0.10  # 8cm -> 10cm

    def test_round_dimension_large_values(self):
        """Test rounding for large values"""
        mapper = DimensionMapper()

        assert mapper.round_dimension(25.03) == 25.05  # 2503cm -> 2505cm
        assert mapper.round_dimension(25.07) == 25.05  # 2507cm -> 2505cm
        assert mapper.round_dimension(25.08) == 25.10  # 2508cm -> 2510cm

    def test_round_dimension_precision(self):
        """Test precision handling"""
        mapper = DimensionMapper()

        # Test that result maintains proper precision
        result = mapper.round_dimension(1.234)
        assert isinstance(result, float)
        assert abs(result - 1.25) < 1e-10  # Should be 1.25 (125cm)
