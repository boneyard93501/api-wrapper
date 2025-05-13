"""
VM management commands for the Fluence CLI with estimate command.
"""

import sys
import time
import uuid
import json
import click

from fluence_cli.api import FluenceAPIClient
from fluence_cli.config import get_config
from fluence_cli.utils.console import console, format_vm_table, format_vm_details, print_error, print_warning, print_success
from fluence_cli.utils.progress import wait_for_vm_ready, show_operation_progress


# Helper functions to extract information from the API response
def _extract_cpu_count(vm):
    """Extract CPU count from resources."""
    resources = vm.get("resources", [])
    for resource in resources:
        if resource.get("type") == "VCPU":
            return resource.get("supply", 0)
    return 0


def _extract_memory(vm):
    """Extract memory from resources."""
    resources = vm.get("resources", [])
    for resource in resources:
        if resource.get("type") == "RAM":
            return resource.get("supply", 0)
    return 0


def _extract_storage(vm):
    """Extract storage from resources."""
    resources = vm.get("resources", [])
    for resource in resources:
        if resource.get("type") == "STORAGE":
            return resource.get("supply", 0)
    return 0


def _extract_region(vm):
    """Extract region from datacenter."""
    datacenter = vm.get("datacenter", {})
    country = datacenter.get("countryCode", "")
    return country


def _extract_datacenter(vm):
    """Format datacenter information."""
    datacenter = vm.get("datacenter", {})
    country = datacenter.get("countryCode", "")
    city = datacenter.get("cityCode", "")
    return f"{country}/{city}"


def _extract_ports(vm):
    """Format open ports."""
    ports = vm.get("ports", [])
    return ", ".join([f"{p.get('port')}/{p.get('protocol', 'tcp')}" for p in ports])


def _format_ssh_key(key):
    """
    Ensures SSH key is properly formatted.
    
    Args:
        key: SSH key to format
        
    Returns:
        Properly formatted SSH key
    """
    key = key.strip()
    # If the key doesn't include the ssh- prefix, try to prepend it
    if key and not key.startswith('ssh-') and key.startswith('AAAA'):
        # This appears to be the base64 part of an Ed25519 key without the prefix
        if key.startswith('AAAAC3NzaC1lZDI1NTE5'):
            key = f"ssh-ed25519 {key}"
        # This appears to be the base64 part of an RSA key without the prefix
        elif key.startswith('AAAAB3NzaC1yc2E'):
            key = f"ssh-rsa {key}"
    return key


@click.group(name="vm")
@click.pass_context
def vm_group(ctx):
    """Manage Fluence VMs."""
    pass


@vm_group.command("list")
@click.pass_context
def list_vms(ctx):
    """List all VMs."""
    console.print("[bold]Listing VMs...[/bold]")
    
    try:
        config = get_config()
        client = FluenceAPIClient(api_key=config["FLUENCE_API_KEY"], api_url=config["FLUENCE_API_URL"], 
                                 debug=ctx.obj.debug if hasattr(ctx.obj, 'debug') else False)
        
        vms = client.list_vms()
        
        if not vms:
            print_warning("No VMs found.")
            return
        
        # Get output format from context
        output_format = ctx.obj.output_format if hasattr(ctx.obj, 'output_format') else "table"
        
        if output_format == "json":
            # Pretty print the raw JSON response
            console.print(json.dumps(vms, indent=2))
        elif output_format == "compact":
            # Display a compact table with minimal information
            for i, vm in enumerate(vms, 1):
                console.print(f"{i}. [bold]{vm.get('id', 'Unknown ID')}[/bold] - {vm.get('status', 'Unknown')}")
        else:
            # Default table format with improved data extraction
            enhanced_vms = []
            for vm in vms:
                # Extract the correct fields from the API response
                enhanced_vm = {
                    "id": vm.get("id", ""),
                    "name": vm.get("vmName", ""),
                    "status": vm.get("status", ""),
                    "ip_address": vm.get("publicIp", ""),
                    "cpu": _extract_cpu_count(vm),
                    "memory": _extract_memory(vm),
                    "region": _extract_region(vm)
                }
                enhanced_vms.append(enhanced_vm)
                
            table = format_vm_table(enhanced_vms)
            console.print(table)
        
    except Exception as e:
        print_error(f"Error listing VMs: {str(e)}")
        sys.exit(1)


@vm_group.command("get")
@click.argument("vm_id")
@click.pass_context
def get_vm(ctx, vm_id):
    """Get VM details."""
    console.print(f"[bold]Getting details for VM {vm_id}...[/bold]")
    
    try:
        config = get_config()
        client = FluenceAPIClient(api_key=config["FLUENCE_API_KEY"], api_url=config["FLUENCE_API_URL"],
                                 debug=ctx.obj.debug if hasattr(ctx.obj, 'debug') else False)
        
        vm = client.get_vm(vm_id)
        
        # Get output format from context
        output_format = ctx.obj.output_format if hasattr(ctx.obj, 'output_format') else "table"
        
        if output_format == "json":
            # Pretty print the raw JSON response
            console.print(json.dumps(vm, indent=2))
        else:
            # Extract and enhance VM details for better display
            enhanced_vm = {
                "id": vm.get("id", ""),
                "name": vm.get("vmName", ""),
                "status": vm.get("status", ""),
                "ip_address": vm.get("publicIp", ""),
                "cpu": _extract_cpu_count(vm),
                "memory": _extract_memory(vm),
                "storage": _extract_storage(vm),
                "region": _extract_region(vm),
                "datacenter": _extract_datacenter(vm),
                "os_image": vm.get("osImage", ""),
                "created_at": vm.get("createdAt", ""),
                "next_billing_at": vm.get("nextBillingAt", ""),
                "price_per_epoch": vm.get("pricePerEpoch", ""),
                "total_spent": vm.get("totalSpent", ""),
                "open_ports": _extract_ports(vm)
            }
            
            # Display VM details in a more readable format
            table = format_vm_details(enhanced_vm)
            console.print(table)
        
    except Exception as e:
        print_error(f"Error getting VM details: {str(e)}")
        sys.exit(1)


@vm_group.command("create")
@click.argument("name", required=False)
@click.option("--cpu", type=int, help="Number of CPU cores")
@click.option("--memory", type=int, help="Memory in GB")
@click.option("--wait", is_flag=True, help="Wait for VM to be ready")
@click.option("--config", type=click.Path(exists=True), help="Path to VM configuration file")
@click.option("--region", help="Region code (e.g. US, DE, BE)")
@click.pass_context
def create_vm(ctx, name, cpu, memory, wait, config, region):
    """Create a new VM."""
    try:
        config_dict = get_config()
        client = FluenceAPIClient(api_key=config_dict["FLUENCE_API_KEY"], api_url=config_dict["FLUENCE_API_URL"],
                                 debug=ctx.obj.debug if hasattr(ctx.obj, 'debug') else False)
        
        # Generate VM name if not provided
        if not name:
            prefix = config_dict["VM_NAME_PREFIX"]
            name = f"{prefix}{uuid.uuid4().hex[:8]}"
        
        console.print(f"[bold]Creating VM: {name}[/bold]")
        
        # If config file is provided, load it
        if config:
            try:
                with open(config, 'r') as f:
                    vm_config = json.load(f)
            except Exception as e:
                print_error(f"Error loading config file: {str(e)}")
                sys.exit(1)
        else:
            # Use specified values or defaults from config
            vm_cpu = cpu or config_dict["VM_CPU_COUNT"]
            vm_memory = memory or config_dict["VM_MEMORY_GB"]
            
            # Create VM configuration
            try:
                # Try to get available configurations from the API
                configs = client.get_basic_configurations()
                desired_config = f"cpu-{vm_cpu}-ram-{vm_memory}gb-storage-25gb"
                
                if desired_config in configs:
                    basic_config = desired_config
                    console.print(f"Using configuration: {basic_config}")
                else:
                    # Use the first configuration if exact match not found
                    basic_config = configs[0]
                    print_warning(f"No exact match for {desired_config}. Using {basic_config}")
            except Exception as e:
                print_warning(f"Error getting configurations: {str(e)}. Using default.")
                basic_config = f"cpu-{vm_cpu}-ram-{vm_memory}gb-storage-25gb"
            
            # Format SSH key to ensure it has proper prefix
            ssh_key = _format_ssh_key(config_dict["SSH_PUBLIC_KEY"])
            
            # Construct configuration
            vm_config = {
                "constraints": {
                    "basicConfiguration": basic_config
                },
                "instances": 1,
                "vmConfiguration": {
                    "openPorts": config_dict["OPEN_PORTS"],
                    "sshKeys": [ssh_key],
                    "osImage": "https://cloud-images.ubuntu.com/releases/22.04/release/ubuntu-22.04-server-cloudimg-amd64.img"
                }
            }
            
            # Add datacenter constraint if region is specified
            if region:
                vm_config["constraints"]["datacenter"] = {
                    "countries": [region]
                }
            elif "VM_REGION" in config_dict and config_dict["VM_REGION"]:
                vm_config["constraints"]["datacenter"] = {
                    "countries": [config_dict["VM_REGION"]]
                }
        
        # Create VM with progress indicator
        def create_vm_operation():
            return client.create_vm(name, vm_config)
            
        vm = show_operation_progress(
            create_vm_operation,
            f"Creating VM {name}...",
            "VM creation request successful",
            "VM creation failed"
        )
        
        # Get output format from context
        output_format = ctx.obj.output_format if hasattr(ctx.obj, 'output_format') else "table"
        
        if output_format == "json":
            console.print(json.dumps(vm, indent=2))
        else:
            console.print(f"[bold]VM ID:[/bold] {vm.get('id')}")
        
        # Wait for VM to be ready if requested
        if wait:
            try:
                vm = wait_for_vm_ready(client, vm.get("id"))
                if output_format == "json":
                    console.print(json.dumps(vm, indent=2))
                else:
                    print_success(f"VM is now running at IP: {vm.get('publicIp')}")
            except TimeoutError as e:
                print_warning(str(e))
                print_warning("The VM creation is still in progress. You can check its status later.")
        else:
            print_warning("VM creation is in progress. Use 'flu-cli vm get <id>' to check status.")
        
    except Exception as e:
        print_error(f"Error creating VM: {str(e)}")
        sys.exit(1)


@vm_group.command("estimate")
@click.option("--cpu", type=int, help="Number of CPU cores")
@click.option("--memory", type=int, help="Memory in GB")
@click.option("--storage", type=int, default=25, help="Storage in GB (default: 25)")
@click.option("--region", help="Region code (default: from config)")
@click.option("--config", type=click.Path(exists=True), help="Path to VM configuration file")
@click.pass_context
def estimate_vm(ctx, cpu, memory, storage, region, config):
    """Estimate VM cost without creating it."""
    console.print("[bold]Estimating VM cost...[/bold]")
    
    try:
        config_dict = get_config()
        client = FluenceAPIClient(api_key=config_dict["FLUENCE_API_KEY"], api_url=config_dict["FLUENCE_API_URL"],
                               debug=ctx.obj.debug if hasattr(ctx.obj, 'debug') else False)
        
        # If config file is provided, load it
        if config:
            try:
                with open(config, 'r') as f:
                    vm_config = json.load(f)
            except Exception as e:
                print_error(f"Error loading config file: {str(e)}")
                sys.exit(1)
        else:
            # Use specified values or defaults from config
            vm_cpu = cpu or config_dict["VM_CPU_COUNT"]
            vm_memory = memory or config_dict["VM_MEMORY_GB"]
            vm_storage = storage or config_dict["VM_STORAGE_GB"]
            
            # Create VM configuration
            vm_config = {
                "constraints": {
                    "basicConfiguration": f"cpu-{vm_cpu}-ram-{vm_memory}gb-storage-{vm_storage}gb"
                },
                "instances": 1
            }
            
            # Add datacenter constraint if region is specified
            if region:
                vm_config["constraints"]["datacenter"] = {
                    "countries": [region]
                }
            elif "VM_REGION" in config_dict and config_dict["VM_REGION"]:
                vm_config["constraints"]["datacenter"] = {
                    "countries": [config_dict["VM_REGION"]]
                }
        
        # Get estimate from API
        estimate = client.estimate_vm(vm_config)
        
        # Get output format from context
        output_format = ctx.obj.output_format if hasattr(ctx.obj, 'output_format') else "table"
        
        if output_format == "json":
            console.print(json.dumps(estimate, indent=2))
        else:
            if "totalPricePerEpochUsd" in estimate:
                price = estimate["totalPricePerEpochUsd"]
                console.print(f"[bold]Daily price:[/bold] ${price}")
                
                # Calculate hourly price if not provided
                if "hourlyPriceUsd" in estimate:
                    hourly = estimate["hourlyPriceUsd"]
                else:
                    hourly = float(price) / 24
                console.print(f"[bold]Hourly price:[/bold] ${hourly:.6f}")
                
                # Calculate monthly price (30 days)
                monthly = float(price) * 30
                console.print(f"[bold]Monthly price (30 days):[/bold] ${monthly:.2f}")
            else:
                print_warning("No pricing information available")
        
    except Exception as e:
        print_error(f"Error estimating VM cost: {str(e)}")
        sys.exit(1)


@vm_group.command("delete")
@click.argument("vm_id")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def delete_vm(ctx, vm_id, force):
    """Delete a VM."""
    console.print(f"[bold]Deleting VM {vm_id}...[/bold]")
    
    try:
        config = get_config()
        client = FluenceAPIClient(api_key=config["FLUENCE_API_KEY"], api_url=config["FLUENCE_API_URL"],
                                 debug=ctx.obj.debug if hasattr(ctx.obj, 'debug') else False)
        
        # Get VM details first to confirm
        try:
            vm = client.get_vm(vm_id)
            console.print(f"Deleting VM: [bold]{vm.get('vmName', '')}[/bold] (IP: {vm.get('publicIp', '')})")
        except:
            print_warning(f"Could not get VM details for {vm_id}")
        
        # Confirm deletion
        if not force and not click.confirm("Are you sure you want to delete this VM?"):
            print_warning("Deletion cancelled.")
            return
        
        # Delete VM with progress indicator
        def delete_vm_operation():
            return client.delete_vm(vm_id)
            
        result = show_operation_progress(
            delete_vm_operation,
            f"Deleting VM {vm_id}...",
            "VM deletion request successful",
            "VM deletion failed"
        )
        
        # Get output format from context
        output_format = ctx.obj.output_format if hasattr(ctx.obj, 'output_format') else "table"
        
        if output_format == "json":
            console.print(json.dumps(result, indent=2))
        else:
            print_warning("The VM deletion is in progress and may take a few minutes to complete.")
        
    except Exception as e:
        print_error(f"Error deleting VM: {str(e)}")
        sys.exit(1)


@vm_group.command("scale")
@click.argument("vm_id")
@click.option("--cpu", required=True, type=int, help="New CPU count")
@click.option("--memory", required=True, type=int, help="New memory size in GB")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def scale_vm(ctx, vm_id, cpu, memory, force):
    """Scale VM resources."""
    console.print(f"[bold]Scaling VM {vm_id}...[/bold]")
    
    try:
        config = get_config()
        client = FluenceAPIClient(api_key=config["FLUENCE_API_KEY"], api_url=config["FLUENCE_API_URL"],
                                 debug=ctx.obj.debug if hasattr(ctx.obj, 'debug') else False)
        
        # Get current VM details
        vm = client.get_vm(vm_id)
        current_cpu = _extract_cpu_count(vm)
        current_memory = _extract_memory(vm)
        
        console.print(f"Current resources: [yellow]{current_cpu} CPU, {current_memory} GB[/yellow]")
        console.print(f"New resources: [green]{cpu} CPU, {memory} GB[/green]")
        
        # Confirm scaling
        if not force and not click.confirm("Are you sure you want to scale this VM?"):
            print_warning("Scaling cancelled.")
            return
        
        # Scale VM with progress indicator
        def scale_vm_operation():
            return client.scale_vm(
                vm_id, cpu, memory, 
                cpu_manufacturer=config["CPU_MANUFACTURER"],
                cpu_architecture=config["CPU_ARCHITECTURE"]
            )
            
        result = show_operation_progress(
            scale_vm_operation,
            f"Scaling VM {vm_id}...",
            "VM scaling request successful",
            "VM scaling failed"
        )
        
        # Get output format from context
        output_format = ctx.obj.output_format if hasattr(ctx.obj, 'output_format') else "table"
        
        if output_format == "json":
            console.print(json.dumps(result, indent=2))
        else:
            cpu_count = _extract_cpu_count(result)
            memory_size = _extract_memory(result)
            console.print(f"[bold]New CPU:[/bold] {cpu_count}")
            console.print(f"[bold]New Memory:[/bold] {memory_size} GB")
        
    except Exception as e:
        print_error(f"Error scaling VM: {str(e)}")
        sys.exit(1)