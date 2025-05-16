"""Homebrew management tools for macos-tools CLI."""

import json
import subprocess
import os
import re
import time
from typing import List, Dict, Any, Optional, Tuple, Union
import click
from macos_tools.commands.system import format_size, get_dir_size

def check_brew_exists() -> bool:
    """Check if Homebrew is installed on the system."""
    try:
        result = subprocess.run(
            ["which", "brew"], 
            capture_output=True, 
            text=True, 
            check=False
        )
        return result.returncode == 0
    except Exception:
        return False


def run_brew_command(command: List[str], streaming: bool = False) -> Tuple[int, str, str]:
    """Run a brew command and return its output.
    
    Args:
        command: List of command parts
        streaming: Whether to stream output in real-time
        
    Returns:
        Tuple of (return_code, stdout, stderr)
    """
    if not check_brew_exists():
        return 1, "", "Homebrew is not installed on this system."
    
    full_command = ["brew"] + command
    
    if streaming:
        # For commands where we want to show output in real-time
        process = subprocess.Popen(
            full_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        stdout_lines = []
        stderr_lines = []
        
        # Process stdout and stderr
        for line in process.stdout:
            stdout_lines.append(line)
            click.echo(line.rstrip())
        
        for line in process.stderr:
            stderr_lines.append(line)
            click.echo(click.style(line.rstrip(), fg='yellow'), err=True)
        
        return_code = process.wait()
        return return_code, "".join(stdout_lines), "".join(stderr_lines)
    else:
        # For commands where we want to capture and process output
        result = subprocess.run(
            full_command, 
            capture_output=True, 
            text=True, 
            check=False
        )
        return result.returncode, result.stdout, result.stderr


def get_brew_installed_formulae() -> List[Dict[str, Any]]:
    """Get a list of installed Homebrew formulae with details."""
    returncode, stdout, stderr = run_brew_command(["info", "--installed", "--json"])
    
    if returncode != 0:
        click.echo(f"Error getting formula information: {stderr}", err=True)
        return []
    
    try:
        formulae = json.loads(stdout)
        return formulae
    except json.JSONDecodeError:
        click.echo("Error parsing Homebrew output.", err=True)
        return []


def get_brew_cask_list() -> List[str]:
    """Get a list of installed Homebrew casks."""
    returncode, stdout, stderr = run_brew_command(["list", "--cask"])
    
    if returncode != 0:
        click.echo(f"Error getting cask list: {stderr}", err=True)
        return []
    
    return [line.strip() for line in stdout.splitlines() if line.strip()]


def get_brew_leaves() -> List[str]:
    """Get a list of formulae that were explicitly installed."""
    returncode, stdout, stderr = run_brew_command(["leaves"])
    
    if returncode != 0:
        click.echo(f"Error getting leaves: {stderr}", err=True)
        return []
    
    return [line.strip() for line in stdout.splitlines() if line.strip()]


def parse_brew_dir_sizes() -> Dict[str, int]:
    """Parse the output of brew commands and get sizes of Homebrew directories."""
    # Get Homebrew cache directory
    returncode, stdout, stderr = run_brew_command(["--cache"])
    
    if returncode != 0:
        click.echo(f"Error getting Homebrew cache directory: {stderr}", err=True)
        return {}
    
    cache_dir = stdout.strip()
    
    # Get Homebrew cellar directory
    returncode, stdout, stderr = run_brew_command(["--cellar"])
    if returncode != 0:
        click.echo(f"Error getting Homebrew cellar directory: {stderr}", err=True)
        return {}
    
    cellar_dir = stdout.strip()
    
    # Get base directory
    base_dir = os.path.dirname(cellar_dir)
    
    sizes = {
        "Cache": get_dir_size(cache_dir) if os.path.exists(cache_dir) else 0,
        "Cellar": get_dir_size(cellar_dir) if os.path.exists(cellar_dir) else 0,
        "Core": get_dir_size(os.path.join(base_dir, "Homebrew")) if os.path.exists(os.path.join(base_dir, "Homebrew")) else 0,
        "Cask": get_dir_size(os.path.join(base_dir, "Caskroom")) if os.path.exists(os.path.join(base_dir, "Caskroom")) else 0,
    }
    
    # Total size
    sizes["Total"] = sum(size for category, size in sizes.items())
    
    return sizes


@click.group()
def brew():
    """Homebrew management tools.
    
    A collection of tools for managing Homebrew installations.
    """
    if not check_brew_exists():
        click.echo("Warning: Homebrew is not installed on this system.")
        click.echo("Install Homebrew from https://brew.sh")
        click.echo("")


@brew.command("update")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
def brew_update(json_output):
    """Update Homebrew and all formulae.
    
    Equivalent to running 'brew update'.
    """
    if not check_brew_exists():
        if json_output:
            click.echo(json.dumps({"error": "Homebrew is not installed"}))
        else:
            click.echo("Error: Homebrew is not installed on this system.")
            click.echo("Install Homebrew from https://brew.sh")
        return 1
    
    click.echo("Updating Homebrew and formulae...")
    
    with click.progressbar(length=100, label="Updating Homebrew") as bar:
        # Start the update process
        process = subprocess.Popen(
            ["brew", "update"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1
        )
        
        stdout_lines = []
        stderr_lines = []
        output_lines = []
        
        # Poll process for new output until finished
        bar.update(10)  # Mark the start of the process
        
        while True:
            # Check if process has finished
            if process.poll() is not None:
                break
                
            # Read output from the process
            stdout_line = process.stdout.readline()
            if stdout_line:
                stdout_lines.append(stdout_line)
                output_lines.append(stdout_line.rstrip())
                
            stderr_line = process.stderr.readline()
            if stderr_line:
                stderr_lines.append(stderr_line)
                output_lines.append(stderr_line.rstrip())
                
            # Increment progress bar to show activity
            bar.update(1)
            time.sleep(0.1)
            
        # Get any remaining output
        remainder = process.communicate()
        if remainder[0]:
            stdout_lines.append(remainder[0])
            output_lines.append(remainder[0].rstrip())
        if remainder[1]:
            stderr_lines.append(remainder[1])
            output_lines.append(remainder[1].rstrip())
            
        # Complete the progress bar
        bar.update(100)
    
    returncode = process.returncode
    stdout = "".join(stdout_lines)
    stderr = "".join(stderr_lines)
    
    # Display the output
    if json_output:
        result = {
            "success": returncode == 0,
            "returncode": returncode,
            "stdout": stdout,
            "stderr": stderr
        }
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo("\nUpdate complete.")
        if output_lines:
            click.echo("\nOutput:")
            for line in output_lines:
                click.echo(f"  {line}")
    
    return returncode


@brew.command("cleanup")
@click.option("--dry-run", is_flag=True, help="Show what would be removed without actually removing anything")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
def brew_cleanup(dry_run, json_output):
    """Clean up old versions of installed formulae.
    
    Remove old versions of formulae, clear cache, and reclaim disk space.
    """
    if not check_brew_exists():
        if json_output:
            click.echo(json.dumps({"error": "Homebrew is not installed"}))
        else:
            click.echo("Error: Homebrew is not installed on this system.")
            click.echo("Install Homebrew from https://brew.sh")
        return 1
    
    # Get space used before cleanup
    sizes_before = parse_brew_dir_sizes()
    
    # Prepare command
    command = ["cleanup"]
    if dry_run:
        command.append("--dry-run")
    
    click.echo(f"{'Simulating cleanup' if dry_run else 'Cleaning up'} Homebrew files...")
    returncode, stdout, stderr = run_brew_command(command, streaming=True)
    
    # Get space used after cleanup
    sizes_after = parse_brew_dir_sizes() if not dry_run else sizes_before
    
    # Calculate space freed
    space_freed = sizes_before["Total"] - sizes_after["Total"] if not dry_run else 0
    
    if json_output:
        result = {
            "success": returncode == 0,
            "dry_run": dry_run,
            "space_freed": space_freed,
            "space_freed_formatted": format_size(space_freed),
            "sizes_before": {k: v for k, v in sizes_before.items()},
            "sizes_after": {k: v for k, v in sizes_after.items()},
            "stdout": stdout,
            "stderr": stderr
        }
        click.echo(json.dumps(result, indent=2))
    else:
        if not dry_run:
            click.echo(f"\nCleanup complete. Freed {format_size(space_freed)} of disk space.")
        else:
            click.echo("\nDry run complete. No files were removed.")
            potential_savings = 0
            # Try to extract potential savings from output
            for line in stdout.splitlines():
                # Look for size info, typically in format like "file (1234 bytes)"
                match = re.search(r'\((\d+) bytes\)', line)
                if match:
                    potential_savings += int(match.group(1))
            
            if potential_savings:
                click.echo(f"Potential space savings: {format_size(potential_savings)}")
    
    return returncode


@brew.command("doctor")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
def brew_doctor(json_output):
    """Run brew doctor to diagnose issues.
    
    Check for common issues and potential problems with your Homebrew installation.
    """
    if not check_brew_exists():
        if json_output:
            click.echo(json.dumps({"error": "Homebrew is not installed"}))
        else:
            click.echo("Error: Homebrew is not installed on this system.")
            click.echo("Install Homebrew from https://brew.sh")
        return 1
    
    click.echo("Running brew doctor to diagnose issues...")
    click.echo("This may take a moment...")
    
    returncode, stdout, stderr = run_brew_command(["doctor"], streaming=True)
    
    if json_output:
        result = {
            "success": returncode == 0,
            "output": stdout.splitlines(),
            "warnings": stderr.splitlines() if stderr else [],
            "has_issues": bool(re.search(r"warning", stdout + stderr, re.IGNORECASE)) or returncode != 0
        }
        click.echo(json.dumps(result, indent=2))
    
    return returncode


@brew.command("size")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
def brew_size(json_output):
    """Show disk space used by Homebrew.
    
    Displays the amount of disk space used by the Homebrew installation.
    """
    if not check_brew_exists():
        if json_output:
            click.echo(json.dumps({"error": "Homebrew is not installed"}))
        else:
            click.echo("Error: Homebrew is not installed on this system.")
            click.echo("Install Homebrew from https://brew.sh")
        return 1
    
    click.echo("Calculating Homebrew disk usage...")
    
    with click.progressbar(length=5, label="Analyzing disk usage") as bar:
        sizes = parse_brew_dir_sizes()
        bar.update(5)  # Complete the progress
    
    if json_output:
        click.echo(json.dumps(
            {k: {"bytes": v, "formatted": format_size(v)} for k, v in sizes.items()}, 
            indent=2
        ))
    else:
        # Calculate column widths
        category_width = max(len(category) for category in sizes.keys())
        size_width = max(len(format_size(size)) for size in sizes.values())
        
        # Create a nice table
        click.echo("\nHomebrew Disk Usage:")
        click.echo(f"{'-' * (category_width + size_width + 7)}")
        
        # Print rows in order, keeping Total for last
        categories = sorted([c for c in sizes.keys() if c != "Total"])
        
        for category in categories:
            size = sizes[category]
            click.echo(f"| {category:{category_width}} | {format_size(size):{size_width}} |")
        
        # Separator before total
        click.echo(f"{'-' * (category_width + size_width + 7)}")
        click.echo(f"| {'Total':{category_width}} | {format_size(sizes['Total']):{size_width}} |")
        click.echo(f"{'-' * (category_width + size_width + 7)}")
    
    return 0


@brew.command("leaves")
@click.option("--with-deps", is_flag=True, help="Show dependencies for each formula")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
def brew_leaves(with_deps, json_output):
    """List installed formulae that are not dependencies of another formula.
    
    These are formulae that were explicitly installed rather than being pulled in as dependencies.
    """
    if not check_brew_exists():
        if json_output:
            click.echo(json.dumps({"error": "Homebrew is not installed"}))
        else:
            click.echo("Error: Homebrew is not installed on this system.")
            click.echo("Install Homebrew from https://brew.sh")
        return 1
    
    # Get list of leaves (formulae installed explicitly)
    leaves = get_brew_leaves()
    
    if not leaves:
        if json_output:
            click.echo(json.dumps({"leaves": []}))
        else:
            click.echo("No explicitly installed formulae found.")
        return 0
    
    # If we need dependencies, get them
    if with_deps:
        formulae_info = {}
        for leaf in leaves:
            returncode, stdout, stderr = run_brew_command(["deps", "--tree", leaf])
            if returncode == 0:
                # Parse the dependency tree
                deps = []
                for line in stdout.splitlines():
                    if line.startswith(leaf):
                        continue  # Skip the formula itself
                    # Remove the tree characters and whitespace
                    dep = re.sub(r'^[├└]─[─┬]+\s*', '', line).strip()
                    if dep:
                        deps.append(dep)
                
                formulae_info[leaf] = deps
            else:
                formulae_info[leaf] = []
        
        # Output the results
        if json_output:
            click.echo(json.dumps({"leaves": formulae_info}, indent=2))
        else:
            click.echo(f"Found {len(leaves)} explicitly installed formulae:")
            for leaf, deps in formulae_info.items():
                click.echo(f"\n• {leaf}")
                if deps:
                    for dep in deps:
                        click.echo(f"  └── {dep}")
                else:
                    click.echo("  (no dependencies)")
    else:
        # Just output the list of leaves
        if json_output:
            click.echo(json.dumps({"leaves": leaves}, indent=2))
        else:
            click.echo(f"Explicitly installed formulae ({len(leaves)}):")
            for leaf in sorted(leaves):
                click.echo(f"• {leaf}")
    
    return 0

