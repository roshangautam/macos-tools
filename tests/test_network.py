"""Test cases for the network command module."""

import pytest
from click.testing import CliRunner
from commands.network import network


def test_network_help():
    """Test network command help output."""
    runner = CliRunner()
    result = runner.invoke(network, ["--help"])
    assert result.exit_code == 0
    assert "Network utilities." in result.output


def test_network_speed():
    """Test network speed subcommand."""
    runner = CliRunner()
    result = runner.invoke(network, ["speed", "--help"])
    assert result.exit_code == 0
    assert "Test network speed" in result.output


def test_network_scan():
    """Test network scan subcommand."""
    runner = CliRunner()
    result = runner.invoke(network, ["scan", "--help"])
    assert result.exit_code == 0
    assert "Scan local network" in result.output


def test_network_speed_invalid_server():
    """Test network speed with invalid server."""
    runner = CliRunner()
    result = runner.invoke(network, ["speed", "--server", "invalid.server"]) 
    assert result.exit_code == 1
    assert "Connection failed" in result.output


def test_network_scan_invalid_range():
    """Test network scan with invalid IP range."""
    runner = CliRunner()
    result = runner.invoke(network, ["scan", "--range", "invalid.range"]) 
    assert result.exit_code == 2
    assert "Invalid IP range" in result.output
