"""Xcode management tools for macos-tools CLI."""

import json
import os
import shutil
import subprocess
from typing import Any, Dict, List, Tuple

import click

from utils.formatting import format_size


def get_dir_size(path: str) -> int:
    """Calculate the total size of a directory in bytes.

    Args:
        path: Path to the directory.

    Returns:
        Total size in bytes.
    """
    total_size = 0
    for dirpath, _, filenames in os.walk(path):
        for filename in filenames:
            filepath = os.path.join(dirpath, filename)
            try:
                total_size += os.path.getsize(filepath)
            except (OSError, PermissionError):
                continue
    return total_size


def check_xcode_path_exists(path: str) -> bool:
    """Check if an Xcode-related path exists.

    Args:
        path: Path to check for existence.

    Returns:
        bool: True if path exists, False otherwise.
    """
    expanded_path = os.path.expanduser(path)
    return os.path.exists(expanded_path)


def get_xcode_path_size(path: str) -> int:
    """Get the size of an Xcode-related path.

    Args:
        path: Path to calculate size for.

    Returns:
        int: Size in bytes.
    """
    expanded_path = os.path.expanduser(path)
    if not os.path.exists(expanded_path):
        return 0

    try:
        return get_dir_size(expanded_path)
    except Exception:
        return 0


def clean_xcode_path(path: str, dry_run: bool = False) -> int:
    """Clean an Xcode-related path and return freed space.

    Args:
        path: Path to clean.
        dry_run: If True, only show what would be done without making changes.

    Returns:
        int: Number of bytes that would be or were freed.
    """
    expanded_path = os.path.expanduser(path)

    if not os.path.exists(expanded_path):
        return 0

    try:
        # Check if the path is in use
        if is_directory_in_use(expanded_path):
            click.echo(f"Warning: {expanded_path} is in use and won't be modified.")
            return 0

        # Calculate size before deletion
        total_size = get_dir_size(expanded_path)

        if dry_run:
            click.echo(f"Would remove {expanded_path} ({format_size(total_size)})")
        else:
            if os.path.isdir(expanded_path):
                shutil.rmtree(expanded_path, ignore_errors=True)
            else:
                os.remove(expanded_path)
            click.echo(f"Removed {expanded_path} ({format_size(total_size)})")

        return total_size

    except Exception as e:
        click.echo(f"Error cleaning {expanded_path}: {str(e)}", err=True)
        return 0


def is_directory_in_use(path: str) -> bool:
    """Check if a directory might be in use by checking for lock files or active processes.

    Args:
        path: Directory path to check.

    Returns:
        bool: True if the directory appears to be in use, False otherwise.
    """
    # Check for common lock files
    lock_files = [
        ".DS_Store",
        "com.apple.dt.Xcode",
        "com.apple.dt.xcodebuild",
        "com.apple.DeveloperTools",
    ]

    try:
        for root, _, files in os.walk(path):
            for file in files:
                if any(lock_file in file for lock_file in lock_files):
                    return True

        # Check if any process is using the directory
        try:
            # This is a simple check and might not catch all cases
            result = subprocess.run(
                ["lsof", "+D", path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            return result.returncode == 0 and bool(result.stdout)

        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    except (OSError, PermissionError):
        return True


@click.group()
def xcode() -> None:
    """Xcode management tools.

    A collection of tools for managing Xcode installations and caches.
    """
    pass


@xcode.group()
def cleanup() -> None:
    """Clean up Xcode caches and temporary files.

    Remove derived data, archives, and other Xcode-generated files to free up space.
    """
    pass


@cleanup.command()
@click.option(
    "--force",
    is_flag=True,
    help="Force cleanup even if directories appear to be in use",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be cleaned without actually removing files",
)
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
def cleanup_derived_data(force: bool, dry_run: bool, json_output: bool) -> None:
    """Clean Xcode derived data directory.

    Removes build products and intermediates to free up space.
    This directory can grow very large over time.

    Args:
        force: If True, clean even if directories appear to be in use.
        dry_run: If True, only show what would be cleaned.
        json_output: If True, output results in JSON format.
    """
    derived_data_paths = [
        "~/Library/Developer/Xcode/DerivedData",
        "~/Library/Developer/Xcode/Archives",
    ]

    total_freed = 0
    results = {
        "cleaned_paths": [],
        "skipped_paths": [],
        "total_freed_bytes": 0,
        "total_freed_human": "0 B",
    }

    for path in derived_data_paths:
        expanded_path = os.path.expanduser(path)
        if not os.path.exists(expanded_path):
            results["skipped_paths"].append(
                {"path": expanded_path, "reason": "Does not exist"}
            )
            continue

        if not force and is_directory_in_use(expanded_path):
            results["skipped_paths"].append(
                {"path": expanded_path, "reason": "Directory in use"}
            )
            continue

        if dry_run:
            size = get_dir_size(expanded_path)
            results["cleaned_paths"].append(
                {"path": expanded_path, "size_bytes": size, "dry_run": True}
            )
            total_freed += size
        else:
            size = clean_xcode_path(expanded_path, dry_run)
            if size > 0:
                results["cleaned_paths"].append(
                    {"path": expanded_path, "size_bytes": size, "dry_run": False}
                )
                total_freed += size

    results["total_freed_bytes"] = total_freed
    results["total_freed_human"] = format_size(total_freed)

    if json_output:
        click.echo(json.dumps(results, indent=2))
    elif not dry_run:
        if total_freed > 0:
            click.echo(f"✅ Freed {format_size(total_freed)} from Xcode derived data")
        else:
            click.echo("No Xcode derived data to clean")

    return 0


@cleanup.command()
@click.option(
    "--force", is_flag=True, help="Force cleanup even if archives appear to be in use"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be cleaned without actually removing files",
)
@click.option(
    "--keep-latest", is_flag=True, help="Keep the latest version of each archive"
)
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
def _get_archives(archives_path: str) -> List[Dict[str, Any]]:
    """Get a list of Xcode archives from the given path.

    Args:
        archives_path: Path to the Xcode archives directory.

    Returns:
        List of archive dictionaries with path, mtime, and name.
    """
    archives = []
    for root, _, files in os.walk(archives_path):
        for file in files:
            if file.endswith(".xcarchive"):
                archive_path = os.path.join(root, file)
                archives.append(
                    {
                        "path": archive_path,
                        "mtime": os.path.getmtime(archive_path),
                        "name": os.path.basename(archive_path).split(".")[0],
                    }
                )
    return archives


def _get_archives_to_remove(
    archives: List[Dict[str, Any]], keep_latest: bool
) -> List[Dict[str, Any]]:
    """Determine which archives should be removed.

    Args:
        archives: List of archive dictionaries.
        keep_latest: If True, keep the latest version of each archive.

    Returns:
        List of archives to remove.
    """
    if not keep_latest:
        return archives

    # Sort archives by modification time (newest first)
    archives.sort(key=lambda x: x["mtime"], reverse=True)

    # Group archives by project name and keep only the latest for each
    latest_archives = {}
    to_remove = []

    for archive in archives:
        # Get project name from archive name (first part before space)
        project_name = archive["name"].split(" ")[0]
        if project_name not in latest_archives:
            latest_archives[project_name] = archive
        else:
            to_remove.append(archive)

    return to_remove


def _calculate_total_size(archives: List[Dict[str, Any]]) -> int:
    """Calculate the total size of the given archives.

    Args:
        archives: List of archive dictionaries.

    Returns:
        Total size in bytes.
    """
    total_size = 0
    for archive in archives:
        try:
            total_size += get_dir_size(archive["path"])
        except (OSError, PermissionError):
            pass
    return total_size


def _remove_archives(archives: List[Dict[str, Any]]) -> Tuple[int, int, List[str]]:
    """Remove the specified archives.

    Args:
        archives: List of archive dictionaries to remove.

    Returns:
        Tuple of (removed_count, removed_size, errors)
    """
    removed_count = 0
    removed_size = 0
    errors = []

    for archive in archives:
        try:
            archive_size = get_dir_size(archive["path"])
            shutil.rmtree(archive["path"])
            removed_count += 1
            removed_size += archive_size
        except Exception as e:
            errors.append(f"Failed to remove {archive['path']}: {str(e)}")

    return removed_count, removed_size, errors


def _show_results(
    removed_count: int,
    total_archives: int,
    removed_size: int,
    errors: List[str],
    json_output: bool,
) -> None:
    """Display the results of the archive removal.

    Args:
        removed_count: Number of archives removed.
        total_archives: Total number of archives that were attempted to be removed.
        removed_size: Total size of removed archives in bytes.
        errors: List of error messages.
        json_output: If True, output results in JSON format.
    """
    result = {
        "success": removed_count > 0,
        "removed_count": removed_count,
        "total_archives": total_archives,
        "space_freed": removed_size,
        "formatted_space_freed": format_size(removed_size),
        "errors": errors,
    }

    if json_output:
        click.echo(json.dumps(result, indent=2))
    else:
        if removed_count > 0:
            click.echo(
                f"✅ Removed {removed_count} archives "
                f"(freed {format_size(removed_size)})"
            )
        if errors:
            click.echo("\nEncountered some errors:", err=True)
            for error in errors:
                click.echo(f"  - {error}", err=True)


def _get_archives_path() -> str:
    """Get the path to the Xcode archives directory.

    Returns:
        Path to the Xcode archives directory.
    """
    home_dir = os.path.expanduser("~")
    return os.path.join(home_dir, "Library/Developer/Xcode/Archives")


def _handle_no_archives_found(json_output: bool) -> int:
    """Handle the case when no archives are found.

    Args:
        json_output: Whether to output in JSON format.

    Returns:
        int: 0 for success.
    """
    message = "No archives found to clean"
    if json_output:
        click.echo(json.dumps({"message": message, "success": True}))
    else:
        click.echo(message)
    return 0


def _handle_no_archives_to_remove(keep_latest: bool, json_output: bool) -> int:
    """Handle the case when no archives need to be removed.

    Args:
        keep_latest: Whether to keep the latest versions.
        json_output: Whether to output in JSON format.

    Returns:
        int: 0 for success.
    """
    message = "No archives to remove"
    if keep_latest:
        message += " (keeping latest versions)"
    if json_output:
        click.echo(json.dumps({"message": message, "success": True}))
    else:
        click.echo(message)
    return 0


def _show_dry_run_results(
    to_remove: List[Dict[str, Any]], total_size: int, json_output: bool
) -> int:
    """Show the results of a dry run.

    Args:
        to_remove: List of archives that would be removed.
        total_size: Total size that would be freed.
        json_output: Whether to output in JSON format.

    Returns:
        int: 0 for success.
    """
    result = {
        "success": True,
        "dry_run": True,
        "archives_to_remove": [a["path"] for a in to_remove],
        "total_archives": len(to_remove),
        "space_to_free": total_size,
        "formatted_space": format_size(total_size),
    }
    if json_output:
        click.echo(json.dumps(result, indent=2))
    else:
        click.echo(
            f"Would remove {len(to_remove)} archives "
            f"(total: {format_size(total_size)})"
        )
    return 0


def cleanup_archives(
    force: bool, dry_run: bool, keep_latest: bool, json_output: bool
) -> int:
    """Clean Xcode archives directory.

    Removes old app archives to free up space.
    Useful after distributing apps to App Store or TestFlight.

    Args:
        force: If True, clean even if archives appear to be in use.
        dry_run: If True, only show what would be cleaned.
        keep_latest: If True, keep the latest version of each archive.
        json_output: If True, output results in JSON format.

    Returns:
        int: 0 on success, 1 on error.
    """
    # Get the path to the Xcode archives directory
    archives_path = _get_archives_path()
    expanded_path = os.path.expanduser(archives_path)

    if not os.path.exists(expanded_path):
        message = f"Archives directory not found at {archives_path}"
        if json_output:
            click.echo(json.dumps({"success": False, "error": message}))
        else:
            click.echo(f"❌ {message}", err=True)
        return 1

    try:
        # Get all archive files
        archives = _get_archives(expanded_path)

        if not archives:
            return _handle_no_archives_found(json_output)

        # Determine which archives to remove
        to_remove = _get_archives_to_remove(archives, keep_latest)

        if not to_remove:
            return _handle_no_archives_to_remove(keep_latest, json_output)

        # Calculate total size to be freed
        total_size = _calculate_total_size(to_remove)

        if dry_run:
            return _show_dry_run_results(to_remove, total_size, json_output)

        # Actually remove the archives
        if not force and not json_output:
            if not click.confirm(
                f"Remove {len(to_remove)} archives? "
                f"This will free {format_size(total_size)}. "
                "Continue?"
            ):
                return 0

        # Remove the archives and show results
        removed_count, removed_size, errors = _remove_archives(to_remove)
        _show_results(
            removed_count=removed_count,
            total_archives=len(to_remove),
            removed_size=removed_size,
            errors=errors,
            json_output=json_output,
        )

        return 0 if removed_count > 0 else 1

    except Exception as e:
        error_msg = f"Error cleaning archives: {str(e)}"
        if json_output:
            click.echo(json.dumps({"success": False, "error": error_msg}))
        else:
            click.echo(f"❌ {error_msg}", err=True)
        return 1


@cleanup.command("device-support")
@click.option(
    "--force",
    is_flag=True,
    help="Force cleanup even if directories appear to be in use",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be cleaned without actually removing files",
)
@click.option(
    "--keep-latest",
    is_flag=True,
    help="Keep the most recent device support files for each iOS version",
)
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
def _get_device_support_path() -> str:
    """Get the path to the Xcode device support directory.

    Returns:
        str: Path to the device support directory.
    """
    return os.path.expanduser("~/Library/Developer/Xcode/iOS DeviceSupport")


def _get_device_support_directories(device_support_path: str) -> List[Dict[str, Any]]:
    """Get all device support directories with their metadata.

    Args:
        device_support_path: Path to the device support directory.

    Returns:
        List of device support directory dictionaries with metadata.
    """
    device_dirs = []
    try:
        for dir_name in os.listdir(device_support_path):
            dir_path = os.path.join(device_support_path, dir_name)
            if os.path.isdir(dir_path):
                mtime = os.path.getmtime(dir_path)
                size = get_dir_size(dir_path)
                device_dirs.append(
                    {"name": dir_name, "path": dir_path, "mtime": mtime, "size": size}
                )
    except (PermissionError, OSError) as e:
        raise RuntimeError(f"Error reading device support directory: {str(e)}")

    return device_dirs


def _group_device_support_by_version(
    device_dirs: List[Dict[str, Any]],
) -> Dict[str, List[Dict[str, Any]]]:
    """Group device support directories by iOS version.

    Args:
        device_dirs: List of device support directory dictionaries.

    Returns:
        Dictionary mapping iOS versions to their device support directories.
    """
    version_groups = {}
    for device_dir in device_dirs:
        # Extract version from name (e.g., "12.4.1" from "12.4.1 (16G102)")
        version = device_dir["name"].split(" ")[0]
        if version not in version_groups:
            version_groups[version] = []
        version_groups[version].append(device_dir)
    return version_groups


def _get_directories_to_remove(
    device_dirs: List[Dict[str, Any]], keep_latest: bool
) -> Tuple[List[Dict[str, Any]], int]:
    """Determine which device support directories to remove.

    Args:
        device_dirs: List of device support directory dictionaries.
        keep_latest: Whether to keep the latest version of each iOS version.

    Returns:
        Tuple of (directories_to_remove, total_size_to_free)
    """
    if not device_dirs:
        return [], 0

    if not keep_latest:
        total_size = sum(d["size"] for d in device_dirs)
        return device_dirs, total_size

    # Group by iOS version and keep the latest for each
    version_groups = _group_device_support_by_version(device_dirs)
    to_keep = []
    to_remove = []

    for version, dirs in version_groups.items():
        # Sort by mtime (newest first) and keep the first one
        dirs_sorted = sorted(dirs, key=lambda x: x["mtime"], reverse=True)
        to_keep.append(dirs_sorted[0])
        to_remove.extend(dirs_sorted[1:])

    total_size = sum(d["size"] for d in to_remove)
    return to_remove, total_size


def _remove_device_support_directories(
    to_remove: List[Dict[str, Any]],
) -> Tuple[int, int, List[str]]:
    """Remove the specified device support directories.

    Args:
        to_remove: List of device support directory dictionaries to remove.

    Returns:
        Tuple of (removed_count, removed_size, errors)
    """
    removed_count = 0
    removed_size = 0
    errors = []

    for device_dir in to_remove:
        try:
            if os.path.exists(device_dir["path"]):
                shutil.rmtree(device_dir["path"])
                removed_count += 1
                removed_size += device_dir["size"]
        except Exception as e:
            errors.append(f"Error removing {device_dir['path']}: {str(e)}")

    return removed_count, removed_size, errors


def _show_device_cleanup_results(
    removed_count: int,
    total_directories: int,
    removed_size: int,
    errors: List[str],
    json_output: bool,
) -> None:
    """Show the results of the device cleanup operation.

    Args:
        removed_count: Number of directories removed.
        total_directories: Total number of directories that could be removed.
        removed_size: Total size of removed directories in bytes.
        errors: List of error messages.
        json_output: Whether to output in JSON format.
    """
    if json_output:
        result = {
            "success": True,
            "removed_count": removed_count,
            "total_directories": total_directories,
            "space_freed": removed_size,
            "formatted_space_freed": format_size(removed_size),
            "errors": errors,
        }
        click.echo(json.dumps(result, indent=2))
    else:
        if removed_count > 0:
            click.echo(
                f"✅ Removed {removed_count} device support directories "
                f"(freed {format_size(removed_size)})"
            )
        else:
            click.echo("No device support directories were removed")

        if errors:
            click.echo("\nErrors:", err=True)
            for error in errors[:5]:
                click.echo(f"  - {error}", err=True)
            if len(errors) > 5:
                click.echo(f"  - ...and {len(errors) - 5} more errors")


def cleanup_device_support(
    force: bool, dry_run: bool, keep_latest: bool, json_output: bool
) -> int:
    """Clean Xcode device support files.

    Removes device support files for iOS/iPadOS devices.
    These can consume significant space over time.

    Args:
        force: If True, clean even if files appear to be in use.
        dry_run: If True, only show what would be cleaned.
        keep_latest: If True, keep the latest version of each iOS version.
        json_output: If True, output results in JSON format.

    Returns:
        int: 0 on success, 1 on error.
    """
    device_support_path = _get_device_support_path()

    if not check_xcode_path_exists(device_support_path):
        message = f"Device support directory not found at {device_support_path}"
        if json_output:
            click.echo(json.dumps({"success": False, "error": message}))
        else:
            click.echo(message, err=True)
        return 1

    # Check if in use
    if not force and is_directory_in_use(device_support_path):
        message = "Device support directory appears to be in use. Use --force to clean anyway."
        if json_output:
            click.echo(json.dumps({"success": False, "error": message}))
        else:
            click.echo(
                "Warning: Device support directory appears to be in use.", err=True
            )
            click.echo(
                "This may indicate that Xcode is currently using these files.", err=True
            )
            click.echo("Use --force to clean anyway, or close Xcode first.", err=True)
        return 1

    try:
        # Get all device support directories
        device_dirs = _get_device_support_directories(device_support_path)

        if not device_dirs:
            message = "No device support directories found to clean"
            if json_output:
                click.echo(json.dumps({"message": message, "success": True}))
            else:
                click.echo(message)
            return 0

        # Determine which directories to remove
        to_remove, total_size = _get_directories_to_remove(device_dirs, keep_latest)

        if not to_remove:
            message = "No device support directories to remove"
            if keep_latest:
                message += " (keeping latest versions)"
            if json_output:
                click.echo(json.dumps({"message": message, "success": True}))
            else:
                click.echo(message)
            return 0

        # Handle dry run
        if dry_run:
            result = {
                "success": True,
                "dry_run": True,
                "directories_to_remove": [d["path"] for d in to_remove],
                "total_directories": len(to_remove),
                "space_to_free": total_size,
                "formatted_space_to_free": format_size(total_size),
            }
            if json_output:
                click.echo(json.dumps(result, indent=2))
            else:
                click.echo(
                    f"Would remove {len(to_remove)} device support directories "
                    f"(total: {format_size(total_size)})"
                )
            return 0

        # Actually remove the directories
        if not force and not json_output:
            if not click.confirm(
                f"Remove {len(to_remove)} device support directories? "
                f"This will free {format_size(total_size)}. "
                "Continue?"
            ):
                return 0

        # Remove the directories and show results
        removed_count, removed_size, errors = _remove_device_support_directories(
            to_remove
        )
        _show_device_cleanup_results(
            removed_count=removed_count,
            total_directories=len(to_remove),
            removed_size=removed_size,
            errors=errors,
            json_output=json_output,
        )

        return 0 if removed_count > 0 else 1

    except Exception as e:
        error_msg = f"Error cleaning device support directories: {str(e)}"
        if json_output:
            click.echo(json.dumps({"success": False, "error": error_msg}))
        else:
            click.echo(f"❌ {error_msg}", err=True)
        return 1


@cleanup.command("simulators")
@click.option(
    "--force",
    is_flag=True,
    help="Force cleanup even if directories appear to be in use",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be cleaned without actually removing files",
)
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
def cleanup_simulators(force, dry_run, json_output):
    """Clean iOS simulator caches and data.

    Removes data, caches, and tmp files from iOS simulators.
    Preserves simulator devices but cleans their content.
    """
    simulator_path = "~/Library/Developer/CoreSimulator/Devices"

    if not check_xcode_path_exists(simulator_path):
        if json_output:
            click.echo(
                json.dumps(
                    {
                        "success": False,
                        "error": f"Simulator directory not found at {simulator_path}",
                    }
                )
            )
        else:
            click.echo(f"Simulator directory not found at {simulator_path}")
        return 1

    # Check if in use
    if not force and is_directory_in_use(simulator_path):
        if json_output:
            click.echo(
                json.dumps(
                    {
                        "success": False,
                        "error": "Simulator directory appears to be in use. Use --force to clean anyway.",
                    }
                )
            )
        else:
            click.echo("Warning: Simulator directory appears to be in use.")
            click.echo("This may indicate that the iOS Simulator is currently running.")
            click.echo("Use --force to clean anyway, or close iOS Simulator first.")
        return 1

    # Get size before cleaning
    total_size_before = get_xcode_path_size(simulator_path)
    expanded_path = os.path.expanduser(simulator_path)

    # For simulators, we want to clean specific subdirectories (data, cache, tmp)
    # but preserve the simulator devices themselves
    try:
        devices = os.listdir(expanded_path)
    except (PermissionError, OSError) as e:
        if json_output:
            click.echo(json.dumps({"success": False, "error": str(e)}))
        else:
            click.echo(f"Error reading simulator directory: {str(e)}", err=True)
        return 1

    # Collect paths to clean
    cache_dirs = []
    data_dirs = []
    tmp_dirs = []

    for device in devices:
        device_path = os.path.join(expanded_path, device)
        if os.path.isdir(device_path):
            # Look for cache, data, tmp directories in each device directory
            for subdir in os.listdir(device_path):
                if subdir == "data":
                    data_dirs.append(os.path.join(device_path, subdir))
                elif subdir == "Library" or subdir == "tmp":
                    cache_dirs.append(os.path.join(device_path, subdir))

    # Calculate sizes
    data_size = sum(get_dir_size(d) for d in data_dirs)
    cache_size = sum(get_dir_size(d) for d in cache_dirs)

    # For dry run, just show what would be cleaned
    if dry_run:
        if json_output:
            click.echo(
                json.dumps(
                    {
                        "success": True,
                        "dry_run": True,
                        "data_size": data_size,
                        "cache_size": cache_size,
                        "total_size": data_size + cache_size,
                        "formatted_data_size": format_size(data_size),
                        "formatted_cache_size": format_size(cache_size),
                        "formatted_total_size": format_size(data_size + cache_size),
                    }
                )
            )
        else:
            click.echo(f"Simulator data size: {format_size(data_size)}")
            click.echo(f"Simulator cache size: {format_size(cache_size)}")
            click.echo(
                f"Total would free: {format_size(data_size + cache_size)} (dry run)"
            )
        return 0

    # If not dry run, actually clean the directories
    total_freed = 0
    errors = []

    # Clean data directories
    if data_dirs:
        with click.progressbar(data_dirs, label="Cleaning simulator data") as bar:
            for data_dir in bar:
                try:
                    data_size = get_dir_size(data_dir)
                    # Clean contents but keep directory
                    for item in os.listdir(data_dir):
                        item_path = os.path.join(data_dir, item)
                        try:
                            if os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                            else:
                                os.remove(item_path)
                        except (PermissionError, OSError) as e:
                            errors.append(f"Could not remove {item_path}: {str(e)}")

                    # Calculate space freed
                    data_size_after = get_dir_size(data_dir)
                    total_freed += data_size - data_size_after
                except Exception as e:
                    errors.append(f"Error processing {data_dir}: {str(e)}")

    # Clean cache directories
    if cache_dirs:
        with click.progressbar(cache_dirs, label="Cleaning simulator caches") as bar:
            for cache_dir in bar:
                try:
                    cache_size = get_dir_size(cache_dir)
                    # Clean contents but keep directory
                    for item in os.listdir(cache_dir):
                        item_path = os.path.join(cache_dir, item)
                        try:
                            if os.path.isdir(item_path):
                                shutil.rmtree(item_path)
                            else:
                                os.remove(item_path)
                        except (PermissionError, OSError) as e:
                            errors.append(f"Could not remove {item_path}: {str(e)}")

                    # Calculate space freed
                    cache_size_after = get_dir_size(cache_dir)
                    total_freed += cache_size - cache_size_after
                except Exception as e:
                    errors.append(f"Error processing {cache_dir}: {str(e)}")

    if json_output:
        click.echo(
            json.dumps(
                {
                    "success": True,
                    "space_freed": total_freed,
                    "formatted_space_freed": format_size(total_freed),
                    "errors": errors[
                        :10
                    ],  # Only include first 10 errors to avoid huge JSON
                }
            )
        )
    else:
        click.echo(f"Freed {format_size(total_freed)} of space from simulator files")
        if errors:
            click.echo("\nErrors encountered:")
            for error in errors[:5]:  # Show only first 5 errors
                click.echo(f"  - {error}")
            if len(errors) > 5:
                click.echo(f"  - ...and {len(errors) - 5} more errors")

    return 0


@cleanup.command("all")
@click.option(
    "--force",
    is_flag=True,
    help="Force cleanup even if directories appear to be in use",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be cleaned without actually removing files",
)
@click.option(
    "--keep-latest", is_flag=True, help="Keep latest archives and device support"
)
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
def cleanup_all(force, dry_run, keep_latest, json_output):
    """Clean all Xcode caches and temporary files.

    This runs all cleanup commands (derived-data, archives, device-support, simulators).
    Use --keep-latest to preserve the most recent archives and device support files.
    """
    # Store results from each cleanup operation
    results = {}

    # Run derived data cleanup
    click.echo("Cleaning Xcode derived data...")
    returncode = cleanup_derived_data.callback(
        force=force, dry_run=dry_run, json_output=False
    )
    results["derived_data"] = {"success": returncode == 0}

    # Run archives cleanup
    click.echo("\nCleaning Xcode archives...")
    returncode = cleanup_archives.callback(
        force=force, dry_run=dry_run, keep_latest=keep_latest, json_output=False
    )
    results["archives"] = {"success": returncode == 0}

    # Run device support cleanup
    click.echo("\nCleaning device support files...")
    returncode = cleanup_device_support.callback(
        force=force, dry_run=dry_run, keep_latest=keep_latest, json_output=False
    )
    results["device_support"] = {"success": returncode == 0}

    # Run simulator cleanup
    click.echo("\nCleaning simulator files...")
    returncode = cleanup_simulators.callback(
        force=force, dry_run=dry_run, json_output=False
    )
    results["simulators"] = {"success": returncode == 0}

    # Calculate overall success
    overall_success = all(r["success"] for r in results.values())

    if json_output:
        click.echo(
            json.dumps(
                {
                    "success": overall_success,
                    "results": results,
                    "dry_run": dry_run,
                    "keep_latest": keep_latest,
                },
                indent=2,
            )
        )
    else:
        click.echo("\nXcode cleanup completed.")
        if dry_run:
            click.echo("This was a dry run. Use --force to actually clean files.")

    return 0 if overall_success else 1
