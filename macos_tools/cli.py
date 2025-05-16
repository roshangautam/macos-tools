"""
Command line interface for macOS tools.
"""
import os
import shutil
import time
import json
import socket
import subprocess
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple, Union
import click
import platform

@click.group()
@click.version_option()
def cli():
    """A collection of useful tools for macOS."""
    pass

@cli.command()
def system_info():
    """Display system information."""
    import platform
    import subprocess
    
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

@cli.command()
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

@cli.group()
def ports():
    """Port management tools.
    
    List, scan, and manage processes on network ports.
    """
    pass


# Common port groups for convenience
COMMON_PORTS = {
    "web": [80, 443, 3000, 8000, 8080, 8888],
    "db": [3306, 5432, 27017, 6379, 5672, 9200],
    "dev": [3000, 3001, 4200, 5000, 8000, 8080, 9000],
    "mail": [25, 465, 587, 993, 995],
}


def get_process_on_port(port: int) -> List[Dict[str, Any]]:
    """Get information about processes using a specific port."""
    try:
        # Use lsof to find processes using the port
        cmd = f"lsof -i :{port} -n -P"
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        
        if result.returncode != 0 or not result.stdout.strip():
            return []
        
        lines = result.stdout.strip().split('\n')
        if len(lines) <= 1:  # Only header
            return []
        
        processes = []
        # Skip header line
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 9:
                process = {
                    "command": parts[0],
                    "pid": int(parts[1]),
                    "user": parts[2],
                    "fd": parts[3],
                    "type": parts[4],
                    "protocol": parts[8].split(":")[0],
                    "port": port,
                    "state": parts[9] if len(parts) > 9 else "UNKNOWN"
                }
                processes.append(process)
        
        return processes
    except Exception as e:
        click.echo(f"Error checking port {port}: {str(e)}", err=True)
        return []


def scan_port_range(start_port: int, end_port: int) -> Dict[int, str]:
    """Scan a range of ports to determine status."""
    results = {}
    
    for port in range(start_port, end_port + 1):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.1)
            result = s.connect_ex(('127.0.0.1', port))
            status = "OPEN" if result == 0 else "CLOSED"
            results[port] = status
    
    return results


def format_port_processes(processes: List[Dict[str, Any]], json_output: bool = False) -> str:
    """Format process information for display."""
    if json_output:
        return json.dumps(processes, indent=2)
    
    if not processes:
        return "No processes found on specified port(s)."
    
    # Determine column widths
    headers = ["PID", "Command", "User", "Protocol", "Port", "State"]
    widths = {h: len(h) for h in headers}
    
    for proc in processes:
        widths["PID"] = max(widths["PID"], len(str(proc["pid"])))
        widths["Command"] = max(widths["Command"], len(proc["command"]))
        widths["User"] = max(widths["User"], len(proc["user"]))
        widths["Protocol"] = max(widths["Protocol"], len(proc["protocol"]))
        widths["Port"] = max(widths["Port"], len(str(proc["port"])))
        widths["State"] = max(widths["State"], len(proc["state"]))
    
    # Create header
    header = " | ".join(f"{h:{widths[h]}}" for h in headers)
    separator = "-+-".join("-" * widths[h] for h in headers)
    
    # Create rows
    rows = []
    for proc in processes:
        row = " | ".join([
            f"{proc['pid']:{widths['PID']}}", 
            f"{proc['command']:{widths['Command']}}", 
            f"{proc['user']:{widths['User']}}", 
            f"{proc['protocol']:{widths['Protocol']}}", 
            f"{proc['port']:{widths['Port']}}", 
            f"{proc['state']:{widths['State']}}"
        ])
        rows.append(row)
    
    return "\n".join([header, separator] + rows)


def resolve_port_list(ports_arg: Tuple[int], port_groups: List[str]) -> List[int]:
    """Resolve a list of ports from arguments and port groups."""
    resolved_ports = list(ports_arg)
    
    # Add ports from any port groups specified
    for group in port_groups:
        if group in COMMON_PORTS:
            resolved_ports.extend(COMMON_PORTS[group])
    
    # Remove duplicates and sort
    return sorted(list(set(resolved_ports)))


@ports.command("list")
@click.option("--port", "-p", type=int, multiple=True, help="Port(s) to check. Can be specified multiple times.")
@click.option("--web", is_flag=True, help=f"Include common web ports: {', '.join(str(p) for p in COMMON_PORTS['web'])}")
@click.option("--db", is_flag=True, help=f"Include common database ports: {', '.join(str(p) for p in COMMON_PORTS['db'])}")
@click.option("--dev", is_flag=True, help=f"Include common development ports: {', '.join(str(p) for p in COMMON_PORTS['dev'])}")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
def list_ports(port: Tuple[int], web: bool, db: bool, dev: bool, json_output: bool):
    """List processes using specific ports.
    
    If no ports are specified, checks commonly used ports.
    """
    port_groups = []
    if web:
        port_groups.append("web")
    if db:
        port_groups.append("db")
    if dev:
        port_groups.append("dev")
    
    # If no ports or groups specified, use web and dev ports by default
    if not port and not port_groups:
        port_groups = ["web", "dev"]
        click.echo("No ports specified. Checking common web and development ports.")
    
    ports_to_check = resolve_port_list(port, port_groups)
    
    if not ports_to_check:
        click.echo("No ports specified.")
        return
    
    click.echo(f"Checking {len(ports_to_check)} port(s): {', '.join(str(p) for p in ports_to_check)}")
    
    all_processes = []
    for port_num in ports_to_check:
        processes = get_process_on_port(port_num)
        all_processes.extend(processes)
    
    if not all_processes:
        click.echo("No processes found on specified port(s).")
        return
    
    # Display the results
    formatted_output = format_port_processes(all_processes, json_output)
    click.echo(formatted_output)


@ports.command("kill")
@click.option("--port", "-p", type=int, required=True, help="Port to kill processes on")
@click.option("--force", "-f", is_flag=True, help="Force kill (SIGKILL instead of SIGTERM)")
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
def kill_port(port: int, force: bool, yes: bool):
    """Kill processes using a specific port.
    
    Uses SIGTERM by default, or SIGKILL with --force.
    """
    processes = get_process_on_port(port)
    
    if not processes:
        click.echo(f"No processes found on port {port}.")
        return
    
    # Show the processes that will be killed
    click.echo(f"Found {len(processes)} process(es) on port {port}:")
    formatted_output = format_port_processes(processes)
    click.echo(formatted_output)
    
    # Confirm before killing
    if not yes:
        confirm = click.confirm(f"Kill {len(processes)} process(es) on port {port}?", default=False)
        if not confirm:
            click.echo("Operation cancelled.")
            return
    
    # Kill the processes
    signal = "-9" if force else "-15"
    success_count = 0
    
    for process in processes:
        pid = process["pid"]
        try:
            cmd = f"kill {signal} {pid}"
            result = subprocess.run(cmd, shell=True, capture_output=True)
            
            if result.returncode == 0:
                success_count += 1
                click.echo(f"Killed process {pid} ({process['command']})")
            else:
                click.echo(f"Failed to kill process {pid}: {result.stderr.decode('utf-8')}", err=True)
        except Exception as e:
            click.echo(f"Error killing process {pid}: {str(e)}", err=True)
    
    click.echo(f"Successfully killed {success_count} of {len(processes)} process(es).")


@ports.command("scan")
@click.option("--start", "-s", type=int, default=8000, help="Start of port range to scan")
@click.option("--end", "-e", type=int, default=9000, help="End of port range to scan")
@click.option("--common", "-c", is_flag=True, help="Scan common ports across different ranges")
@click.option("--open-only", "-o", is_flag=True, help="Show only open ports")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
def scan_ports(start: int, end: int, common: bool, open_only: bool, json_output: bool):
    """Scan a range of ports to determine which are open or in use.
    
    Defaults to scanning ports 8000-9000.
    """
    if end < start:
        click.echo("Error: End port must be greater than or equal to start port.", err=True)
        return
    
    ports_to_scan = []
    
    if common:
        # Combine all common port groups
        for group in COMMON_PORTS.values():
            ports_to_scan.extend(group)
        ports_to_scan = sorted(list(set(ports_to_scan)))
        click.echo(f"Scanning {len(ports_to_scan)} common ports...")
    else:
        # Scan the specified range
        if end - start > 1000:
            confirm = click.confirm(f"You're about to scan {end - start + 1} ports, which may take a while. Continue?", default=False)
            if not confirm:
                click.echo("Operation cancelled.")
                return
        
        ports_to_scan = list(range(start, end + 1))
        click.echo(f"Scanning port range {start}-{end} ({len(ports_to_scan)} ports)...")
    
    # Create a progress bar
    with click.progressbar(ports_to_scan, label="Scanning ports") as bar:
        results = {}
        for port in bar:
            # Check if port is open
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.1)
                result = s.connect_ex(('127.0.0.1', port))
                status = "OPEN" if result == 0 else "CLOSED"
                
                if not open_only or status == "OPEN":
                    results[port] = status
    
    # Get details for open ports
    for port, status in list(results.items()):
        if status == "OPEN":
            processes = get_process_on_port(port)
            if processes:
                command = processes[0]["command"]
                pid = processes[0]["pid"]
                results[port] = f"OPEN (PID: {pid}, Process: {command})"
    
    # Format output
    if json_output:
        click.echo(json.dumps(results, indent=2))
    else:
        if not results:
            click.echo("No ports found matching criteria.")
            return
        
        # Calculate column widths
        port_width = max(len("PORT"), max(len(str(p)) for p in results.keys()))
        status_width = max(len("STATUS"), max(len(str(s)) for s in results.values()))
        
        # Print header
        click.echo(f"{'PORT':{port_width}} | {'STATUS':{status_width}}")
        click.echo(f"{'-' * port_width} | {'-' * status_width}")
        
        # Print results
        for port in sorted(results.keys()):
            click.echo(f"{port:{port_width}} | {results[port]:{status_width}}")
        
        click.echo(f"\nFound {len(results)} port(s) matching criteria.")


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
    """Parse the output of 'brew --cache' and get sizes of Homebrew directories."""
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


@cli.group()
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
            potential_savings = sum(size for file, size in re.findall(r"(\S+) \((\d+) bytes\)", stdout))
            if potential_savings:
                click.echo(f"Potential space savings: {format_size(int(potential_savings))}")
    
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


@cli.group()
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
@click.option("--force", is_flag=True, help="Force cleanup even if simulators appear to be in use")
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
            "errors": errors
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


@cli.group()
def network():
    """Network management tools.
    
    A collection of tools for managing and diagnosing network settings.
    """
    pass


def check_docker_installed() -> bool:
    """Check if Docker is installed and available."""
    try:
        result = subprocess.run(
            ["docker", "--version"], 
            stdout=subprocess.PIPE, 
            stderr=subprocess.PIPE, 
            check=False
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
            check=False
        )
        return result.returncode == 0
    except Exception:
        return False


def run_docker_command(command: List[str], capture_json: bool = False, streaming: bool = False) -> Tuple[int, Any, str]:
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
        return 1, None if capture_json else "", "Docker is not installed on this system."
    
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
        stdout_data = "".join(stdout_lines)
        stderr_data = "".join(stderr_lines)
    else:
        # For commands where we want to capture and process output
        result = subprocess.run(
            full_command, 
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
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


@cli.group()
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
@click.option("--all", "all_containers", is_flag=True, help="Remove all containers, not just stopped ones")
@click.option("--force", "-f", is_flag=True, help="Force removal of containers")
@click.option("--dry-run", is_flag=True, help="Show what would be removed without removing anything")
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
    filter_arg = "" if all_containers else "--filter status=exited --filter status=created --filter status=dead"
    
    return_code, containers, stderr = run_docker_command(
        ["ps", "-a", "--format", "{{json .}}"] + filter_arg.split(),
        capture_json=False
    )
    
    if return_code != 0:
        if json_output:
            click.echo(json.dumps({"error": stderr}))
        else:
            click.echo(f"Error listing containers: {stderr}", err=True)
        return return_code
    
    # Parse container list (each line is a JSON object)
    container_list = []
    for line in containers.strip().split('\n'):
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
            click.echo(f"Found {len(container_list)} stopped containers that would be removed:")
        
        # Calculate column widths
        id_width = max(10, max(len(c.get("ID", "")[:12]) for c in container_list))
        name_width = max(10, max(len(c.get("Names", "")) for c in container_list))
        image_width = max(15, max(len(c.get("Image", "")) for c in container_list))
        status_width = max(10, max(len(c.get("Status", "")) for c in container_list))
        
        # Header
        click.echo(f"{'CONTAINER ID':{id_width}} | {'IMAGE':{image_width}} | {'STATUS':{status_width}} | {'NAMES':{name_width}}")
        click.echo(f"{'-' * id_width} | {'-' * image_width} | {'-' * status_width} | {'-' * name_width}")
        
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
                "count": len(container_list)
            }
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo("\nDry run complete. Use without --dry-run to actually remove containers.")
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
    
    return_code, stdout, stderr = run_docker_command(rm_cmd + container_ids, streaming=True)
    
    if return_code == 0:
        if json_output:
            result = {
                "success": True,
                "removed_count": len(container_list),
                "containers": container_list
            }
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"Successfully removed {len(container_list)} containers.")
    else:
        if json_output:
            result = {
                "success": False,
                "error": stderr,
                "removed_count": 0
            }
            click.echo(json.dumps(result, indent=2))
        else:
            click.echo(f"Error removing containers: {stderr}", err=True)
    
    return return_code


@cleanup.command("images")
@click.option("--all", "all_images", is_flag=True, help="Remove all images, not just dangling ones")
@click.option("--force", "-f", is_flag=True, help="Force removal of images")
@click.option("--dry-run", is_flag=True, help="Show what would be removed without removing anything")
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
    filter_arg = "--filter dangling=true" if not all_images else "--filter dangling=true --filter dangling=false"
    
    return_code, images, stderr = run_docker_command(
        ["images", "--format", "{{json .}}"] + filter_arg.split(),
        capture_json=False
    )
    
    if return_code != 0:
        if json_output:
            click.echo(json.dumps({"error": stderr}))
        else:
            click.echo(f"Error listing images: {stderr}", err=True)
        return return_code
    
    # Parse image list (each line is a JSON object)
    image_list = []
    for line in images.strip().split('\n'):
        if line:
            try:
                image_list.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    
    # Filter out images that are in use
    if not all_images:
        # Get list of images used by containers
        return_code, containers, stderr = run_docker_command(
            ["ps", "-a", "--format", "{{.Image}}"],
            capture_json=False
        )
        
        if return_code == 0:
            used_images = containers.strip().split('\n')
            image_list = [img for img in image_list if img.get("Repository") + ":" + img.get("Tag") not in used_images]
    
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
            click.echo(f"Found {len(image_list)} images that would be removed (approx. {format_size(total_size)}):")
        else:
            click.echo(f"Found {len(image_list)} unused images that would be removed (approx. {format_size(total_size)}):")
        
        # Calculate column widths
        repo_width = max(12, max(len(i.get("Repository", "")) for i in image_list))
        tag_width = max(8, max(len(i.get("Tag", "")) for i in image_list))
        id_width = max(12, max(len(i.get("ID", "")[:12]) for i in image_list))
        size_width = max(8, max(len(i.get("Size", "")) for i in image_list))
        
        # Header
        click.echo(f"{'REPOSITORY':{repo_width}} | {'TAG':{tag_width}} | {'IMAGE ID':{id_width}} | {'SIZE':{size_width}}")
        click.echo(f"{'-' * repo_width} | {'-' * tag_width} | {'-' * id_width} | {'-' * size_width}")
        
        # Image list
        for image in image_list:
            click.echo(
                f"{image.get('


@network.command("dns-flush")
@click.option("--force", "-f", is_flag=True, help="Skip confirmation prompt")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
def flush_dns(force, json_output):
    """Flush DNS cache on macOS.
    
    This clears the DNS cache, which can resolve DNS-related connection issues.
    """
    # Check if we're on macOS
    if platform.system() != "Darwin":
        if json_output:
            click.echo(json.dumps({"success": False, "error": "This command is only available on macOS"}))
        else:
            click.echo("Error: This command is only available on macOS", err=True)
        return 1
    
    # Confirm before proceeding
    if not force:
        if not click.confirm("Are you sure you want to flush the DNS cache?"):
            if json_output:
                click.echo(json.dumps({"success": False, "message": "Operation cancelled by user"}))
            else:
                click.echo("Operation cancelled.")
            return 0
    
    # Determine macOS version to use appropriate command
    version = platform.mac_ver()[0]
    major_version = int(version.split('.')[0]) if version else 0

    try:
        click.echo("Flushing DNS cache...")
        
        with click.progressbar(length=100, label="Flushing DNS") as bar:
            bar.update(30)
            
            # Different commands for different macOS versions
            if major_version >= 12:  # macOS Monterey and newer
                cmd = ["sudo", "dscacheutil", "-flushcache"]
                result1 = subprocess.run(cmd, capture_output=True, text=True, check=False)
                bar.update(50)
                
                cmd = ["sudo", "killall", "-HUP", "mDNSResponder"]
                result2 = subprocess.run(cmd, capture_output=True, text=True, check=False)
                success = result1.returncode == 0 and result2.returncode == 0
                stderr = result1.stderr + result2.stderr
            else:  # Older macOS versions
                cmd = ["sudo", "killall", "-HUP", "mDNSResponder"]
                result = subprocess.run(cmd, capture_output=True, text=True, check=False)
                success = result.returncode == 0
                stderr = result.stderr
            
            bar.update(100)
        
        if success:
            if json_output:
                click.echo(json.dumps({"success": True, "message": "DNS cache flushed successfully"}))
            else:
                click.echo("DNS cache flushed successfully.")
        else:
            if json_output:
                click.echo(json.dumps({
                    "success": False, 
                    "error": "Failed to flush DNS cache", 
                    "stderr": stderr
                }))
            else:
                click.echo(f"Error: Failed to flush DNS cache\n{stderr}", err=True)
                click.echo("Note: This command may require administrative privileges.")
        
        return 0 if success else 1
    
    except Exception as e:
        if json_output:
            click.echo(json.dumps({"success": False, "error": str(e)}))
        else:
            click.echo(f"Error: {str(e)}", err=True)
        return 1


@network.command("info")
@click.option("--interface", "-i", help="Specific interface to show (e.g., en0, en1)")
@click.option("--dns", is_flag=True, help="Show only DNS information")
@click.option("--ip", is_flag=True, help="Show only IP information")
@click.option("--routes", is_flag=True, help="Show routing information")
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
def network_info(interface, dns, ip, routes, json_output):
    """Show network interface information.
    
    Displays detailed information about network interfaces, including
    IP addresses, DNS settings, and routing information.
    """
    # Check if we're on macOS
    if platform.system() != "Darwin":
        if json_output:
            click.echo(json.dumps({"success": False, "error": "This command is only available on macOS"}))
        else:
            click.echo("Error: This command is only available on macOS", err=True)
        return 1
    
    results = {}
    
    try:
        # If no specific filter is selected, show all
        if not any([dns, ip, routes]):
            dns = ip = routes = True
        
        # Get network interfaces
        if ip:
            result = subprocess.run(["ifconfig"], capture_output=True, text=True)
            
            if result.returncode != 0:
                if json_output:
                    click.echo(json.dumps({"success": False, "error": "Failed to get network interface information"}))
                else:
                    click.echo("Error: Failed to get network interface information", err=True)
                return 1
            
            # Parse ifconfig output for interfaces
            interface_info = {}
            current_interface = None
            
            for line in result.stdout.splitlines():
                # New interface definition
                if line and not line.startswith("\t"):
                    interface_name = line.split(":")[0].strip()
                    current_interface = interface_name
                    interface_info[current_interface] = {"addresses": []}
                # IP address lines
                elif current_interface and "inet " in line:
                    parts = line.strip().split()
                    addr_type = "ipv4" if "inet " in line else "ipv6"
                    addr = parts[1]
                    mask = parts[3] if "inet " in line else parts[3].split("/")[1]
                    interface_info[current_interface]["addresses"].append({
                        "type": addr_type,
                        "address": addr,
                        "netmask": mask
                    })
                # Status and flags
                elif current_interface and "status:" in line.lower():
                    status = line.split("status:")[1].strip()
                    interface_info[current_interface]["status"] = status
            
            # Filter by specific interface if provided
            if interface:
                interface_info = {k: v for k, v in interface_info.items() if k == interface}
            
            results["interfaces"] = interface_info
        
        # Get DNS information
        if dns:
            dns_info = {}
            
            # Get DNS servers
            try:
                dns_output = subprocess.run(["scutil", "--dns"], capture_output=True, text=True)
                
                if dns_output.returncode == 0:
                    dns_servers = []
                    for line in dns_output.stdout.splitlines():
                        if "nameserver" in line:
                            server = line.split("[")[1].split("]")[0].strip()
                            dns_servers.append(server)
                    
                    dns_info["servers"] = list(set(dns_servers))  # Remove duplicates
                    
                    # Get search domains
                    search_domains = []
                    for line in dns_output.stdout.splitlines():
                        if "search domain" in line:
                            domain = line.split("[")[1].split("]")[0].strip()
                            search_domains.append(domain)
                    
                    dns_info["search_domains"] = list(set(search_domains))
            except Exception as e:
                dns_info["error"] = str(e)
            
            results["dns"] = dns_info
        
        # Get routing information
        if routes:
            route_info = []
            
            try:
                route_output = subprocess.run(["netstat", "-nr"], capture_output=True, text=True)
                
                if route_output.returncode == 0:
                    in_
