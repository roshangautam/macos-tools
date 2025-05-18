"""Port management tools for macos-tools CLI."""

import socket
import subprocess
from typing import Any, Dict, List, Optional, Tuple

import click

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

        lines = result.stdout.strip().split("\n")
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
                    "state": parts[9] if len(parts) > 9 else "UNKNOWN",
                }
                processes.append(process)

        return processes
    except Exception as e:
        click.echo(f"Error checking port {port}: {str(e)}", err=True)
        return []


@click.group()
def ports():
    """Port management tools.

    List, scan, and manage processes on network ports.
    """
    pass


@ports.command("list")
@click.option(
    "--port",
    "-p",
    type=int,
    multiple=True,
    help="Port(s) to check. Can be specified multiple times.",
)
@click.option(
    "--web",
    is_flag=True,
    help=f"Include common web ports: {', '.join(str(p) for p in COMMON_PORTS['web'])}",
)
@click.option(
    "--db",
    is_flag=True,
    help=f"Include common database ports: {', '.join(str(p) for p in COMMON_PORTS['db'])}",
)
@click.option(
    "--dev",
    is_flag=True,
    help=f"Include common development ports: {', '.join(str(p) for p in COMMON_PORTS['dev'])}",
)
@click.option(
    "--mail",
    is_flag=True,
    help=f"Include common mail ports: {', '.join(str(p) for p in COMMON_PORTS['mail'])}",
)
@click.option(
    "--all-common",
    "-a",
    is_flag=True,
    help="Include all common ports from all categories",
)
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
def list_ports(
    port: Tuple[int],
    web: bool,
    db: bool,
    dev: bool,
    mail: bool,
    all_common: bool,
    json_output: bool,
):
    """List processes using specific ports.

    If no ports are specified, checks commonly used ports.
    """
    ports_to_check = set(port)

    # Add ports from common categories if specified
    if web or all_common:
        ports_to_check.update(COMMON_PORTS["web"])
    if db or all_common:
        ports_to_check.update(COMMON_PORTS["db"])
    if dev or all_common:
        ports_to_check.update(COMMON_PORTS["dev"])
    if mail or all_common:
        ports_to_check.update(COMMON_PORTS["mail"])

    # If no ports specified and no common ports selected, use all common ports
    if not ports_to_check and not (web or db or dev or mail or all_common):
        click.echo("No specific ports provided. Checking all common ports...")
        all_common = True
        for category in COMMON_PORTS.values():
            ports_to_check.update(category)

    if not ports_to_check:
        click.echo("No ports to check. Please specify ports or use common port groups.")
        return

    results = {}
    for port_num in sorted(ports_to_check):
        processes = get_process_on_port(port_num)
        if processes:
            results[port_num] = processes

    if json_output:
        import json

        click.echo(json.dumps(results, indent=2))
    else:
        if not results:
            click.echo("No processes found using the specified ports.")
            return

        for port_num, processes in results.items():
            click.echo(f"\nPort {port_num} is in use by:")
            for i, proc in enumerate(processes, 1):
                click.echo(
                    f"  {i}. PID: {proc['pid']}, Command: {proc['command']}, User: {proc['user']}, Protocol: {proc['protocol']}, State: {proc['state']}"
                )


@ports.command("kill")
@click.option("--port", "-p", type=int, required=True, help="Port to kill processes on")
@click.option(
    "--force", "-f", is_flag=True, help="Force kill (SIGKILL instead of SIGTERM)"
)
@click.option("--yes", "-y", is_flag=True, help="Skip confirmation prompt")
@click.option(
    "--signal",
    "-s",
    type=str,
    default=None,
    help="Specify signal to send (e.g., 9, 15, TERM, KILL)",
)
def kill_port(port: int, force: bool, yes: bool, signal: Optional[str]):
    """Kill processes using a specific port.

    Uses SIGTERM by default, or SIGKILL with --force.
    You can also specify a custom signal with --signal.
    """
    processes = get_process_on_port(port)
    if not processes:
        click.echo(f"No processes found using port {port}.")
        return

    # Prepare signal
    sig = signal
    if sig is None:
        sig = "KILL" if force else "TERM"

    # Show processes to be killed
    click.echo(f"The following processes are using port {port}:")
    for proc in processes:
        click.echo(
            f"  - PID: {proc['pid']}, Command: {proc['command']}, User: {proc['user']}"
        )

    # Confirm before killing
    if not yes:
        if not click.confirm(
            f"\nAre you sure you want to send SIG{sig} to these processes?"
        ):
            return

    # Kill processes
    success = 0
    for proc in processes:
        try:
            import signal as sig_lib

            sig_num = getattr(sig_lib, f"SIG{sig}", None) or int(sig)
            subprocess.run(["kill", f"-{sig_num}", str(proc["pid"])], check=True)
            click.echo(f"Sent SIG{sig} to process {proc['pid']} ({proc['command']})")
            success += 1
        except (subprocess.CalledProcessError, (ValueError, AttributeError)) as e:
            click.echo(f"Failed to kill process {proc['pid']}: {str(e)}", err=True)

    if success > 0:
        click.echo(f"Successfully sent signal to {success} process(es).")
    else:
        click.echo("No processes were terminated.", err=True)


def is_port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    """Check if a port is open and listening."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            return result == 0
    except (socket.timeout, ConnectionRefusedError):
        return False
    except Exception as e:
        click.echo(f"Error checking port {port}: {str(e)}", err=True)
        return False


@ports.command("scan")
@click.option(
    "--start", "-s", type=int, default=8000, help="Start of port range to scan"
)
@click.option("--end", "-e", type=int, default=9000, help="End of port range to scan")
@click.option(
    "--common", "-c", is_flag=True, help="Scan common ports across different ranges"
)
@click.option("--open-only", "-o", is_flag=True, help="Show only open ports")
@click.option(
    "--host", "-h", default="localhost", help="Host to scan (default: localhost)"
)
@click.option(
    "--timeout",
    "-t",
    type=float,
    default=0.5,
    help="Connection timeout in seconds (default: 0.5)",
)
@click.option("--json", "json_output", is_flag=True, help="Output in JSON format")
def scan_ports(
    start: int,
    end: int,
    common: bool,
    open_only: bool,
    host: str,
    timeout: float,
    json_output: bool,
):
    """Scan a range of ports to determine which are open or in use.

    Defaults to scanning ports 8000-9000 on localhost.
    """
    if start < 1 or end > 65535 or start > end:
        click.echo(
            "Invalid port range. Ports must be between 1 and 65535, and start must be less than or equal to end.",
            err=True,
        )
        return

    # Prepare ports to scan
    ports_to_scan = set(range(start, end + 1))

    if common:
        # Add all common ports from all categories
        for category_ports in COMMON_PORTS.values():
            ports_to_scan.update(category_ports)

    # Scan ports
    results = {}
    with click.progressbar(
        sorted(ports_to_scan),
        label=f"Scanning ports on {host}",
        show_eta=False,
        item_show_func=lambda p: f"Port {p}" if p else "",
    ) as ports:
        for port in ports:
            is_open = is_port_open(host, port, timeout)
            processes = get_process_on_port(port) if is_open else []

            if not open_only or is_open:
                results[port] = {"open": is_open, "processes": processes}

    # Output results
    if json_output:
        import json

        click.echo(json.dumps(results, indent=2))
    else:
        if not results:
            click.echo("No ports matched the scan criteria.")
            return

        click.echo(f"\nPort Scan Results for {host}:")
        click.echo("=" * 40)

        for port, info in sorted(results.items()):
            status = "OPEN" if info["open"] else "CLOSED"
            processes = info["processes"]

            if info["open"]:
                if processes:
                    proc_info = ", ".join(
                        f"{p['command']} (PID: {p['pid']})" for p in processes
                    )
                    click.echo(f"Port {port}: {status} - Used by {proc_info}")
                else:
                    click.echo(
                        f"Port {port}: {status} - No process found (port might be in TIME_WAIT state)"
                    )
            elif not open_only:
                click.echo(f"Port {port}: {status}")
