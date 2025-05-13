"""
Console output formatting utilities for the Fluence CLI.
"""

from typing import List, Dict, Any, Optional
from rich.console import Console
from rich.table import Table

# Initialize a global console instance
console = Console()


def format_vm_table(vms: List[Dict[str, Any]]) -> Table:
    """
    Format a list of VMs as a rich table.
    
    Args:
        vms: List of VM data dictionaries
        
    Returns:
        Rich Table object for display
    """
    table = Table(show_header=True)
    table.add_column("ID", style="cyan")
    table.add_column("Name", style="green")
    table.add_column("Status", style="yellow")
    table.add_column("IP Address", style="blue")
    table.add_column("CPU", style="magenta")
    table.add_column("Memory", style="magenta")
    table.add_column("Region", style="red")
    
    for vm in vms:
        table.add_row(
            vm.get("id", ""),
            vm.get("name", ""),
            vm.get("status", ""),
            vm.get("ip_address", ""),
            str(vm.get("cpu", "")),
            f"{vm.get('memory', '')} GB",
            vm.get("region", "")
        )
    
    return table


def format_vm_details(vm: Dict[str, Any]) -> Table:
    """
    Format VM details as a rich table.
    
    Args:
        vm: VM data dictionary
        
    Returns:
        Rich Table object for display
    """
    table = Table(show_header=False, box=None)
    table.add_column("Property", style="green")
    table.add_column("Value", style="yellow")
    
    # Add primary details
    table.add_row("ID", vm.get("id", ""))
    table.add_row("Name", vm.get("name", ""))
    table.add_row("Status", vm.get("status", ""))
    table.add_row("IP Address", vm.get("ip_address", "") or "None")
    table.add_row("CPU", str(vm.get("cpu", "")))
    table.add_row("Memory", f"{vm.get('memory', '')} GB")
    table.add_row("Region", vm.get("region", ""))
    
    # Add additional details
    if "created_at" in vm:
        table.add_row("Created At", vm.get("created_at", ""))
    
    if "storage" in vm:
        table.add_row("Storage", f"{vm.get('storage', '')} GB")
    
    return table


def format_config_table(configs: List[str]) -> Table:
    """
    Format configuration list as a rich table.
    
    Args:
        configs: List of configuration strings
        
    Returns:
        Rich Table object for display
    """
    table = Table(show_header=True)
    table.add_column("Configuration", style="cyan")
    table.add_column("CPU", style="green")
    table.add_column("RAM (GB)", style="yellow")
    table.add_column("Storage (GB)", style="blue")
    
    for config_str in configs:
        # Parse configuration string (format: cpu-X-ram-Ygb-storage-Zgb)
        parts = config_str.split('-')
        cpu = "N/A"
        ram = "N/A"
        storage = "N/A"
        
        for i in range(len(parts)):
            if parts[i] == "cpu" and i + 1 < len(parts):
                cpu = parts[i + 1]
            elif parts[i] == "ram" and i + 1 < len(parts):
                ram = parts[i + 1].replace("gb", "")
            elif parts[i] == "storage" and i + 1 < len(parts):
                storage = parts[i + 1].replace("gb", "")
        
        table.add_row(config_str, cpu, ram, storage)
    
    return table


def print_error(message: str) -> None:
    """
    Print an error message in red.
    
    Args:
        message: Error message to print
    """
    console.print(f"[bold red]Error: {message}[/bold red]")


def print_warning(message: str) -> None:
    """
    Print a warning message in yellow.
    
    Args:
        message: Warning message to print
    """
    console.print(f"[yellow]{message}[/yellow]")


def print_success(message: str) -> None:
    """
    Print a success message in green.
    
    Args:
        message: Success message to print
    """
    console.print(f"[green]{message}[/green]")