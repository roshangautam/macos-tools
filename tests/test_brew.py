"""Test cases for the brew command module."""

import pytest
from click.testing import CliRunner
from commands.brew import brew


def test_brew_help():
    """Test brew command help output."""
    runner = CliRunner()
    result = runner.invoke(brew, ["--help"])
    assert result.exit_code == 0
    assert "Homebrew management tools" in result.output

def test_brew_update():
    """Test brew update subcommand."""
    runner = CliRunner()
    result = runner.invoke(brew, ["update", "--help"])
    assert result.exit_code == 0
    assert "Update Homebrew" in result.output


def test_brew_nonexistent_command():
    """Test brew with nonexistent subcommand."""
    runner = CliRunner()
    result = runner.invoke(brew, ["nonexistent"])
    assert result.exit_code == 2
    assert "No such command" in result.output
