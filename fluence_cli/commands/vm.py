"""
VM management commands for the Fluence CLI with API v3 compatibility.
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
    if key and not key.startswith('ssh-') and not key.startswith('ecdsa-') and key.startswith('AAAA'):
        # This appears to be the base64 part of an Ed25519 key without the prefix
        if key.startswith('AAAAC3NzaC1lZDI1NTE5'):
            key = f"ssh-ed25519 {key}"
        # This appears to be the base64 part of an RSA key without the prefix
        elif key.startswith('AAAAB3NzaC1yc2E'):
            key = f"ssh-rsa {key}"
        # ECDSA keys
        elif key.startswith('AAAAE2VjZHNhLXNoYTItbmlzdHA'):
            if 'bmlzdHAyNTY' in key:
                key = f"ecdsa-sha2-nistp256 {key}"
            elif 'bmlzdHAzODQ' in key:
                key = f"ecdsa-sha2-nistp384 {key}"
            elif 'bmlzdHA1MjE' in key:
                key = f"ecdsa-sha2-nistp521 {key}"
    return key


@click.group(name="vm")
@click.pass_context
def vm_group(ctx):
    """Manage Fluence VMs."""
    pass


@vm_group.command("list")
@click.option("--all", "-a", is_flag=True, help="Show all VMs including terminated")
@click.option("--status", help="Filter by status (Active, Terminated, etc.)")
@click.option("--full-id", is_flag=True, help="Show full VM IDs without truncation")
@click.pass_context
def list_vms(ctx, all, status, full_id):
    """List VMs (by default only active ones)."""
    # Get output format from context
    output_format = ctx.obj.output_format if hasattr(ctx.obj, 'output_format') else "table"
    
    # Only print status messages if NOT in JSON format
    if output_format != "json":
        console.print("[bold]Listing VMs...[/bold]")
    
    try:
        config = get_config()
        client = FluenceAPIClient(api_key=config["FLUENCE_API_KEY"], api_url=config["FLUENCE_API_URL"], 
                                 debug=ctx.obj.debug if hasattr(ctx.obj, 'debug') else False)
        
        vms = client.list_vms()
        
        # Filter VMs based on options
        if not all and not status:
            # Default: only show Active VMs
            vms = [vm for vm in vms if vm.get("status") == "Active"]
        elif status:
            # Filter by specific status
            vms = [vm for vm in vms if vm.get("status", "").lower() == status.lower()]
        
        if not vms:
            if all:
                print_warning("No VMs found.")
            else:
                print_warning("No active VMs found. Use --all to see all VMs.")
            return
        
        # Get output format from context
        output_format = ctx.obj.output_format if hasattr(ctx.obj, 'output_format') else "table"
        
        if output_format == "json":
            # For JSON format, output ONLY the JSON, no other text
            print(json.dumps(vms, indent=2))
        elif output_format == "compact":
            # Display a compact list with full IDs
            for i, vm in enumerate(vms, 1):
                vm_id = vm.get('id', 'Unknown ID')
                if not full_id and len(vm_id) > 16:
                    # Show first 6 and last 6 characters
                    vm_id = f"{vm_id[:6]}...{vm_id[-6:]}"
                status_color = "green" if vm.get('status') == "Active" else "yellow"
                console.print(f"{i}. [bold]{vm_id}[/bold] - [{status_color}]{vm.get('status', 'Unknown')}[/{status_color}] - {vm.get('vmName', 'Unnamed')}")
        else:
            # Default table format with improved data extraction
            enhanced_vms = []
            for vm in vms:
                vm_id = vm.get("id", "")
                if not full_id and len(vm_id) > 16:
                    # Truncate ID for table display
                    display_id = f"{vm_id[:6]}...{vm_id[-6:]}"
                else:
                    display_id = vm_id
                
                # Extract the correct fields from the API response
                enhanced_vm = {
                    "id": display_id,
                    "name": vm.get("vmName", ""),
                    "status": vm.get("status", ""),
                    "ip_address": vm.get("publicIp", ""),
                    "cpu": _extract_cpu_count(vm),
                    "memory": _extract_memory(vm),
                    "region": _extract_region(vm),
                    "full_id": vm_id  # Store full ID for reference
                }
                enhanced_vms.append(enhanced_vm)
                
            table = format_vm_table(enhanced_vms)
            console.print(table)
            
            if not full_id and any(len(vm.get("id", "")) > 16 for vm in vms):
                console.print("\n[dim]Use --full-id to see complete VM IDs[/dim]")
        
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
@click.option("--image", help="OS image slug or URL (use 'vm images' to list available)")
@click.pass_context
def create_vm(ctx, name, cpu, memory, wait, config, region, image):
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
            
            # Get available configurations from API
            try:
                configs = client.get_basic_configurations()
                desired_config = f"cpu-{vm_cpu}-ram-{vm_memory}gb-storage-25gb"
                
                if desired_config in configs:
                    basic_config = desired_config
                    console.print(f"Using configuration: {basic_config}")
                else:
                    # Find closest match
                    basic_config = configs[0] if configs else desired_config
                    print_warning(f"No exact match for {desired_config}. Using {basic_config}")
            except Exception as e:
                print_warning(f"Using default configuration")
                basic_config = f"cpu-{vm_cpu}-ram-{vm_memory}gb-storage-25gb"
            
            # Handle OS image selection
            os_image = "https://cloud-images.ubuntu.com/releases/22.04/release/ubuntu-22.04-server-cloudimg-amd64.img"
            
            if image:
                # Check if it's a URL or a slug
                if image.startswith("http://") or image.startswith("https://"):
                    os_image = image
                else:
                    # Try to find image by slug
                    try:
                        images = client.get_default_images()
                        for img in images:
                            if img.get("slug") == image:
                                os_image = img.get("downloadUrl")
                                console.print(f"Using image: {img.get('name')} ({img.get('distribution')})")
                                break
                        else:
                            print_warning(f"Image slug '{image}' not found. Using default Ubuntu 22.04")
                    except:
                        print_warning("Could not fetch available images. Using default Ubuntu 22.04")
            
            # Format SSH key to ensure it has proper prefix
            ssh_key = _format_ssh_key(config_dict["SSH_PUBLIC_KEY"])
            
            # Construct configuration
            vm_config = {
                "constraints": {
                    "basicConfiguration": basic_config
                },
                "instances": 1,
                "vmConfiguration": {
                    "name": name,
                    "openPorts": config_dict["OPEN_PORTS"],
                    "sshKeys": [ssh_key],
                    "osImage": os_image
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
            
        vms = show_operation_progress(
            create_vm_operation,
            f"Creating VM {name}...",
            "VM creation request successful",
            "VM creation failed"
        )
        
        # Handle array response - get first VM
        if isinstance(vms, list) and len(vms) > 0:
            vm = vms[0]
        else:
            print_error("Unexpected response format from VM creation")
            sys.exit(1)
        
        # Get output format from context
        output_format = ctx.obj.output_format if hasattr(ctx.obj, 'output_format') else "table"
        
        if output_format == "json":
            console.print(json.dumps(vm, indent=2))
        else:
            vm_id = vm.get('vmId', vm.get('id', ''))
            console.print(f"[bold]VM ID:[/bold] {vm_id}")
            console.print(f"[bold]VM Name:[/bold] {vm.get('vmName', name)}")
        
        # Wait for VM to be ready if requested
        if wait and vm_id:
            try:
                # Use Active status (API v3 uses Active, not running)
                vm = wait_for_vm_ready(client, vm_id, target_status="Active")
                if output_format == "json":
                    console.print(json.dumps(vm, indent=2))
                else:
                    print_success(f"VM is now active at IP: {vm.get('publicIp')}")
            except TimeoutError as e:
                print_warning(str(e))
                print_warning("The VM creation is still in progress. You can check its status later.")
        else:
            print_warning("VM creation is in progress. Use 'fvm-cli vm get <id>' to check status.")
        
    except Exception as e:
        print_error(f"Error creating VM: {str(e)}")
        sys.exit(1)


@vm_group.command("images")
@click.pass_context
def list_images(ctx):
    """List available OS images."""
    console.print("[bold]Listing available OS images...[/bold]")
    
    try:
        config = get_config()
        client = FluenceAPIClient(api_key=config["FLUENCE_API_KEY"], api_url=config["FLUENCE_API_URL"],
                                 debug=ctx.obj.debug if hasattr(ctx.obj, 'debug') else False)
        
        images = client.get_default_images()
        
        if not images:
            print_warning("No images found.")
            return
        
        # Get output format from context
        output_format = ctx.obj.output_format if hasattr(ctx.obj, 'output_format') else "table"
        
        if output_format == "json":
            console.print(json.dumps(images, indent=2))
        elif output_format == "compact":
            for img in images:
                console.print(f"{img.get('slug')} - {img.get('name')}")
        else:
            # Create a table for images
            from rich.table import Table
            table = Table(show_header=True)
            table.add_column("Slug", style="cyan")
            table.add_column("Name", style="green")
            table.add_column("Distribution", style="yellow")
            table.add_column("Username", style="blue")
            table.add_column("Created", style="magenta")
            
            for img in images:
                table.add_row(
                    img.get("slug", ""),
                    img.get("name", ""),
                    img.get("distribution", ""),
                    img.get("username", ""),
                    img.get("createdAt", "")[:10]  # Just date part
                )
            
            console.print(table)
            console.print("\n[dim]Use --image <slug> when creating a VM to use a specific image[/dim]")
        
    except Exception as e:
        print_error(f"Error listing images: {str(e)}")
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
            if "totalPricePerEpoch" in estimate:
                price = estimate["totalPricePerEpoch"]
                console.print(f"[bold]Daily price:[/bold] ${price}")
                
                # Calculate hourly price if not provided
                if "hourlyPriceUsd" in estimate:
                    hourly = estimate["hourlyPriceUsd"]
                else:
                    try:
                        hourly = float(price) / 24
                        hourly = f"{hourly:.6f}"
                    except (ValueError, TypeError):
                        hourly = "Unable to calculate"
                console.print(f"[bold]Hourly price:[/bold] ${hourly}")
                
                # Calculate monthly price (30 days)
                try:
                    monthly = float(price) * 30
                    console.print(f"[bold]Monthly price (30 days):[/bold] ${monthly:.2f}")
                except (ValueError, TypeError):
                    console.print(f"[bold]Monthly price (30 days):[/bold] Unable to calculate")
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


@vm_group.command("update")
@click.argument("vm_id")
@click.option("--name", help="New VM name")
@click.option("--add-port", multiple=True, help="Add port (format: port/protocol, e.g., 8080/tcp)")
@click.option("--remove-port", multiple=True, help="Remove port (format: port/protocol)")
@click.option("--force", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def update_vm(ctx, vm_id, name, add_port, remove_port, force):
    """Update VM configuration (name and/or open ports)."""
    console.print(f"[bold]Updating VM {vm_id}...[/bold]")
    
    try:
        config = get_config()
        client = FluenceAPIClient(api_key=config["FLUENCE_API_KEY"], api_url=config["FLUENCE_API_URL"],
                                 debug=ctx.obj.debug if hasattr(ctx.obj, 'debug') else False)
        
        # Get current VM details
        vm = client.get_vm(vm_id)
        current_name = vm.get("vmName", "")
        current_ports = vm.get("ports", [])
        
        # Build updates
        updates = {}
        
        # Handle name update
        if name and name != current_name:
            updates["vmName"] = name
            console.print(f"Updating name: [yellow]{current_name}[/yellow] → [green]{name}[/green]")
        
        # Handle port updates
        if add_port or remove_port:
            # Convert current ports to a dict for easier manipulation
            port_dict = {f"{p['port']}/{p.get('protocol', 'tcp')}": p for p in current_ports}
            
            # Remove ports
            for port_spec in remove_port:
                if port_spec in port_dict:
                    del port_dict[port_spec]
                    console.print(f"Removing port: [red]{port_spec}[/red]")
                else:
                    print_warning(f"Port {port_spec} not found in current configuration")
            
            # Add ports
            for port_spec in add_port:
                if '/' in port_spec:
                    port_num, protocol = port_spec.split('/', 1)
                else:
                    port_num, protocol = port_spec, 'tcp'
                
                try:
                    port_num = int(port_num)
                    if port_num < 1 or port_num > 65535:
                        print_warning(f"Invalid port number: {port_num}")
                        continue
                        
                    key = f"{port_num}/{protocol}"
                    if key not in port_dict:
                        port_dict[key] = {"port": port_num, "protocol": protocol}
                        console.print(f"Adding port: [green]{key}[/green]")
                    else:
                        print_warning(f"Port {key} already exists")
                except ValueError:
                    print_warning(f"Invalid port specification: {port_spec}")
            
            # Convert back to list
            updates["openPorts"] = list(port_dict.values())
        
        # Check if there are any updates
        if not updates:
            print_warning("No updates specified.")
            return
        
        # Confirm update
        if not force and not click.confirm("Are you sure you want to update this VM?"):
            print_warning("Update cancelled.")
            return
        
        # Update VM with progress indicator
        def update_vm_operation():
            return client.update_vm(vm_id, updates)
            
        result = show_operation_progress(
            update_vm_operation,
            f"Updating VM {vm_id}...",
            "VM update request successful",
            "VM update failed"
        )
        
        # Get output format from context
        output_format = ctx.obj.output_format if hasattr(ctx.obj, 'output_format') else "table"
        
        if output_format == "json":
            console.print(json.dumps(result, indent=2))
        else:
            print_success("VM updated successfully")
        
    except Exception as e:
        print_error(f"Error updating VM: {str(e)}")
        sys.exit(1)