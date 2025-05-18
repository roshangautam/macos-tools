"""Network management tools for macos-tools CLI."""

import json
import platform
import re
import subprocess
import time
from typing import Any, Dict, List, Optional, Tuple

import click


@click.group()
def network():
    """Network management tools.

    A collection of tools for managing and diagnosing network settings.
    """
    pass


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
            click.echo(
                json.dumps(
                    {
                        "success": False,
                        "error": "This command is only available on macOS",
                    }
                )
            )
        else:
            click.echo("Error: This command is only available on macOS", err=True)
        return 1

    # Confirm before proceeding
    if not force:
        if not click.confirm("Are you sure you want to flush the DNS cache?"):
            if json_output:
                click.echo(
                    json.dumps(
                        {"success": False, "message": "Operation cancelled by user"}
                    )
                )
            else:
                click.echo("Operation cancelled.")
            return 0

    # Determine macOS version to use appropriate command
    version = platform.mac_ver()[0]
    major_version = int(version.split(".")[0]) if version else 0

    try:
        click.echo("Flushing DNS cache...")

        with click.progressbar(length=100, label="Flushing DNS") as bar:
            bar.update(30)

            # Different commands for different macOS versions
            if major_version >= 12:  # macOS Monterey and newer
                cmd = ["sudo", "dscacheutil", "-flushcache"]
                result1 = subprocess.run(
                    cmd, capture_output=True, text=True, check=False
                )
                bar.update(50)

                cmd = ["sudo", "killall", "-HUP", "mDNSResponder"]
                result2 = subprocess.run(
                    cmd, capture_output=True, text=True, check=False
                )
                success = result1.returncode == 0 and result2.returncode == 0
                stderr = result1.stderr + result2.stderr
            else:  # Older macOS versions
                cmd = ["sudo", "killall", "-HUP", "mDNSResponder"]
                result = subprocess.run(
                    cmd, capture_output=True, text=True, check=False
                )
                success = result.returncode == 0
                stderr = result.stderr

            bar.update(100)

        if success:
            if json_output:
                click.echo(
                    json.dumps(
                        {"success": True, "message": "DNS cache flushed successfully"}
                    )
                )
            else:
                click.echo("DNS cache flushed successfully.")
        else:
            if json_output:
                click.echo(
                    json.dumps(
                        {
                            "success": False,
                            "error": "Failed to flush DNS cache",
                            "stderr": stderr,
                        }
                    )
                )
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
            click.echo(
                json.dumps(
                    {
                        "success": False,
                        "error": "This command is only available on macOS",
                    }
                )
            )
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
                    click.echo(
                        json.dumps(
                            {
                                "success": False,
                                "error": "Failed to get network interface information",
                            }
                        )
                    )
                else:
                    click.echo(
                        "Error: Failed to get network interface information", err=True
                    )
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
                    interface_info[current_interface]["addresses"].append(
                        {"type": addr_type, "address": addr, "netmask": mask}
                    )
                # Status and flags
                elif current_interface and "status:" in line.lower():
                    status = line.split("status:")[1].strip()
                    interface_info[current_interface]["status"] = status

            # Filter by specific interface if provided
            if interface:
                interface_info = {
                    k: v for k, v in interface_info.items() if k == interface
                }

            results["interfaces"] = interface_info

        # Get DNS information
        if dns:
            dns_info = {}

            # Get DNS servers
            try:
                dns_output = subprocess.run(
                    ["scutil", "--dns"], capture_output=True, text=True
                )

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
                route_output = subprocess.run(
                    ["netstat", "-nr"], capture_output=True, text=True
                )

                if route_output.returncode == 0:
                    # Process routing table output
                    lines = route_output.stdout.strip().split("\n")
                    headers = None

                    for line in lines:
                        if line.strip() and "Destination" in line:
                            # This is the header line
                            headers = [h for h in line.split() if h]
                        elif line.strip() and headers:
                            # This is a data line
                            parts = line.split()
                            if len(parts) >= len(headers):
                                route = {}
                                for i, header in enumerate(headers):
                                    route[header.lower()] = parts[i]
                                route_info.append(route)

                    # Filter by interface
                    if interface:
                        route_info = [
                            r for r in route_info if r.get("netif", "") == interface
                        ]

            except Exception as e:
                if json_output:
                    click.echo(json.dumps({"success": False, "error": str(e)}))
                else:
                    click.echo(f"Error getting routing information: {str(e)}", err=True)

            results["routes"] = route_info

        # Display the results
        if json_output:
            click.echo(json.dumps({"success": True, "results": results}))
        else:
            # Display interfaces
            if ip and "interfaces" in results:
                click.echo("\nNetwork Interfaces:")
                click.echo("==================")

                for iface, info in results["interfaces"].items():
                    click.echo(f"\n{iface}:")
                    if "status" in info:
                        click.echo(f"  Status: {info['status']}")

                    if "addresses" in info and info["addresses"]:
                        click.echo("  Addresses:")
                        for addr in info["addresses"]:
                            addr_type = addr.get("type", "unknown").upper()
                            address = addr.get("address", "N/A")
                            netmask = addr.get("netmask", "N/A")
                            click.echo(
                                f"    {addr_type}: {address} (Netmask: {netmask})"
                            )

            # Display DNS information
            if dns and "dns" in results:
                click.echo("\nDNS Configuration:")
                click.echo("=================")

                if "servers" in results["dns"] and results["dns"]["servers"]:
                    click.echo("\nDNS Servers:")
                    for server in results["dns"]["servers"]:
                        click.echo(f"  {server}")

                if (
                    "search_domains" in results["dns"]
                    and results["dns"]["search_domains"]
                ):
                    click.echo("\nSearch Domains:")
                    for domain in results["dns"]["search_domains"]:
                        click.echo(f"  {domain}")

                if "error" in results["dns"]:
                    click.echo(
                        f"\nError retrieving DNS information: {results['dns']['error']}"
                    )

            # Display routing information
            if routes and "routes" in results:
                click.echo("\nRouting Table:")
                click.echo("=============")

                if not results["routes"]:
                    click.echo("  No routes found.")
                else:
                    # Determine column widths
                    headers = ["destination", "gateway", "flags", "netif"]
                    widths = {h: len(h) for h in headers}

                    for route in results["routes"]:
                        for h in headers:
                            if h in route:
                                widths[h] = max(widths[h], len(route[h]))

                    # Print header
                    header = " | ".join(f"{h.upper():{widths[h]}}" for h in headers)
                    separator = "-+-".join("-" * widths[h] for h in headers)
                    click.echo(f"\n{header}")
                    click.echo(separator)

                    # Print routes
                    for route in results["routes"]:
                        row = " | ".join(
                            f"{route.get(h, ''):{widths[h]}}" for h in headers
                        )
                        click.echo(row)

        return 0

    except Exception as e:
        if json_output:
            click.echo(json.dumps({"success": False, "error": str(e)}))
        else:
            click.echo(f"Error: {str(e)}", err=True)
        return 1
