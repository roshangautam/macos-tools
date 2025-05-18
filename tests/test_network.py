"""Test cases for the network command module."""

import pytest
from click.testing import CliRunner
from commands.network import network


def test_network_help():
    """Test network command help output."""
    runner = CliRunner()
    result = runner.invoke(network, ["--help"])
    assert result.exit_code == 0
    assert "Network management tools." in result.output
