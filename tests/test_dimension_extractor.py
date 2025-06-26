"""Tests for dimension extraction functions."""

from dxfto.process.dimension_extractor import (
    convert_to_unit,
    extract_rectangular,
    extract_round,
)


class TestExtractRoundDimension:
    """Tests for extract_round_dimension function."""

    def test_extract_with_large_diameter_symbol(self):
        """Test extraction with large Ø symbol."""
        assert extract_round("Ø100") == (100.0, None)
        assert extract_round("Ø123.5") == (123.5, None)
        assert extract_round("Ø 200") == (200.0, None)
        assert extract_round(" Ø 150 ") == (150.0, None)

    def test_extract_with_small_diameter_symbol(self):
        """Test extraction with small ø symbol."""
        assert extract_round("ø100") == (100.0, None)
        assert extract_round("ø123.5") == (123.5, None)
        assert extract_round("ø 200") == (200.0, None)

    def test_extract_with_phi_symbols(self):
        """Test extraction with Φ and φ symbols."""
        assert extract_round("Φ100") == (100.0, None)
        assert extract_round("φ150") == (150.0, None)
        assert extract_round("Φ 200") == (200.0, None)

    def test_extract_with_dn_prefix(self):
        """Test extraction with DN prefix."""
        assert extract_round("DN100") == (100.0, None)
        assert extract_round("DN 150") == (150.0, None)
        assert extract_round("dn200") == (200.0, None)

    def test_extract_with_d_prefix(self):
        """Test extraction with D prefix."""
        assert extract_round("D100") == (100.0, None)
        assert extract_round("D 150") == (150.0, None)
        assert extract_round("d200") == (200.0, None)

    def test_extract_plain_number(self):
        """Test extraction of plain numbers."""
        assert extract_round("100") == (100.0, None)
        assert extract_round("123.5") == (123.5, None)
        assert extract_round(" 200 ") == (200.0, None)

    def test_extract_with_units(self):
        """Test extraction with unit suffixes."""
        assert extract_round("100mm") == (100.0, "mm")
        assert extract_round("150 mm") == (150.0, "mm")
        assert extract_round("200cm") == (200.0, "cm")
        assert extract_round("300 m") == (300.0, "m")
        assert extract_round("Ø100mm") == (100.0, "mm")

    def test_extract_with_comma_decimal(self):
        """Test extraction with comma as decimal separator."""
        assert extract_round("Ø100,5") == (100.5, None)
        assert extract_round("DN150,25") == (150.25, None)
        assert extract_round("200,75mm") == (200.75, "mm")

    def test_extract_mixed_case(self):
        """Test extraction with mixed case input."""
        assert extract_round("ø100MM") == (100.0, "mm")
        assert extract_round("Dn150") == (150.0, None)
        assert extract_round("d200CM") == (200.0, "cm")

    def test_extract_invalid_input(self):
        """Test extraction with invalid input."""
        assert extract_round("") is None
        assert extract_round("abc") is None
        assert extract_round("Ø") is None
        assert extract_round("DN") is None
        assert extract_round("100x200") is None
        assert extract_round("text without numbers") is None

    def test_extract_multiple_numbers(self):
        """Test extraction when multiple numbers are present."""
        # Should extract the first valid pattern
        assert extract_round("Ø100 and 200") == (100.0, None)
        assert extract_round("DN150 or DN200") == (150.0, None)

    def test_malformed_numbers(self):
        """Test handling of malformed numbers."""
        assert extract_round("Ø.100") is None


class TestExtractRectangularDimension:
    """Tests for extract_rectangular_dimension function."""

    def test_extract_with_x_separator(self):
        """Test extraction with 'x' separator."""
        assert extract_rectangular("100x200") == ((100.0, 200.0), None)
        assert extract_rectangular("150 x 300") == ((150.0, 300.0), None)
        assert extract_rectangular(" 200x400 ") == ((200.0, 400.0), None)

    def test_extract_with_multiplication_symbol(self):
        """Test extraction with '×' separator."""
        assert extract_rectangular("100×200") == ((100.0, 200.0), None)
        assert extract_rectangular("150 × 300") == ((150.0, 300.0), None)

    def test_extract_with_comma_separator(self):
        """Test extraction with ',' separator."""
        assert extract_rectangular("100,200") == ((100.0, 200.0), None)
        assert extract_rectangular("150 , 300") == ((150.0, 300.0), None)

    def test_extract_with_asterisk_separator(self):
        """Test extraction with '*' separator."""
        assert extract_rectangular("100*200") == ((100.0, 200.0), None)
        assert extract_rectangular("150 * 300") == ((150.0, 300.0), None)

    def test_extract_with_slash_separator(self):
        """Test extraction with '/' separator."""
        assert extract_rectangular("100/200") == ((100.0, 200.0), None)
        assert extract_rectangular("150 / 300") == ((150.0, 300.0), None)

    def test_extract_with_decimal_numbers(self):
        """Test extraction with decimal numbers."""
        assert extract_rectangular("100.5x200.75") == ((100.5, 200.75), None)
        assert extract_rectangular("150.25 × 300.5") == ((150.25, 300.5), None)

    def test_extract_with_comma_decimal(self):
        """Test extraction with comma as decimal separator."""
        assert extract_rectangular("100,5x200,75") == ((100.5, 200.75), None)
        assert extract_rectangular("150,25 × 300,5") == ((150.25, 300.5), None)

    def test_extract_with_units(self):
        """Test extraction with unit suffixes."""
        assert extract_rectangular("100x200mm") == ((100.0, 200.0), "mm")
        assert extract_rectangular("150×300cm") == ((150.0, 300.0), "cm")
        assert extract_rectangular("200*400m") == ((200.0, 400.0), "m")

    def test_extract_mixed_separators(self):
        """Test that function handles different separators correctly."""
        test_cases = [
            ("100x200", ((100.0, 200.0), None)),
            ("100×200", ((100.0, 200.0), None)),
            ("100,200", ((100.0, 200.0), None)),
            ("100*200", ((100.0, 200.0), None)),
            ("100/200", ((100.0, 200.0), None)),
        ]

        for input_text, expected in test_cases:
            assert extract_rectangular(input_text) == expected

    def test_extract_with_whitespace(self):
        """Test extraction with various whitespace patterns."""
        assert extract_rectangular("  100  x  200  ") == ((100.0, 200.0), None)
        assert extract_rectangular("\t150×300\n") == ((150.0, 300.0), None)

    def test_extract_invalid_input(self):
        """Test extraction with invalid input."""
        assert extract_rectangular("") is None
        assert extract_rectangular("abc") is None
        assert extract_rectangular("100") is None
        assert extract_rectangular("Ø100") is None
        assert extract_rectangular("DN150") is None
        assert extract_rectangular("text without numbers") is None
        assert extract_rectangular("100 200") is None  # No separator

    def test_extract_single_dimension(self):
        """Test that single dimensions are not extracted."""
        assert extract_rectangular("100") is None
        assert extract_rectangular("200.5") is None

    def test_extract_three_dimensions(self):
        """Test extraction when three dimensions are present."""
        # Should extract the first two valid dimensions
        assert extract_rectangular("100x200x300") == ((100.0, 200.0), None)
        assert extract_rectangular("150×250×350") == ((150.0, 250.0), None)

    def test_extract_case_insensitive(self):
        """Test that extraction is case insensitive for separators."""
        assert extract_rectangular("100X200") == ((100.0, 200.0), None)

    def test_malformed_numbers(self):
        """Test handling of malformed numbers."""
        assert extract_rectangular("100.x200") is None
        assert extract_rectangular("100x.200") is None


class TestConvertToStandardUnit:
    """Tests for convert_to_standard_unit function."""

    def test_convert_mm_to_mm(self):
        """Test conversion from mm to mm."""
        assert convert_to_unit(100.0, "mm", "mm") == 100.0

    def test_convert_cm_to_mm(self):
        """Test conversion from cm to mm."""
        assert convert_to_unit(10.0, "cm", "mm") == 100.0

    def test_convert_m_to_mm(self):
        """Test conversion from m to mm."""
        assert convert_to_unit(1.0, "m", "mm") == 1000.0

    def test_convert_mm_to_cm(self):
        """Test conversion from mm to cm."""
        assert convert_to_unit(100.0, "mm", "cm") == 10.0

    def test_convert_none_unit_defaults_to_mm(self):
        """Test that None unit defaults to mm."""
        assert convert_to_unit(100.0, None, "mm") == 100.0
        assert convert_to_unit(100.0, None, "cm") == 10.0


class TestDimensionExtractionEdgeCases:
    """Tests for edge cases in dimension extraction."""

    def test_empty_and_whitespace_input(self):
        """Test handling of empty and whitespace-only input."""
        assert extract_round("") is None
        assert extract_round("   ") is None
        assert extract_round("\t\n") is None

        assert extract_rectangular("") is None
        assert extract_rectangular("   ") is None
        assert extract_rectangular("\t\n") is None

    def test_very_large_numbers(self):
        """Test handling of very large numbers."""
        assert extract_round("Ø9999.99") == (9999.99, None)
        assert extract_rectangular("9999x8888") == ((9999.0, 8888.0), None)

    def test_very_small_numbers(self):
        """Test handling of very small numbers."""
        assert extract_round("Ø0.1") == (0.1, None)
        assert extract_rectangular("0.1x0.2") == ((0.1, 0.2), None)

    def test_zero_dimensions(self):
        """Test handling of zero dimensions."""
        assert extract_round("Ø0") == (0.0, None)
        assert extract_rectangular("0x0") == ((0.0, 0.0), None)
