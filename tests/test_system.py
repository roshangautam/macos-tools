"""Test cases for the system command module."""

import pytest
from click.testing import CliRunner
from commands.system import system


def test_system_help():
    """Test system command help output."""
    runner = CliRunner()
    result = runner.invoke(system, ["--help"])
    assert result.exit_code == 0
    assert "System management tools." in result.output


def test_system_info():
    """Test system info subcommand."""
    runner = CliRunner()
    result = runner.invoke(system, ["info", "--help"])
    assert result.exit_code == 0
    assert "Display system information" in result.output


def test_system_cleanup_temp():
    """Test system cleanup temp subcommand."""
    runner = CliRunner()
    result = runner.invoke(system, ["cleanup-temp", "--help"])
    assert result.exit_code == 0
    assert "Clean up temporary files." in result.output
