"""Test cases for the CLI interface.

Contains unit tests for the main CLI entry point."""

from click.testing import CliRunner

# Import after installing package in development mode
from cli import cli


def test_cli_basic():
    """Test that the CLI can be invoked without errors."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Show this message and exit." in result.output


def test_cli_version():
    """Test that version flag works correctly."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])
    assert result.exit_code == 0
    assert "version" in result.output.lower()
