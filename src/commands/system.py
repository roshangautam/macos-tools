"""System management tools for macos-tools CLI."""

import os
import shutil
import time
import subprocess
import platform
from typing import Dict, Any
import click

def format_size(size_bytes):
    """Format bytes into a human-readable format."""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
    
    return f"{size_bytes:.2f} {size_names[i]}"

def get_dir_size(path):
    """Calculate the total size of a directory."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(path):
        for fname in filenames:
            file_path = os.path.join(dirpath, fname)
            try:
                total_size += os.path.getsize(file_path)
            except (OSError, FileNotFoundError):
                pass
    return total_size

@click.group()
def system():
    """System management tools.
    
    A collection of tools for managing system information and maintenance.
    """
    pass

@system.command()
def info():
    """Display system information."""
    # Get system information
    system = platform.system()
    version = platform.mac_ver()[0] if system == 'Darwin' else 'N/A'
    processor = platform.processor()
    
    # Get memory info using vm_stat command
    try:
        vm_stat = subprocess.check_output(['vm_stat']).decode('utf-8')
        memory_lines = vm_stat.splitlines()
        page_size = 4096  # Default page size on macOS (4KB)
        
        # Extract memory information
        memory_info = {}
        for line in memory_lines:
            if ':' in line:
                key, value = line.split(':')
                if value.strip().endswith('.'):
                    memory_info[key.strip()] = int(value.strip()[:-1]) * page_size
    except Exception as e:
        memory_info = {"Error": str(e)}
    
    # Display information
    click.echo(f"System: {system}")
    click.echo(f"macOS Version: {version}")
    click.echo(f"Processor: {processor}")
    
    # Display memory information
    click.echo("\nMemory Information:")
    for key, value in memory_info.items():
        # Convert to MB for better readability
        if isinstance(value, int):
            click.echo(f"{key}: {value / (1024 * 1024):.2f} MB")
        else:
            click.echo(f"{key}: {value}")

@system.command()
@click.option('--force', is_flag=True, help='Actually perform cleanup instead of simulating')
@click.option('--caches', is_flag=True, help='Clean ~/Library/Caches')
@click.option('--logs', is_flag=True, help='Clean ~/Library/Logs')
@click.option('--app-caches', is_flag=True, help='Clean ~/Library/Application Support/Caches')
@click.option('--tmp', is_flag=True, help='Clean /tmp directory')
@click.option('--var-folders', is_flag=True, help='Clean /private/var/folders (use with caution)')
@click.option('--all', 'clean_all', is_flag=True, help='Clean all temporary directories')
def cleanup_temp(force, caches, logs, app_caches, tmp, var_folders, clean_all):
    """Clean up temporary files.
    
    By default, this command runs in simulation mode showing what would be cleaned.
    Use --force to actually perform the cleanup operation.
    
    Use specific flags to control which directories to clean, or --all for everything.
    """
    # Define temp directories with safety checks
    temp_dirs = {}
    home = os.path.expanduser("~")
    
    temp_dirs['caches'] = {
        'path': os.path.join(home, "Library/Caches"),
        'safe_to_remove': True,
        'enabled': caches or clean_all,
        'description': "User caches"
    }
    
    temp_dirs['logs'] = {
        'path': os.path.join(home, "Library/Logs"),
        'safe_to_remove': True,
        'enabled': logs or clean_all,
        'description': "Log files"
    }
    
    temp_dirs['app_caches'] = {
        'path': os.path.join(home, "Library/Application Support/Caches"),
        'safe_to_remove': True,
        'enabled': app_caches or clean_all,
        'description': "Application support caches"
    }
    
    temp_dirs['tmp'] = {
        'path': "/tmp",
        'safe_to_remove': False,  # Don't delete the directory itself, just contents
        'enabled': tmp or clean_all,
        'description': "Temporary files",
        'exclude_patterns': ['.X*', '.lock*', 'com.apple.*']  # Critical system files to keep
    }
    
    temp_dirs['var_folders'] = {
        'path': "/private/var/folders",
        'safe_to_remove': False,  # Don't delete the directory itself, just contents
        'enabled': var_folders or clean_all,
        'description': "System temp files",
        'exclude_patterns': ['**/C/*', '**/T/com.apple*']  # Critical system files to keep
    }
    
    # If no specific directories are selected, show info message and enable caches and tmp by default
    if not (caches or logs or app_caches or tmp or var_folders or clean_all):
        click.echo("No directories specified. Using default: --caches --tmp")
        temp_dirs['caches']['enabled'] = True
        temp_dirs['tmp']['enabled'] = True
    
    total_freed = 0
    total_would_free = 0
    
    # Process each directory
    for dir_name, dir_info in temp_dirs.items():
        if not dir_info['enabled']:
            continue
            
        dir_path = dir_info['path']
        if not os.path.exists(dir_path):
            click.echo(f"Directory {dir_path} does not exist. Skipping.")
            continue
            
        # Get initial size
        try:
            size_before = get_dir_size(dir_path)
            click.echo(f"\nAnalyzing {dir_info['description']}: {dir_path}")
            click.echo(f"Current size: {format_size(size_before)}")
            
            if force:
                click.echo(f"Cleaning {dir_path}...")
                
                # Clean the directory
                if dir_info['safe_to_remove']:
                    # For directories safe to remove entirely
                    with click.progressbar(os.listdir(dir_path), label=f"Cleaning {dir_info['description']}") as items:
                        for item in items:
                            item_path = os.path.join(dir_path, item)
                            try:
                                if os.path.isdir(item_path):
                                    shutil.rmtree(item_path, ignore_errors=True)
                                else:
                                    os.remove(item_path)
                                time.sleep(0.01)  # Small delay for progress bar visibility
                            except (PermissionError, OSError) as e:
                                click.echo(f"\nSkipping {item_path}: {str(e)}", err=True)
                else:
                    # For directories we need to be careful with
                    exclude_patterns = dir_info.get('exclude_patterns', [])
                    items = []
                    
                    # First, gather all items that are safe to delete
                    for root, dirs, files in os.walk(dir_path, topdown=True):
                        # Skip excluded patterns
                        from pathlib import Path
                        for pattern in exclude_patterns:
                            dirs[:] = [d for d in dirs if not Path(os.path.join(root, d)).match(pattern)]
                            files[:] = [f for f in files if not Path(os.path.join(root, f)).match(pattern)]
                        
                        for file in files:
                            file_path = os.path.join(root, file)
                            items.append(file_path)
                    
                    # Then clean them with a progress bar
                    with click.progressbar(items, label=f"Cleaning {dir_info['description']}") as progress_items:
                        for item_path in progress_items:
                            try:
                                os.remove(item_path)
                                time.sleep(0.005)  # Small delay for progress bar visibility
                            except (PermissionError, OSError):
                                pass  # Silently skip files we can't delete
                
                # Calculate space freed
                size_after = get_dir_size(dir_path)
                freed = size_before - size_after
                total_freed += freed
                click.echo(f"Freed {format_size(freed)} of space")
            else:
                # Simulation mode
                click.echo(f"Would clean {dir_path} (simulation mode)")
                total_would_free += size_before
                click.echo(f"Would free approximately {format_size(size_before)}")
                
        except Exception as e:
            click.echo(f"Error processing {dir_path}: {str(e)}", err=True)
    
    # Show summary
    if force:
        click.echo(f"\nTotal space freed: {format_size(total_freed)}")
    else:
        click.echo(f"\nTotal space that would be freed: {format_size(total_would_free)}")
        click.echo("Note: This was just a simulation. Add --force to actually perform cleanup.")

