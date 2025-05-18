"""Test cases for the docker command module."""

import pytest
from click.testing import CliRunner
from commands.docker import docker


def test_docker_help():
    """Test docker command help output."""
    runner = CliRunner()
    result = runner.invoke(docker, ["--help"])
    assert result.exit_code == 0
    assert "Docker management utilities." in result.output


def test_docker_clean():
    """Test docker clean subcommand."""
    runner = CliRunner()
    result = runner.invoke(docker, ["clean", "--help"])
    assert result.exit_code == 0
    assert "Clean Docker resources" in result.output


def test_docker_stats():
    """Test docker stats subcommand."""
    runner = CliRunner()
    result = runner.invoke(docker, ["stats", "--help"])
    assert result.exit_code == 0
    assert "Show Docker statistics" in result.output


def test_docker_clean_dry_run():
    """Test docker clean with dry run flag."""
    runner = CliRunner()
    result = runner.invoke(docker, ["clean", "--dry-run"])
    assert result.exit_code == 0
    assert "Would remove" in result.output


def test_docker_stats_no_containers():
    """Test docker stats with no running containers."""
    runner = CliRunner()
    result = runner.invoke(docker, ["stats"])
    assert result.exit_code == 0
    assert "No running containers" in result.output
