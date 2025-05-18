"""Test cases for the docker command module."""

import pytest
from click.testing import CliRunner
from commands.docker import docker


def test_docker_help():
    """Test docker command help output."""
    runner = CliRunner()
    result = runner.invoke(docker, ["--help"])
    assert result.exit_code == 0
    assert "Docker management tools." in result.output


def test_docker_cleanup():
    """Test docker cleanup subcommand."""
    runner = CliRunner()
    result = runner.invoke(docker, ["cleanup", "--help"])
    assert result.exit_code == 0
    assert "Clean up Docker resources" in result.output
