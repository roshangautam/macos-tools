"""Xcode management tools for macos-tools CLI."""

import os
import shutil
import re
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
import click
from macos_tools.commands.system import format_size, get_dir_size

def check_xcode_path_exists(path: str) -> bool:
    """Check if an Xcode-related path exists."""
    expanded_path = os.path.expanduser(path)
    return os.path.exists(expanded_path)


def get_xcode_path_size(path: str) -> int:
    """Get the size of an Xcode-related path."""
    expanded_path = os.path.expanduser(path)
    if not os.path.exists(expanded_path):
        return 0
    
    try:
        return get_dir_size(expanded_path)
    except Exception:
        return 0


def clean_xcode_path(path: str, dry_run: bool = False) -> int:
    """Clean an Xcode-related path and return freed space."""
    expanded_path = os.path.expanduser(path)
    if not os.path.exists(expanded_path):
        return 0
    
    if dry_run:
        return get_dir_size(expanded_path)
    
    size_before = get_dir_size(expanded_path)
    
    # Try to remove all contents but keep the directory
    try:
        for item in os.listdir(expanded_path):
            item_path = os.path.join(expanded_path, item)
            try:
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
            except (PermissionError, OSError) as e:
                click.echo(f"Could not remove {item_path}: {str(e)}", err=True)
    except (PermissionError, OSError) as e:
        click.echo(f"Error accessing {expanded_path}: {str(e)}", err=True)
    
    # Calculate space freed
    size_after = get_dir_size(expanded_path)
    return size_before - size_after


def is_directory_in_use(path: str) -> bool:
    """Check if a directory might be in use by checking for lock files or active processes."""
    expanded_path = os.path.expanduser(path)
    if not os.path.exists(expanded_path):
        return False
    
    # Check if any processes are using this directory
    try:
        cmd = f"lsof +D {expanded_path} 2>/dev/null | wc -l"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0 and int(result.stdout.strip()) > 0:
            return True
    except Exception:
        pass
    
    # Check for lock files
    try:
        for root, dirs, files in os.walk(expanded_path):
            for f in files:
                if "lock" in f.lower() or f.endswith(".lock"):
                    return True
    except Exception:
        pass
    
    return False


@click.group()
def xcode():
    """Xcode management tools.
    
    A collection of tools for managing Xcode installations and caches.
    """
    pass


@xcode.group()
def cleanup():
    """Clean up Xcode caches and temporary files.
    
    Remove derived data, archives, and other Xcode-generated files to free up space.
    """
    pass


@cleanup.command("derived-data")
@click.option("--force", is_flag=True, help="Force cleanup even if directories appear to be in use")
@click.option("--dry-run", is_flag=True, help="Show what would be cleaned without actually removing files")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
def cleanup_derived_data(force, dry_run, json_output):
    """Clean Xcode derived data directory.
    
    Removes build products and intermediates to free up space.
    This directory can grow very large over time.
    """
    derived_data_path = "~/Library/Developer/Xcode/DerivedData"
    
    if not check_xcode_path_exists(derived_data_path):
        if json_output:
            click.echo(json.dumps({
                "success": False,
                "error": f"Derived data directory not found at {derived_data_path}"
            }))
        else:
            click.echo(f"Derived data directory not found at {derived_data_path}")
        return 1
    
    # Check if in use
    if not force and is_directory_in_use(derived_data_path):
        if json_output:
            click.echo(json.dumps({
                "success": False,
                "error": "Derived data directory appears to be in use. Use --force to clean anyway."
            }))
        else:
            click.echo("Warning: Derived data directory appears to be in use.")
            click.echo("This may indicate that Xcode or a build process is currently active.")
            click.echo("Use --force to clean anyway, or close Xcode first.")
        return 1
    
    # Get size before cleaning
    size_before = get_xcode_path_size(derived_data_path)
    
    if json_output:
        if dry_run:
            click.echo(json.dumps({
                "success": True,
                "dry_run": True,
                "size": size_before,
                "formatted_size": format_size(size_before)
            }))
            return 0
    else:
        click.echo(f"Derived data size: {format_size(size_before)}")
        if dry_run:
            click.echo(f"Would free approximately {format_size(size_before)} (dry run)")
            return 0
    
    click.echo(f"Cleaning Xcode derived data at {derived_data_path}...")
    
    expanded_path = os.path.expanduser(derived_data_path)
    try:
        items = os.listdir(expanded_path)
        with click.progressbar(items, label="Cleaning derived data") as bar:
            for item in bar:
                item_path = os.path.join(expanded_path, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                except (PermissionError, OSError) as e:
                    if not json_output:
                        click.echo(f"\nCould not remove {item}: {str(e)}", err=True)
    except (PermissionError, OSError) as e:
        if json_output:
            click.echo(json.dumps({
                "success": False,
                "error": str(e)
            }))
        else:
            click.echo(f"Error: {str(e)}", err=True)
        return 1
    
    # Calculate space freed
    size_after = get_xcode_path_size(derived_data_path)
    space_freed = size_before - size_after
    
    if json_output:
        click.echo(json.dumps({
            "success": True,
            "space_freed": space_freed,
            "formatted_space_freed": format_size(space_freed),
            "size_before": size_before,
            "size_after": size_after
        }))
    else:
        click.echo(f"Freed {format_size(space_freed)} of space from derived data")
    
    return 0


@cleanup.command("archives")
@click.option("--force", is_flag=True, help="Force cleanup even if directories appear to be in use")
@click.option("--dry-run", is_flag=True, help="Show what would be cleaned without actually removing files")
@click.option("--keep-latest", is_flag=True, help="Keep the most recent archive for each project")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
def cleanup_archives(force, dry_run, keep_latest, json_output):
    """Clean Xcode archives directory.
    
    Removes old app archives to free up space.
    Useful after distributing apps to App Store or TestFlight.
    """
    archives_path = "~/Library/Developer/Xcode/Archives"
    
    if not check_xcode_path_exists(archives_path):
        if json_output:
            click.echo(json.dumps({
                "success": False,
                "error": f"Archives directory not found at {archives_path}"
            }))
        else:
            click.echo(f"Archives directory not found at {archives_path}")
        return 1
    
    # Check if in use
    if not force and is_directory_in_use(archives_path):
        if json_output:
            click.echo(json.dumps({
                "success": False,
                "error": "Archives directory appears to be in use. Use --force to clean anyway."
            }))
        else:
            click.echo("Warning: Archives directory appears to be in use.")
            click.echo("This may indicate that Xcode is currently archiving a project.")
            click.echo("Use --force to clean anyway, or close Xcode first.")
        return 1
    
    # Get size before cleaning
    size_before = get_xcode_path_size(archives_path)
    
    expanded_path = os.path.expanduser(archives_path)
    
    # Handle keep latest option (we need different logic)
    if keep_latest:
        if json_output and dry_run:
            click.echo(json.dumps({
                "success": True,
                "dry_run": True,
                "size": size_before,
                "formatted_size": format_size(size_before),
                "note": "Would keep latest archive for each project"
            }))
            return 0
            
        if not json_output:
            click.echo(f"Archives size: {format_size(size_before)}")
            if dry_run:
                click.echo("Dry run: would keep the latest archive for each project")
        
        # Get organized structure of archives
        # Format: {"ProjectName": {"20250515": [archive1.xcarchive, archive2.xcarchive]}}
        archives_structure = {}
        
        try:
            # Archives are typically organized by date folders
            for date_dir in sorted(os.listdir(expanded_path)):
                date_path = os.path.join(expanded_path, date_dir)
                if os.path.isdir(date_path):
                    for archive in os.listdir(date_path):
                        if archive.endswith(".xcarchive"):
                            # Extract project name from archive name
                            # Format is usually ProjectName YYYY-MM-DD HH.MM.SS.xcarchive
                            project_name = archive.split(" ")[0]
                            
                            if project_name not in archives_structure:
                                archives_structure[project_name] = {}
                            
                            if date_dir not in archives_structure[project_name]:
                                archives_structure[project_name][date_dir] = []
                                
                            archives_structure[project_name][date_dir].append(
                                os.path.join(date_path, archive)
                            )
        except (PermissionError, OSError) as e:
            if json_output:
                click.echo(json.dumps({
                    "success": False,
                    "error": str(e)
                }))
            else:
                click.echo(f"Error reading archives: {str(e)}", err=True)
            return 1
        
        # For each project, find the latest archive and delete the rest
        to_delete = []
        for project, dates in archives_structure.items():
            # Sort date dirs in reverse (newest first)
            sorted_dates = sorted(dates.keys(), reverse=True)
            
            # Keep track of what we've seen
            kept_for_project = False
            
            for date_dir in sorted_dates:
                for archive_path in dates[date_dir]:
                    if not kept_for_project:
                        # Keep this one (the latest)
                        kept_for_project = True
                    else:
                        # Delete older ones
                        to_delete.append(archive_path)
        
        if dry_run:
            space_would_free = 0
            for archive_path in to_delete:
                try:
                    space_would_free += get_dir_size(archive_path)
                except Exception:
                    pass
                    
            if json_output:
                click.echo(json.dumps({
                    "success": True,
                    "dry_run": True,
                    "would_free": space_would_free,
                    "formatted_would_free": format_size(space_would_free),
                    "to_delete_count": len(to_delete),
                    "size_before": size_before,
                    "formatted_size_before": format_size(size_before)
                }))
            else:
                click.echo(f"Would free approximately {format_size(space_would_free)} by removing {len(to_delete)} archives")
                click.echo("Use without --dry-run to actually remove files")
            return 0
        
        # If not dry run, actually remove the files
        if not dry_run:
            if not to_delete:
                if json_output:
                    click.echo(json.dumps({
                        "success": True,
                        "space_freed": 0,
                        "formatted_space_freed": "0 B",
                        "message": "No archives to remove. Each project has at most one archive."
                    }))
                else:
                    click.echo("No archives to remove. Each project has at most one archive.")
                return 0
                
            with click.progressbar(to_delete, label="Removing old archives") as bar:
                space_freed = 0
                success_count = 0
                errors = []
                
                for archive_path in bar:
                    try:
                        archive_size = get_dir_size(archive_path)
                        if os.path.isdir(archive_path):
                            shutil.rmtree(archive_path)
                        else:
                            os.remove(archive_path)
                        space_freed += archive_size
                        success_count += 1
                    except (PermissionError, OSError) as e:
                        errors.append(f"Could not remove {os.path.basename(archive_path)}: {str(e)}")
            
            if json_output:
                click.echo(json.dumps({
                    "success": success_count > 0,
                    "space_freed": space_freed,
                    "formatted_space_freed": format_size(space_freed),
                    "removed_count": success_count,
                    "total_to_remove": len(to_delete),
                    "errors": errors
                }))
            else:
                click.echo(f"Freed {format_size(space_freed)} by removing {success_count} of {len(to_delete)} archives")
                if errors:
                    click.echo("\nErrors encountered:")
                    for error in errors[:5]:  # Show only first 5 errors to avoid overwhelming output
                        click.echo(f"  - {error}")
                    if len(errors) > 5:
                        click.echo(f"  - ...and {len(errors) - 5} more errors")
            
            return 0
    else:
        # Regular cleanup (remove all archives)
        if json_output and dry_run:
            click.echo(json.dumps({
                "success": True,
                "dry_run": True,
                "size": size_before,
                "formatted_size": format_size(size_before)
            }))
            return 0
        
        if not json_output:
            click.echo(f"Archives size: {format_size(size_before)}")
            if dry_run:
                click.echo(f"Would free approximately {format_size(size_before)} (dry run)")
                return 0
        
        # Actually clean up
        space_freed = clean_xcode_path(archives_path, dry_run=False)
        
        if json_output:
            click.echo(json.dumps({
                "success": True,
                "space_freed": space_freed,
                "formatted_space_freed": format_size(space_freed),
                "size_before": size_before,
                "size_after": size_before - space_freed
            }))
        else:
            click.echo(f"Freed {format_size(space_freed)} of space from archives")
        
        return 0


@cleanup.command("device-support")
@click.option("--force", is_flag=True, help="Force cleanup even if directories appear to be in use")
@click.option("--dry-run", is_flag=True, help="Show what would be cleaned without actually removing files")
@click.option("--keep-latest", is_flag=True, help="Keep the most recent device support files for each iOS version")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
def cleanup_device_support(force, dry_run, keep_latest, json_output):
    """Clean Xcode device support files.
    
    Removes device support files for iOS/iPadOS devices.
    These can consume significant space over time.
    """
    device_support_path = "~/Library/Developer/Xcode/iOS DeviceSupport"
    
    if not check_xcode_path_exists(device_support_path):
        if json_output:
            click.echo(json.dumps({
                "success": False,
                "error": f"Device support directory not found at {device_support_path}"
            }))
        else:
            click.echo(f"Device support directory not found at {device_support_path}")
        return 1
    
    # Check if in use
    if not force and is_directory_in_use(device_support_path):
        if json_output:
            click.echo(json.dumps({
                "success": False,
                "error": "Device support directory appears to be in use. Use --force to clean anyway."
            }))
        else:
            click.echo("Warning: Device support directory appears to be in use.")
            click.echo("This may indicate that Xcode is currently using these files.")
            click.echo("Use --force to clean anyway, or close Xcode first.")
        return 1
    
    # Get size before cleaning
    size_before = get_xcode_path_size(device_support_path)
    
    expanded_path = os.path.expanduser(device_support_path)
    
    # Handle keep latest option
    if keep_latest:
        if json_output and dry_run:
            click.echo(json.dumps({
                "success": True,
                "dry_run": True,
                "size": size_before,
                "formatted_size": format_size(size_before),
                "note": "Would keep latest device support files for each iOS version"
            }))
            return 0
        
        if not json_output:
            click.echo(f"Device support size: {format_size(size_before)}")
            if dry_run:
                click.echo("Dry run: would keep the latest device support files for each iOS version")
        
        # Organize device support directories by iOS version
        # iOS device support directories are usually named like "12.4.1 (16G102)" or "13.0 (17A577)"
        ios_versions = {}
        
        try:
            for item in os.listdir(expanded_path):
                item_path = os.path.join(expanded_path, item)
                if os.path.isdir(item_path):
                    # Extract version from name (e.g. "12.4.1" from "12.4.1 (16G102)")
                    version_match = re.match(r'^(\d+\.\d+(?:\.\d+)?)', item)
                    if version_match:
                        version = version_match.group(1)
                        if version not in ios_versions:
                            ios_versions[version] = []
                        ios_versions[version].append(item_path)
        except (PermissionError, OSError) as e:
            if json_output:
                click.echo(json.dumps({
                    "success": False,
                    "error": str(e)
                }))
            else:
                click.echo(f"Error reading device support directory: {str(e)}", err=True)
            return 1
        
        # For each iOS version, keep only the latest directory
        to_delete = []
        for version, dirs in ios_versions.items():
            if len(dirs) > 1:
                # Sort by directory name in reverse order
                # This works because the build number in parentheses increases with newer builds
                sorted_dirs = sorted(dirs, reverse=True)
                # Keep the first one (latest), delete the rest
                to_delete.extend(sorted_dirs[1:])
        
        if dry_run:
            space_would_free = 0
            for dir_path in to_delete:
                try:
                    space_would_free += get_dir_size(dir_path)
                except Exception:
                    pass
            
            if json_output:
                click.echo(json.dumps({
                    "success": True,
                    "dry_run": True,
                    "would_free": space_would_free,
                    "formatted_would_free": format_size(space_would_free),
                    "to_delete_count": len(to_delete),
                    "size_before": size_before,
                    "formatted_size_before": format_size(size_before)
                }))
            else:
                click.echo(f"Would free approximately {format_size(space_would_free)} by removing {len(to_delete)} device support directories")
                click.echo("Use without --dry-run to actually remove files")
            return 0
        
        # If not dry run, actually remove the directories
        if not dry_run:
            if not to_delete:
                if json_output:
                    click.echo(json.dumps({
                        "success": True,
                        "space_freed": 0,
                        "formatted_space_freed": "0 B",
                        "message": "No device support directories to remove. Each iOS version has at most one directory."
                    }))
                else:
                    click.echo("No device support directories to remove. Each iOS version has at most one directory.")
                return 0
            
            with click.progressbar(to_delete, label="Removing old device support files") as bar:
                space_freed = 0
                success_count = 0
                errors = []
                
                for dir_path in bar:
                    try:
                        dir_size = get_dir_size(dir_path)
                        shutil.rmtree(dir_path)
                        space_freed += dir_size
                        success_count += 1
                    except (PermissionError, OSError) as e:
                        errors.append(f"Could not remove {os.path.basename(dir_path)}: {str(e)}")
            
            if json_output:
                click.echo(json.dumps({
                    "success": success_count > 0,
                    "space_freed": space_freed,
                    "formatted_space_freed": format_size(space_freed),
                    "removed_count": success_count,
                    "total_to_remove": len(to_delete),
                    "errors": errors
                }))
            else:
                click.echo(f"Freed {format_size(space_freed)} by removing {success_count} of {len(to_delete)} device support directories")
                if errors:
                    click.echo("\nErrors encountered:")
                    for error in errors[:5]:
                        click.echo(f"  - {error}")
                    if len(errors) > 5:
                        click.echo(f"  - ...and {len(errors) - 5} more errors")
            
            return 0
    else:
        # Regular cleanup (remove all device support files)
        if json_output and dry_run:
            click.echo(json.dumps({
                "success": True,
                "dry_run": True,
                "size": size_before,
                "formatted_size": format_size(size_before)
            }))
            return 0
        
        if not json_output:
            click.echo(f"Device support size: {format_size(size_before)}")
            if dry_run:
                click.echo(f"Would free approximately {format_size(size_before)} (dry run)")
                return 0
        
        # Actually clean up
        space_freed = clean_xcode_path(device_support_path, dry_run=False)
        
        if json_output:
            click.echo(json.dumps({
                "success": True,
                "space_freed": space_freed,
                "formatted_space_freed": format_size(space_freed),
                "size_before": size_before,
                "size_after": size_before - space_freed
            }))
        else:
            click.echo(f"Freed {format_size(space_freed)} of space from device support files")
        
        return 0


@cleanup.command("simulators")
@click.option("--force", is_flag=True, help="Force cleanup even if directories appear to be in use")
@click.option("--dry-run", is_flag=True, help="Show what would be cleaned without actually removing files")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
def cleanup_simulators(force, dry_run, json_output):
    """Clean iOS simulator caches and data.
    
    Removes data, caches, and tmp files from iOS simulators.
    Preserves simulator devices but cleans their content.
    """
    simulator_path = "~/Library/Developer/CoreSimulator/Devices"
    
    if not check_xcode_path_exists(simulator_path):
        if json_output:
            click.echo(json.dumps({
                "success": False,
                "error": f"Simulator directory not found at {simulator_path}"
            }))
        else:
            click.echo(f"Simulator directory not found at {simulator_path}")
        return 1
    
    # Check if in use
    if not force and is_directory_in_use(simulator_path):
        if json_output:
            click.echo(json.dumps({
                "success": False,
                "error": "Simulator directory appears to be in use. Use --force to clean anyway."
            }))
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
            click.echo(json.dumps({
                "success": False,
                "error": str(e)
            }))
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
            click.echo(json.dumps({
                "success": True,
                "dry_run": True,
                "data_size": data_size,
                "cache_size": cache_size,
                "total_size": data_size + cache_size,
                "formatted_data_size": format_size(data_size),
                "formatted_cache_size": format_size(cache_size),
                "formatted_total_size": format_size(data_size + cache_size)
            }))
        else:
            click.echo(f"Simulator data size: {format_size(data_size)}")
            click.echo(f"Simulator cache size: {format_size(cache_size)}")
            click.echo(f"Total would free: {format_size(data_size + cache_size)} (dry run)")
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
                    total_freed += (data_size - data_size_after)
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
                    total_freed += (cache_size - cache_size_after)
                except Exception as e:
                    errors.append(f"Error processing {cache_dir}: {str(e)}")
    
    if json_output:
        click.echo(json.dumps({
            "success": True,
            "space_freed": total_freed,
            "formatted_space_freed": format_size(total_freed),
            "errors": errors[:10]  # Only include first 10 errors to avoid huge JSON
        }))
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
@click.option("--force", is_flag=True, help="Force cleanup even if directories appear to be in use")
@click.option("--dry-run", is_flag=True, help="Show what would be cleaned without actually removing files")
@click.option("--keep-latest", is_flag=True, help="Keep latest archives and device support")
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
    returncode = cleanup_derived_data.callback(force=force, dry_run=dry_run, json_output=False)
    results["derived_data"] = {"success": returncode == 0}
    
    # Run archives cleanup
    click.echo("\nCleaning Xcode archives...")
    returncode = cleanup_archives.callback(force=force, dry_run=dry_run, keep_latest=keep_latest, json_output=False)
    results["archives"] = {"success": returncode == 0}
    
    # Run device support cleanup
    click.echo("\nCleaning device support files...")
    returncode = cleanup_device_support.callback(force=force, dry_run=dry_run, keep_latest=keep_latest, json_output=False)
    results["device_support"] = {"success": returncode == 0}
    
    # Run simulator cleanup
    click.echo("\nCleaning simulator files...")
    returncode = cleanup_simulators.callback(force=force, dry_run=dry_run, json_output=False)
    results["simulators"] = {"success": returncode == 0}
    
    # Calculate overall success
    overall_success = all(r["success"] for r in results.values())
    
    if json_output:
        click.echo(json.dumps({
            "success": overall_success,
            "results": results,
            "dry_run": dry_run,
            "keep_latest": keep_latest
        }, indent=2))
    else:
        click.echo("\nXcode cleanup completed.")
        if dry_run:
            click.echo("This was a dry run. Use --force to actually clean files.")
    
    return 0 if overall_success else 1

