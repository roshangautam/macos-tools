"""
Command line interface for macOS tools.
"""

import click

from src.commands.brew import brew
from src.commands.docker import docker
from src.commands.network import network
from src.commands.ports import ports
from src.commands.system import system
from src.commands.xcode import xcode


@click.group()
@click.version_option()
def cli():
    """A collection of useful tools for macOS."""
    pass


# Register all command groups with the main CLI
cli.add_command(system)
cli.add_command(ports)
cli.add_command(brew)
cli.add_command(xcode)
cli.add_command(network)
cli.add_command(docker)
