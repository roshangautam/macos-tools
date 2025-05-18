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


def test_brew_install_no_package():
    """Test brew install with no package specified."""
    runner = CliRunner()
    result = runner.invoke(brew, ["install"])
    assert result.exit_code == 2
    assert "Error: Missing argument" in result.output


def test_brew_update_dry_run():
    """Test brew update with dry run flag."""
    runner = CliRunner()
    result = runner.invoke(brew, ["update", "--dry-run"])
    assert result.exit_code == 0
    assert "Dry run" in result.output


def test_brew_nonexistent_command():
    """Test brew with nonexistent subcommand."""
    runner = CliRunner()
    result = runner.invoke(brew, ["nonexistent"])
    assert result.exit_code == 2
    assert "No such command" in result.output
