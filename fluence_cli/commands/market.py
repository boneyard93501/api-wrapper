"""
Marketplace commands for the Fluence CLI using global format options.
"""

import sys
import json
import click

from fluence_cli.api import FluenceAPIClient
from fluence_cli.config import get_config
from fluence_cli.utils.console import console, print_error, print_warning, print_success


@click.group(name="market")
def market_group():
    """Query Fluence marketplace information."""
    pass


@market_group.command("countries")
@click.pass_context
def list_countries(ctx):
    """List available countries."""
    console.print("[bold]Listing available countries...[/bold]")
    
    try:
        config = get_config()
        client = FluenceAPIClient(api_key=config["FLUENCE_API_KEY"], api_url=config["FLUENCE_API_URL"],
                                 debug=ctx.obj.debug if hasattr(ctx.obj, 'debug') else False)
        
        countries = client.get_available_countries()
        
        if not countries:
            print_warning("No countries found.")
            return
        
        # Get output format from context
        output_format = ctx.obj.output_format if hasattr(ctx, 'obj') and hasattr(ctx.obj, 'output_format') else "table"
        
        if output_format == "json":
            console.print(json.dumps(countries, indent=2))
        elif output_format == "compact":
            console.print("Available country codes: " + ", ".join(countries))
        else:
            console.print("Available country codes:")
            console.print("-------------------------------------")
            
            for i, country in enumerate(countries, 1):
                console.print(f"{i}. [cyan]{country}[/cyan]")
            
            console.print("-------------------------------------")
        
    except Exception as e:
        print_error(f"Error listing countries: {str(e)}")
        sys.exit(1)


@market_group.command("pricing")
@click.option("--cpu", required=True, type=int, help="Number of CPU cores")
@click.option("--memory", required=True, type=int, help="Memory in GB")
@click.option("--region", help="Region code (default: from config)")
@click.pass_context
def get_pricing(ctx, cpu, memory, region):
    """Get VM pricing estimate."""
    console.print(f"[bold]Getting pricing for {cpu} CPU, {memory} GB...[/bold]")
    
    try:
        config = get_config()
        client = FluenceAPIClient(api_key=config["FLUENCE_API_KEY"], api_url=config["FLUENCE_API_URL"],
                                 debug=ctx.obj.debug if hasattr(ctx.obj, 'debug') else False)
        
        # Use specified region or default from config
        region_code = region or config.get("VM_REGION")
        
        pricing = client.get_vm_pricing(cpu, memory, region=region_code)
        
        # Get output format from context
        output_format = ctx.obj.output_format if hasattr(ctx, 'obj') and hasattr(ctx.obj, 'output_format') else "table"
        
        if output_format == "json":
            console.print(json.dumps(pricing, indent=2))
        else:
            console.print("[bold]Pricing Estimate:[/bold]")
            
            if "totalPricePerEpoch" in pricing:
                daily_price = pricing.get("totalPricePerEpoch")
                console.print(f"Daily Price: [yellow]${daily_price}[/yellow]")
                
            if "dailyPriceUsd" in pricing:
                daily_price = pricing.get("dailyPriceUsd")
                console.print(f"Daily Price: [yellow]${daily_price}[/yellow]")
            
            if "hourlyPriceUsd" in pricing:
                hourly_price = pricing.get("hourlyPriceUsd")
                console.print(f"Hourly Price: [green]${hourly_price}[/green]")
            
            if "monthlyPriceUsd" in pricing:
                monthly_price = pricing.get("monthlyPriceUsd")
                console.print(f"Monthly Price: [magenta]${monthly_price}[/magenta]")
            elif "totalPricePerEpoch" in pricing or "dailyPriceUsd" in pricing:
                # Calculate monthly price
                daily = float(pricing.get("totalPricePerEpoch", pricing.get("dailyPriceUsd", "0")))
                monthly = daily * 30
                console.print(f"Monthly Price (30 days): [magenta]${monthly:.2f}[/magenta]")
        
    except Exception as e:
        print_error(f"Error getting pricing: {str(e)}")
        sys.exit(1)


@market_group.command("hardware")
@click.pass_context
def list_hardware(ctx):
    """List available hardware options."""
    console.print("[bold]Listing available hardware options...[/bold]")
    
    try:
        config = get_config()
        client = FluenceAPIClient(api_key=config["FLUENCE_API_KEY"], api_url=config["FLUENCE_API_URL"],
                                 debug=ctx.obj.debug if hasattr(ctx.obj, 'debug') else False)
        
        hardware = client.get_hardware_options()
        
        # Get output format from context
        output_format = ctx.obj.output_format if hasattr(ctx, 'obj') and hasattr(ctx.obj, 'output_format') else "table"
        
        if output_format == "json":
            console.print(json.dumps(hardware, indent=2))
        else:
            # Display CPU options
            console.print("[bold]CPU Options:[/bold]")
            for cpu in hardware.get("cpu", []):
                console.print(f"  - [cyan]{cpu.get('manufacturer')} {cpu.get('architecture')}[/cyan]")
            
            # Display memory options
            console.print("\n[bold]Memory Options:[/bold]")
            for memory in hardware.get("memory", []):
                console.print(f"  - [cyan]{memory.get('type')} Gen{memory.get('generation')}[/cyan]")
            
            # Display storage options
            console.print("\n[bold]Storage Options:[/bold]")
            for storage in hardware.get("storage", []):
                console.print(f"  - [cyan]{storage.get('type')}[/cyan]")
        
    except Exception as e:
        print_error(f"Error listing hardware options: {str(e)}")
        sys.exit(1)


@market_group.command("configurations")
@click.pass_context
def list_configurations(ctx):
    """List available basic configurations."""
    console.print("[bold]Listing available basic configurations...[/bold]")
    
    try:
        config = get_config()
        client = FluenceAPIClient(api_key=config["FLUENCE_API_KEY"], api_url=config["FLUENCE_API_URL"],
                                 debug=ctx.obj.debug if hasattr(ctx.obj, 'debug') else False)
        
        configurations = client.get_basic_configurations()
        
        if not configurations:
            print_warning("No configurations found.")
            return
        
        # Get output format from context
        output_format = ctx.obj.output_format if hasattr(ctx, 'obj') and hasattr(ctx.obj, 'output_format') else "table"
        
        if output_format == "json":
            console.print(json.dumps(configurations, indent=2))
        elif output_format == "compact":
            for config_str in configurations:
                console.print(config_str)
        else:
            # Create a formatted table
            from rich.table import Table
            table = Table(show_header=True)
            table.add_column("Configuration", style="cyan")
            table.add_column("CPU", style="green", justify="center")
            table.add_column("RAM (GB)", style="yellow", justify="center")
            table.add_column("Storage (GB)", style="blue", justify="center")
            
            for config_str in configurations:
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
            
            console.print(table)
        
    except Exception as e:
        print_error(f"Error listing configurations: {str(e)}")
        sys.exit(1)


@market_group.command("offers")
@click.option("--cpu", type=int, help="Filter by CPU cores")
@click.option("--memory", type=int, help="Filter by memory (GB)")
@click.option("--storage", type=int, help="Filter by storage (GB)")
@click.option("--region", help="Filter by region (country code)")
@click.option("--max-price", type=float, help="Maximum price per day in USD")
@click.option("--cpu-manufacturer", help="Filter by CPU manufacturer (e.g., AMD, Intel)")
@click.option("--storage-type", help="Filter by storage type (HDD, SSD, NVMe)")
@click.pass_context
def search_offers(ctx, cpu, memory, storage, region, max_price, cpu_manufacturer, storage_type):
    """Search marketplace for available compute offers."""
    console.print("[bold]Searching marketplace offers...[/bold]")
    
    try:
        config = get_config()
        client = FluenceAPIClient(api_key=config["FLUENCE_API_KEY"], api_url=config["FLUENCE_API_URL"],
                                 debug=ctx.obj.debug if hasattr(ctx.obj, 'debug') else False)
        
        # Build constraints
        constraints = {}
        
        # Basic configuration constraint
        if cpu and memory:
            storage_size = storage or 25
            constraints["basicConfiguration"] = f"cpu-{cpu}-ram-{memory}gb-storage-{storage_size}gb"
        
        # Datacenter constraint
        if region:
            constraints["datacenter"] = {
                "countries": [region]
            }
        
        # Max price constraint
        if max_price:
            constraints["maxTotalPricePerEpochUsd"] = str(max_price)
        
        # Hardware constraints
        hardware_constraints = {}
        if cpu_manufacturer:
            hardware_constraints["cpu"] = [{"manufacturer": cpu_manufacturer}]
        if storage_type:
            hardware_constraints["storage"] = [{"type": storage_type}]
        
        if hardware_constraints:
            constraints["hardware"] = hardware_constraints
        
        # Search offers
        offers = client.get_marketplace_offers(constraints)
        
        if not offers:
            print_warning("No offers found matching your criteria.")
            return
        
        # Get output format from context
        output_format = ctx.obj.output_format if hasattr(ctx, 'obj') and hasattr(ctx.obj, 'output_format') else "table"
        
        if output_format == "json":
            console.print(json.dumps(offers, indent=2))
        else:
            console.print(f"\n[bold]Found {len(offers)} offer(s):[/bold]\n")
            
            # Create a table for offers
            from rich.table import Table
            table = Table(show_header=True)
            table.add_column("Configuration", style="cyan")
            table.add_column("Price/Day", style="green", justify="right")
            table.add_column("Location", style="yellow")
            table.add_column("Available", style="blue", justify="center")
            table.add_column("Datacenter", style="magenta")
            
            for offer in offers:
                config_info = offer.get("configuration", {})
                config_slug = config_info.get("slug", "N/A")
                price = config_info.get("price", "N/A")
                
                datacenter = offer.get("datacenter", {})
                country = datacenter.get("countryCode", "")
                city = datacenter.get("cityCode", "")
                location = f"{country}/{city}" if city else country
                
                # Get certifications
                certs = datacenter.get("certifications", [])
                cert_str = ", ".join(certs) if certs else "N/A"
                
                # Count available instances
                servers = offer.get("servers", [])
                total_available = sum(s.get("availableBasicInstances", 0) for s in servers)
                
                table.add_row(
                    config_slug,
                    f"${price}",
                    location,
                    str(total_available),
                    cert_str
                )
            
            console.print(table)
            
            # Show summary of resources if in verbose mode
            if ctx.obj.debug:
                console.print("\n[bold]Resource Details:[/bold]")
                for i, offer in enumerate(offers[:3]):  # Show first 3 offers
                    console.print(f"\n[dim]Offer {i+1}:[/dim]")
                    resources = offer.get("resources", [])
                    for resource in resources:
                        res_type = resource.get("type")
                        metadata = resource.get("metadata", {})
                        price = resource.get("price")
                        
                        if res_type == "VCPU":
                            cpu_info = f"{metadata.get('manufacturer', '')} {metadata.get('architecture', '')}"
                            console.print(f"  CPU: {cpu_info} - ${price}")
                        elif res_type == "RAM":
                            ram_info = f"{metadata.get('type', '')} Gen{metadata.get('generation', '')}"
                            console.print(f"  RAM: {ram_info} - ${price}")
                        elif res_type == "STORAGE":
                            storage_info = metadata.get('type', '')
                            console.print(f"  Storage: {storage_info} - ${price}")
        
    except Exception as e:
        print_error(f"Error searching offers: {str(e)}")
        sys.exit(1)