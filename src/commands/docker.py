"""Docker management tools for macos-tools CLI."""

import json
import subprocess
from typing import Any, Dict, List, Optional, Tuple, Union

import click


def check_docker_installed() -> bool:
    """Check if Docker is installed and available."""
    try:
        result = subprocess.run(
            ["docker", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def check_docker_running() -> bool:
    """Check if Docker daemon is running."""
    if not check_docker_installed():
        return False

    try:
        result = subprocess.run(
            ["docker", "info"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        return result.returncode == 0
    except Exception:
        return False


def run_docker_command(
    command: List[str], capture_json: bool = False, streaming: bool = False
) -> Tuple[int, Any, str]:
    """Run a Docker command and return its output.

    Args:
        command: List of command parts
        capture_json: Whether to parse the output as JSON
        streaming: Whether to stream output in real-time

    Returns:
        Tuple of (return_code, stdout, stderr)
        If capture_json is True, stdout will be a parsed JSON object
    """
    if not check_docker_installed():
        return (
            1,
            None if capture_json else "",
            "Docker is not installed on this system.",
        )

    if not check_docker_running():
        return 1, None if capture_json else "", "Docker daemon is not running."

    full_command = ["docker"] + command

    if streaming:
        # For commands where we want to show output in real-time
        process = subprocess.Popen(
            full_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1,
        )

        stdout_lines = []
        stderr_lines = []

        # Process stdout and stderr
        for line in process.stdout:
            stdout_lines.append(line)
            click.echo(line.rstrip())

        for line in process.stderr:
            stderr_lines.append(line)
            click.echo(click.style(line.rstrip(), fg="yellow"), err=True)

        return_code = process.wait()
        stdout_data = "".join(stdout_lines)
        stderr_data = "".join(stderr_lines)
    else:
        # For commands where we want to capture and process output
        result = subprocess.run(
            full_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
        return_code = result.returncode
        stdout_data = result.stdout
        stderr_data = result.stderr

    # Parse JSON if requested
    if capture_json and return_code == 0:
        try:
            json_data = json.loads(stdout_data)
            return return_code, json_data, stderr_data
        except json.JSONDecodeError:
            return return_code, None, f"Error parsing JSON output: {stderr_data}"

    return return_code, stdout_data, stderr_data


@click.group()
def docker():
    """Docker management tools.

    A collection of tools for managing Docker containers, images, and volumes.
    """
    if not check_docker_installed():
        click.echo("Warning: Docker is not installed on this system.")
        click.echo("Install Docker from https://docs.docker.com/get-docker/")
        click.echo("")
    elif not check_docker_running():
        click.echo("Warning: Docker daemon is not running.")
        click.echo("Start Docker and try again.")
        click.echo("")


@docker.group()
def cleanup():
    """Clean up Docker resources.

    Remove unused containers, images, and volumes to free up disk space.
    """
    pass


@cleanup.command("containers")
@click.option(
    "--all",
    "all_containers",
    is_flag=True,
    help="Remove all containers, not just stopped ones",
)
@click.option("--force", "-f", is_flag=True, help="Force removal of containers")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be removed without removing anything",
)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
def cleanup_containers(all_containers, force, dry_run, yes, json_output):
    """Remove stopped Docker containers.

    By default, removes only stopped containers. Use --all to remove all containers.
    """
    if not check_docker_running():
        if json_output:
            click.echo(json.dumps({"error": "Docker daemon is not running"}))
        else:
            click.echo("Error: Docker daemon is not running.")
        return 1

    # Get list of containers based on options
    filter_arg = (
        ""
        if all_containers
        else "--filter status=exited --filter status=created --filter status=dead"
    )

    return_code, containers, stderr = run_docker_command(
        ["ps", "-a", "--format", "{{json .}}"] + filter_arg.split(), capture_json=False
    )

    if return_code != 0:
        if json_output:
            click.echo(json.dumps({"error": stderr}))
        else:
            click.echo(f"Error listing containers: {stderr}", err=True)
        return return_code

    # Parse container list (each line is a JSON object)
    container_list = []
    for line in containers.strip().split("\n"):
        if line:
            try:
                container_list.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    if not container_list:
        message = "No containers to remove."
        if json_output:
            click.echo(json.dumps({"message": message}))
        else:
            click.echo(message)
        return 0

    # Show containers that would be removed
    if not json_output:
        if all_containers:
            click.echo(f"Found {len(container_list)} containers that would be removed:")
        else:
            click.echo(
                f"Found {len(container_list)} stopped containers that would be removed:"
            )

        # Calculate column widths
        id_width = max(10, max(len(c.get("ID", "")[:12]) for c in container_list))
        name_width = max(10, max(len(c.get("Names", "")) for c in container_list))
        image_width = max(15, max(len(c.get("Image", "")) for c in container_list))
        status_width = max(10, max(len(c.get("Status", "")) for c in container_list))

        # Header
        click.echo(
            f"{'CONTAINER ID':{id_width}} | {'IMAGE':{image_width}} | {'STATUS':{status_width}} | {'NAMES':{name_width}}"
        )
        click.echo(
            f"{'-' * id_width} | {'-' * image_width} | {'-' * status_width} | {'-' * name_width}"
        )

        # Container list
        for container in container_list:
            click.echo(
                f"{container.get('ID', '')[:12]:{id_width}} | "
                f"{container.get('Image', ''):{image_width}} | "
                f"{container.get('Status', ''):{status_width}} | "
                f"{container.get('Names', ''):{name_width}}"
            )

    # In dry-run mode, just show what would be removed
    if dry_run:
        if json_output:
            result = {
                "dry_run": True,
                "containers": container_list,
                "count": len(container_list),
            }
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(
                "\nDry run complete. Use without --dry-run to actually remove containers."
            )
        return 0

    # Confirm before removing
    if not yes:
        if not click.confirm(f"Remove {len(container_list)} containers?"):
            if json_output:
                click.echo(json.dumps({"message": "Operation cancelled"}))
            else:
                click.echo("Operation cancelled.")
            return 0

    # Prepare removal command
    rm_cmd = ["rm"]
    if force:
        rm_cmd.append("-f")

    # Add container IDs
    container_ids = [container.get("ID") for container in container_list]

    # Execute removal
    if not json_output:
        click.echo("\nRemoving containers...")

    return_code, stdout, stderr = run_docker_command(
        rm_cmd + container_ids, streaming=True
    )

    if return_code == 0:
        if json_output:
            result = {
                "success": True,
                "removed_count": len(container_list),
                "containers": container_list,
            }
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"Successfully removed {len(container_list)} containers.")
    else:
        if json_output:
            result = {"success": False, "error": stderr, "removed_count": 0}
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"Error removing containers: {stderr}", err=True)

    return return_code


@cleanup.command("images")
@click.option(
    "--all",
    "all_images",
    is_flag=True,
    help="Remove all images, not just dangling ones",
)
@click.option("--force", "-f", is_flag=True, help="Force removal of images")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be removed without removing anything",
)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
def cleanup_images(all_images, force, dry_run, yes, json_output):
    """Remove unused Docker images.

    By default, removes only dangling images. Use --all to remove all unused images.
    """
    if not check_docker_running():
        if json_output:
            click.echo(json.dumps({"error": "Docker daemon is not running"}))
        else:
            click.echo("Error: Docker daemon is not running.")
        return 1

    # Get list of images based on options
    filter_arg = (
        "--filter dangling=true"
        if not all_images
        else "--filter dangling=true --filter dangling=false"
    )

    return_code, images, stderr = run_docker_command(
        ["images", "--format", "{{json .}}"] + filter_arg.split(), capture_json=False
    )

    if return_code != 0:
        if json_output:
            click.echo(json.dumps({"error": stderr}))
        else:
            click.echo(f"Error listing images: {stderr}", err=True)
        return return_code

    # Parse image list (each line is a JSON object)
    image_list = []
    for line in images.strip().split("\n"):
        if line:
            try:
                image_list.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    # Filter out images that are in use
    if not all_images:
        # Get list of images used by containers
        return_code, containers, stderr = run_docker_command(
            ["ps", "-a", "--format", "{{.Image}}"], capture_json=False
        )

        if return_code == 0:
            used_images = containers.strip().split("\n")
            image_list = [
                img
                for img in image_list
                if img.get("Repository") + ":" + img.get("Tag") not in used_images
            ]

    if not image_list:
        message = "No images to remove."
        if json_output:
            click.echo(json.dumps({"message": message}))
        else:
            click.echo(message)
        return 0

    # Calculate total size
    total_size = 0
    for image in image_list:
        size_str = image.get("Size", "0B")
        # Convert size string (e.g., "10MB", "1.2GB") to bytes
        if "MB" in size_str:
            size_value = float(size_str.replace("MB", "")) * 1024 * 1024
        elif "GB" in size_str:
            size_value = float(size_str.replace("GB", "")) * 1024 * 1024 * 1024
        elif "KB" in size_str:
            size_value = float(size_str.replace("KB", "")) * 1024
        else:
            size_value = float(size_str.replace("B", ""))
        total_size += size_value

    # Show images that would be removed
    if not json_output:
        if all_images:
            from src.commands.system import format_size

            click.echo(
                f"Found {len(image_list)} images that would be removed (approx. {format_size(total_size)}):"
            )
        else:
            from src.commands.system import format_size

            click.echo(
                f"Found {len(image_list)} unused images that would be removed (approx. {format_size(total_size)}):"
            )

        # Calculate column widths
        repo_width = max(12, max(len(i.get("Repository", "")) for i in image_list))
        tag_width = max(8, max(len(i.get("Tag", "")) for i in image_list))
        id_width = max(12, max(len(i.get("ID", "")[:12]) for i in image_list))
        size_width = max(8, max(len(i.get("Size", "")) for i in image_list))

        # Header
        click.echo(
            f"{'REPOSITORY':{repo_width}} | {'TAG':{tag_width}} | {'IMAGE ID':{id_width}} | {'SIZE':{size_width}}"
        )
        click.echo(
            f"{'-' * repo_width} | {'-' * tag_width} | {'-' * id_width} | {'-' * size_width}"
        )

        # Image list
        for image in image_list:
            click.echo(
                f"{image.get('Repository', ''):{repo_width}} | "
                f"{image.get('Tag', ''):{tag_width}} | "
                f"{image.get('ID', '')[:12]:{id_width}} | "
                f"{image.get('Size', ''):{size_width}}"
            )

    # In dry-run mode, just show what would be removed
    if dry_run:
        if dry_run and json_output:
            from src.commands.system import format_size

            result = {
                "dry_run": True,
                "images": image_list,
                "count": len(image_list),
                "total_size": total_size,
                "total_size_formatted": format_size(total_size),
            }
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(
                "\nDry run complete. Use without --dry-run to actually remove images."
            )
