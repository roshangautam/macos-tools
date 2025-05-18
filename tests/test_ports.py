"""Test cases for the ports command module."""

import pytest
from click.testing import CliRunner
from commands.ports import ports


def test_ports_help():
    """Test ports command help output."""
    runner = CliRunner()
    result = runner.invoke(ports, ["--help"])
    assert result.exit_code == 0
    assert "Port management utilities." in result.output


def test_ports_list():
    """Test ports list subcommand."""
    runner = CliRunner()
    result = runner.invoke(ports, ["list", "--help"])
    assert result.exit_code == 0
    assert "List open ports" in result.output


def test_ports_kill():
    """Test ports kill subcommand."""
    runner = CliRunner()
    result = runner.invoke(ports, ["kill", "--help"])
    assert result.exit_code == 0
    assert "Kill process using port" in result.output


def test_ports_list_verbose():
    """Test ports list with verbose flag."""
    runner = CliRunner()
    result = runner.invoke(ports, ["list", "--verbose"])
    assert result.exit_code == 0
    assert "Detailed port information" in result.output


def test_ports_kill_invalid_port():
    """Test ports kill with invalid port number."""
    runner = CliRunner()
    result = runner.invoke(ports, ["kill", "999999"])  # Unlikely to be valid
    assert result.exit_code == 1
    assert "Invalid port" in result.output
