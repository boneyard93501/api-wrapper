"""
Main CLI entry point for the Fluence VM CLI (fvm-cli).
"""

import os
import sys
import json
import click

from fluence_cli.commands.vm import vm_group
from fluence_cli.commands.config import config_group
from fluence_cli.commands.market import market_group
from fluence_cli.config import load_environment
from fluence_cli.utils.console import console, print_error, print_warning, print_success


# Define a custom context class to hold global options
class FluenceCliContext:
    def __init__(self):
        self.output_format = "table"
        self.debug = False


@click.group()
@click.version_option(version="0.1.0", prog_name="fvm-cli")
@click.option("--format", "-f", type=click.Choice(["table", "json", "compact"]), 
              default="table", help="Output format (table, json, compact)")
@click.option("--debug", is_flag=True, help="Show API requests and responses")
@click.pass_context
def cli(ctx, format, debug):
    """FVM CLI - Fluence VM Command Line Interface for managing VMs.
    
    Global Options:
      --format, -f [table|json|compact]  Output format (default: table)
      --debug                            Show API requests and responses
    """
    # Create a context object for the command hierarchy
    ctx.obj = FluenceCliContext()
    ctx.obj.output_format = format
    ctx.obj.debug = debug
    
    # Load environment variables
    load_environment()
    
    # Check for required environment variables
    if not os.environ.get("FLUENCE_API_KEY"):
        print_warning("Warning: FLUENCE_API_KEY environment variable not set.")
        print_warning("You can set it using the .env file or export it in your shell.")


# Add command groups
cli.add_command(vm_group)
cli.add_command(config_group)
cli.add_command(market_group)


def main():
    """Main entry point for the CLI."""
    try:
        cli(obj={})  # Initialize empty context object
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()