"""Test cases for the ports command module."""

import pytest
from click.testing import CliRunner
from commands.ports import ports


def test_ports_help():
    """Test ports command help output."""
    runner = CliRunner()
    result = runner.invoke(ports, ["--help"])
    assert result.exit_code == 0
    assert "Port management tools." in result.output


def test_ports_list():
    """Test ports list subcommand."""
    runner = CliRunner()
    result = runner.invoke(ports, ["list", "--help"])
    assert result.exit_code == 0
    assert "List processes using specific ports." in result.output


def test_ports_kill():
    """Test ports kill subcommand."""
    runner = CliRunner()
    result = runner.invoke(ports, ["kill", "--help"])
    assert result.exit_code == 0
    assert "Kill processes using a specific port." in result.output


def test_ports_kill_invalid_port():
    """Test ports kill with invalid port number."""
    runner = CliRunner()
    result = runner.invoke(ports, ["kill", "-p", "999999"])  # Unlikely to be valid
    assert result.exit_code == 0
    assert "No processes found using port" in result.output
