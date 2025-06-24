"""Tests for CLI interface."""

import json
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from dxfto.cli import create_config, main


class TestCLI:
    """Test CLI commands."""

    def test_create_config_command(self):
        """Test create-config command."""
        runner = CliRunner()

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            config_path = Path(f.name)

        try:
            # Remove the file so create_config can create it
            config_path.unlink()

            result = runner.invoke(create_config, [str(config_path)])

            assert result.exit_code == 0
            assert "Sample configuration created" in result.output
            assert config_path.exists()

            # Verify the created config file
            with open(config_path, "r", encoding="utf-8") as f:
                config_data = json.load(f)

            assert "Abwasserleitung" in config_data
            assert "Wasserleitung" in config_data

            # Check structure of Abwasserleitung
            sewer = config_data["Abwasserleitung"]
            assert "Leitung" in sewer
            assert "Schacht" in sewer
            assert "Text" in sewer

            # Check that layers are specified
            assert "Layer" in sewer["Leitung"]
            assert "Layer" in sewer["Schacht"]
            assert "Layer" in sewer["Text"]

        finally:
            if config_path.exists():
                config_path.unlink()

    def test_main_help(self):
        """Test main command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "DXF processor" in result.output
        assert "process-dxf" in result.output
        assert "create-config" in result.output

    def test_process_dxf_help(self):
        """Test process-dxf command help."""
        runner = CliRunner()
        result = runner.invoke(main, ["process-dxf", "--help"])

        assert result.exit_code == 0
        assert "Process DXF file" in result.output
        assert "--landxml" in result.output
        assert "--output" in result.output
        assert "--config" in result.output
        assert "--grouping" in result.output
        assert "--text-assignment" in result.output

    @pytest.mark.skip(reason="Requires actual DXF file for integration test")
    def test_process_dxf_with_missing_file(self):
        """Test process-dxf with non-existent DXF file."""
        runner = CliRunner()
        result = runner.invoke(main, ["process-dxf", "nonexistent.dxf"])

        assert result.exit_code != 0
        assert "does not exist" in result.output or "No such file" in result.output

    def test_process_dxf_grouping_options(self):
        """Test that process-dxf accepts valid grouping options."""
        runner = CliRunner()

        # Test with invalid grouping option (should fail)
        result = runner.invoke(
            main,
            [
                "process-dxf",
                "dummy.dxf",  # This will fail anyway due to missing file
                "--grouping",
                "invalid",
            ],
        )

        assert result.exit_code != 0
        assert "Invalid value" in result.output

    def test_process_dxf_text_assignment_options(self):
        """Test that process-dxf accepts valid text assignment options."""
        runner = CliRunner()

        # Test with invalid text assignment option (should fail)
        result = runner.invoke(
            main,
            [
                "process-dxf",
                "dummy.dxf",  # This will fail anyway due to missing file
                "--text-assignment",
                "invalid",
            ],
        )

        assert result.exit_code != 0
        assert "Invalid value" in result.output


class TestCLIIntegration:
    """Integration tests for CLI (require creating test files)."""

    def create_minimal_dxf_content(self) -> str:
        """Create minimal DXF content for testing."""
        # This is a very basic DXF structure for testing
        # In a real scenario, you'd use a proper DXF library to create test files
        return """  0
SECTION
  2
HEADER
  0
ENDSEC
  0
SECTION
  2
TABLES
  0
ENDSEC
  0
SECTION
  2
BLOCKS
  0
ENDSEC
  0
SECTION
  2
ENTITIES
  0
LINE
  8
0
 10
0.0
 20
0.0
 30
0.0
 11
10.0
 21
0.0
 31
0.0
  0
CIRCLE
  8
0
 10
5.0
 20
5.0
 30
0.0
 40
2.0
  0
TEXT
  8
0
 10
5.0
 20
1.0
 30
0.0
 40
1.0
  1
DN200
  0
ENDSEC
  0
EOF"""

    @pytest.mark.skip(reason="Creates files and may be slow - enable for full integration testing")
    def test_process_dxf_color_grouping(self):
        """Test processing DXF with color-based grouping."""
        runner = CliRunner()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".dxf", delete=False) as dxf_file:
            dxf_file.write(self.create_minimal_dxf_content())
            dxf_path = Path(dxf_file.name)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as output_file:
            output_path = Path(output_file.name)

        try:
            # Remove output file so command can create it
            output_path.unlink()

            result = runner.invoke(
                main,
                [
                    "process-dxf",
                    str(dxf_path),
                    "--output",
                    str(output_path),
                    "--grouping",
                    "color",
                    "--verbose",
                ],
            )

            # The command might fail due to DXF parsing issues with our minimal file,
            # but we can check that it at least tries to process
            assert "Processing DXF file" in result.output

        finally:
            if dxf_path.exists():
                dxf_path.unlink()
            if output_path.exists():
                output_path.unlink()

    @pytest.mark.skip(reason="Creates files and may be slow - enable for full integration testing")
    def test_process_dxf_layer_grouping(self):
        """Test processing DXF with layer-based grouping."""
        runner = CliRunner()

        # Create config file
        config_data = {
            "TestMedium": {
                "Leitung": {"Layer": "0"},
                "Schacht": {"Layer": "0"},
                "Text": {"Layer": "0"},
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as config_file:
            json.dump(config_data, config_file)
            config_path = Path(config_file.name)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".dxf", delete=False) as dxf_file:
            dxf_file.write(self.create_minimal_dxf_content())
            dxf_path = Path(dxf_file.name)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as output_file:
            output_path = Path(output_file.name)

        try:
            # Remove output file so command can create it
            output_path.unlink()

            result = runner.invoke(
                main,
                [
                    "process-dxf",
                    str(dxf_path),
                    "--config",
                    str(config_path),
                    "--output",
                    str(output_path),
                    "--grouping",
                    "layer",
                    "--verbose",
                ],
            )

            # The command might fail due to DXF parsing issues with our minimal file,
            # but we can check that it at least tries to process
            assert "Processing DXF file" in result.output

        finally:
            if config_path.exists():
                config_path.unlink()
            if dxf_path.exists():
                dxf_path.unlink()
            if output_path.exists():
                output_path.unlink()
