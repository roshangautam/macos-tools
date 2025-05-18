"""Test cases for the xcode command module."""

import pytest
from click.testing import CliRunner
from commands.xcode import xcode


def test_xcode_help():
    """Test xcode command help output."""
    runner = CliRunner()
    result = runner.invoke(xcode, ["--help"])
    assert result.exit_code == 0
    assert "Xcode management tools" in result.output


def test_xcode_cleanup():
    """Test xcode select subcommand."""
    runner = CliRunner()
    result = runner.invoke(xcode, ["cleanup", "--help"])
    assert result.exit_code == 0
    assert "Clean up Xcode caches and temporary files." in result.output
