"""
Command line interface for macOS tools.

This module provides the main CLI entry point for all macOS tools commands.
"""

import click

from commands.brew import brew
from commands.docker import docker
from commands.network import network
from commands.ports import ports
from commands.system import system
from commands.xcode import xcode


@click.group()
@click.version_option()
def cli():
    """A collection of useful tools for macOS.
    
    Provides commands for system management, package management,
    network tools and development environment setup.
    """
    pass


# Register all command groups with the main CLI
cli.add_command(system)
cli.add_command(ports)
cli.add_command(brew)
cli.add_command(xcode)
cli.add_command(network)
cli.add_command(docker)
