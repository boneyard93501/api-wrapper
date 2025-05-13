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
        client = FluenceAPIClient(api_key=config["FLUENCE_API_KEY"], api_url=config["FLUENCE_API_URL"])
        
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
        client = FluenceAPIClient(api_key=config["FLUENCE_API_KEY"], api_url=config["FLUENCE_API_URL"])
        
        # Use specified region or default from config
        region_code = region or config["VM_REGION"]
        
        pricing = client.get_vm_pricing(cpu, memory, region=region_code)
        
        # Get output format from context
        output_format = ctx.obj.output_format if hasattr(ctx, 'obj') and hasattr(ctx.obj, 'output_format') else "table"
        
        if output_format == "json":
            console.print(json.dumps(pricing, indent=2))
        else:
            console.print("[bold]Pricing Estimate:[/bold]")
            
            if "hourlyPriceUsd" in pricing:
                hourly_price = pricing.get("hourlyPriceUsd")
                console.print(f"Hourly Price: [green]${hourly_price}[/green]")
            
            if "dailyPriceUsd" in pricing:
                daily_price = pricing.get("dailyPriceUsd")
                console.print(f"Daily Price: [yellow]${daily_price}[/yellow]")
            
            if "monthlyPriceUsd" in pricing:
                monthly_price = pricing.get("monthlyPriceUsd")
                console.print(f"Monthly Price: [magenta]${monthly_price}[/magenta]")
        
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
        client = FluenceAPIClient(api_key=config["FLUENCE_API_KEY"], api_url=config["FLUENCE_API_URL"])
        
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
                console.print(f"  - [cyan]{memory.get('type')} {memory.get('generation')}[/cyan]")
            
            # Display storage options
            console.print("\n[bold]Storage Options:[/bold]")
            for storage in hardware.get("storage", []):
                console.print(f"  - [cyan]{storage.get('type')}[/cyan]")
        
    except Exception as e:
        print_error(f"Error listing hardware options: {str(e)}")
        sys.exit(1)