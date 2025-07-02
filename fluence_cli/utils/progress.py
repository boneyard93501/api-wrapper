"""
Progress indicators for the Fluence CLI.
"""

import time
from typing import Dict, Any, Optional, Callable
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn

from fluence_cli.api import FluenceAPIClient


def wait_for_vm_ready(client: FluenceAPIClient, vm_id: str, timeout: int = 300, target_status: str = "Active") -> Dict[str, Any]:
    """
    Wait for a VM to be in 'Active' state with progress indicator.
    
    Args:
        client: FluenceAPIClient instance
        vm_id: ID of the VM to wait for
        timeout: Maximum time to wait in seconds
        target_status: Status to wait for (default: Active)
        
    Returns:
        VM details once it's ready
        
    Raises:
        TimeoutError: If VM doesn't reach 'Active' state in time
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn()
    ) as progress:
        task = progress.add_task(f"Waiting for VM {vm_id} to be ready...", total=timeout)
        
        def update_progress(vm_data: Dict[str, Any], elapsed_time: float) -> None:
            """Update progress bar with current VM status."""
            status = vm_data.get("status", "unknown")
            progress.update(
                task, 
                description=f"Waiting for VM {vm_id} to be ready... (Status: {status})",
                completed=min(elapsed_time, timeout)
            )
        
        # Use the built-in wait_for_vm_status method with our callback
        # API v3 uses "Active" status, not "running"
        return client.wait_for_vm_status(
            vm_id, 
            target_status,  # Use the provided target status
            timeout=timeout,
            check_interval=5,
            callback=update_progress
        )


def show_operation_progress(
    operation: Callable, 
    description: str,
    success_message: str,
    error_message: str,
    *args, 
    **kwargs
) -> Any:
    """
    Show progress for a long-running operation.
    
    Args:
        operation: Function to call
        description: Description for the progress bar
        success_message: Message to show on success
        error_message: Message to show on error
        *args: Arguments to pass to the operation
        **kwargs: Keyword arguments to pass to the operation
        
    Returns:
        Result of the operation
        
    Raises:
        Exception: If the operation fails
    """
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TimeElapsedColumn()
    ) as progress:
        task = progress.add_task(description, total=None)
        
        try:
            start_time = time.time()
            result = operation(*args, **kwargs)
            elapsed = time.time() - start_time
            
            # Update task with success message
            progress.update(task, description=f"{success_message} ({elapsed:.2f}s)")
            progress.stop_task(task)
            
            return result
            
        except Exception as e:
            # Update task with error message
            progress.update(task, description=f"{error_message}: {str(e)}")
            progress.stop_task(task)
            raise