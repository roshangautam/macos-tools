"""
Command line interface for macOS tools.
"""
import click
from macos_tools.commands.system import system
from macos_tools.commands.ports import ports
from macos_tools.commands.brew import brew
from macos_tools.commands.xcode import xcode
from macos_tools.commands.network import network
from macos_tools.commands.docker import docker

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
