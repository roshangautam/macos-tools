"""Test cases for the xcode command module."""

import pytest
from click.testing import CliRunner
from commands.xcode import xcode


def test_xcode_help():
    """Test xcode command help output."""
    runner = CliRunner()
    result = runner.invoke(xcode, ["--help"])
    assert result.exit_code == 0
    assert "Manage Xcode installation." in result.output


def test_xcode_install():
    """Test xcode install subcommand."""
    runner = CliRunner()
    result = runner.invoke(xcode, ["install", "--help"])
    assert result.exit_code == 0
    assert "Install Xcode" in result.output


def test_xcode_select():
    """Test xcode select subcommand."""
    runner = CliRunner()
    result = runner.invoke(xcode, ["select", "--help"])
    assert result.exit_code == 0
    assert "Select active Xcode version" in result.output


def test_xcode_install_invalid_version():
    """Test xcode install with invalid version."""
    runner = CliRunner()
    result = runner.invoke(xcode, ["install", "invalid_version"])
    assert result.exit_code == 1
    assert "Invalid version" in result.output


def test_xcode_select_no_version():
    """Test xcode select with no version specified."""
    runner = CliRunner()
    result = runner.invoke(xcode, ["select"])
    assert result.exit_code == 2
    assert "Error: Missing argument" in result.output
