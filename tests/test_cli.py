"""Test cases for the CLI interface.

Contains unit tests for the main CLI entry point and all subcommands."""

import pytest
from click.testing import CliRunner
from cli import cli


def test_cli_basic():
    """Test that the CLI can be invoked without errors."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "A collection of useful tools for macOS." in result.output


def test_cli_version():
    """Test that version flag works correctly."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "version" in result.output.lower()


def test_all_commands_registered():
    """Test that all commands are properly registered."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    
    # Verify all expected commands are present
    expected_commands = ["system", "ports", "brew", "xcode", "network", "docker"]
    for cmd in expected_commands:
        assert cmd in result.output
