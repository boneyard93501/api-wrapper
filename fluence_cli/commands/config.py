"""
Configuration commands for the Fluence CLI using global format options.
"""

import sys
import json
import click

from fluence_cli.config import create_default_config, create_env_template, get_config
from fluence_cli.utils.console import console, print_error, print_warning, print_success


@click.group(name="config")
def config_group():
    """Manage Fluence CLI configuration."""
    pass


@config_group.command("init")
@click.pass_context
def init_config(ctx):
    """Initialize configuration files."""
    try:
        create_default_config()
        print_success("Configuration initialized successfully.")
    except Exception as e:
        print_error(f"Error initializing configuration: {str(e)}")
        sys.exit(1)


@config_group.command("env")
@click.pass_context
def create_env(ctx):
    """Create .env file template."""
    try:
        create_env_template()
    except Exception as e:
        print_error(f"Error creating .env template: {str(e)}")
        sys.exit(1)


@config_group.command("show")
@click.pass_context
def show_config(ctx):
    """Show current configuration."""
    console.print("[bold]Current Configuration:[/bold]")
    
    try:
        config = get_config()
        
        # Get output format from context
        output_format = ctx.obj.output_format if hasattr(ctx, 'obj') and hasattr(ctx.obj, 'output_format') else "table"
        
        if output_format == "json":
            # Remove sensitive information
            safe_config = {k: v for k, v in config.items() if k not in ["FLUENCE_API_KEY", "SSH_PUBLIC_KEY"]}
            console.print(json.dumps(safe_config, indent=2))
        else:
            # Display configuration in a readable format
            console.print("\n[bold]API Configuration:[/bold]")
            console.print(f"API URL: [cyan]{config.get('FLUENCE_API_URL')}[/cyan]")
            
            # Don't display the actual API key, just whether it's set
            if config.get("FLUENCE_API_KEY"):
                console.print("API Key: [green]Set[/green]")
            else:
                console.print("API Key: [red]Not Set[/red]")
                
            # Don't display the actual SSH key, just whether it's set
            if config.get("SSH_PUBLIC_KEY"):
                console.print("SSH Key: [green]Set[/green]")
            else:
                console.print("SSH Key: [red]Not Set[/red]")
            
            console.print("\n[bold]VM Configuration:[/bold]")
            console.print(f"CPU Count: [cyan]{config.get('VM_CPU_COUNT')}[/cyan]")
            console.print(f"Memory (GB): [cyan]{config.get('VM_MEMORY_GB')}[/cyan]")
            console.print(f"Storage (GB): [cyan]{config.get('VM_STORAGE_GB')}[/cyan]")
            console.print(f"Region: [cyan]{config.get('VM_REGION')}[/cyan]")
            console.print(f"VM Name Prefix: [cyan]{config.get('VM_NAME_PREFIX')}[/cyan]")
            
            console.print("\n[bold]Hardware Configuration:[/bold]")
            console.print(f"CPU Manufacturer: [cyan]{config.get('CPU_MANUFACTURER')}[/cyan]")
            console.print(f"CPU Architecture: [cyan]{config.get('CPU_ARCHITECTURE')}[/cyan]")
            
            console.print("\n[bold]Network Configuration:[/bold]")
            console.print("[cyan]Open Ports:[/cyan]")
            for port in config.get('OPEN_PORTS', []):
                console.print(f"  - {port.get('port')}/{port.get('protocol')}")
        
    except Exception as e:
        print_error(f"Error showing configuration: {str(e)}")
        sys.exit(1)