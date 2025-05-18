"""Test cases for the CLI interface."""

from click.testing import CliRunner


def test_cli_basic():
    """Test that the CLI can be invoked without errors."""
    from src.cli import cli

    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Show this message and exit." in result.output
