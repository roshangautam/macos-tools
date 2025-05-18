"""Test cases for the system command module."""

import pytest
from click.testing import CliRunner
from commands.system import system


def test_system_help():
    """Test system command help output."""
    runner = CliRunner()
    result = runner.invoke(system, ["--help"])
    assert result.exit_code == 0
    assert "System management utilities." in result.output


def test_system_info():
    """Test system info subcommand."""
    runner = CliRunner()
    result = runner.invoke(system, ["info", "--help"])
    assert result.exit_code == 0
    assert "Show system information" in result.output


def test_system_info_verbose():
    """Test system info with verbose flag."""
    runner = CliRunner()
    result = runner.invoke(system, ["info", "--verbose"])
    assert result.exit_code == 0
    assert "Detailed system information" in result.output


def test_system_clean():
    """Test system clean subcommand."""
    runner = CliRunner()
    result = runner.invoke(system, ["clean", "--help"])
    assert result.exit_code == 0
    assert "Clean system caches" in result.output


def test_system_clean_force():
    """Test system clean with force flag."""
    runner = CliRunner()
    result = runner.invoke(system, ["clean", "--force"])
    assert result.exit_code == 0
    assert "Force cleaning" in result.output
