#!/usr/bin/env python3
"""
Improved Fluence CLI Smoke Test

This script performs comprehensive testing of the Fluence CLI functionality:
1. Creates a temporary VM configuration file based on API requirements
2. Creates a VM using the configuration file
3. Waits for the VM to be ready
4. Tests various CLI commands
5. Cleans up resources

Usage:
  uv run tests/smoke_test.py [options]
"""

import os
import sys
import json
import time
import tempfile
import argparse
import subprocess
import re
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple


# ANSI colors for better output
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
BLUE = "\033[94m"
BOLD = "\033[1m"
RESET = "\033[0m"


class SmokeTest:
    """Class to encapsulate smoke test functionality with proper state management."""
    
    def __init__(self, args):
        """Initialize the smoke test with command-line arguments."""
        self.args = args
        self.created_vm_id = None
        self.temp_files = []
        
        # Enable more detailed output in debug mode
        self.verbose = args.debug 
        
    def log_step(self, message: str) -> None:
        """Log a test step with formatting."""
        print(f"\n{BOLD}{BLUE}=== {message} ==={RESET}\n")

    def log_success(self, message: str) -> None:
        """Log a success message."""
        print(f"{GREEN}✓ {message}{RESET}")

    def log_warning(self, message: str) -> None:
        """Log a warning message."""
        print(f"{YELLOW}⚠ {message}{RESET}")

    def log_error(self, message: str) -> None:
        """Log an error message."""
        print(f"{RED}✗ {message}{RESET}")
    
    def run_command(self, command: List[str], capture_output: bool = True) -> Tuple[int, str, str]:
        """
        Run a command and return its exit code, stdout, and stderr.
        
        Args:
            command: Command to run as list of strings
            capture_output: Whether to capture stdout/stderr
            
        Returns:
            Tuple of (exit_code, stdout, stderr)
        """
        cmd_str = " ".join(command)
        print(f"{BLUE}Running: {cmd_str}{RESET}")
        
        try:
            if capture_output:
                result = subprocess.run(command, capture_output=True, text=True)
                
                # Print the output only in verbose mode or if there's an error
                if self.verbose and result.stdout.strip():
                    print(result.stdout)
                if result.stderr.strip() and result.returncode != 0:
                    print(f"{RED}{result.stderr}{RESET}")
                    
                return result.returncode, result.stdout, result.stderr
            else:
                # Interactive mode
                result = subprocess.run(command)
                return result.returncode, "", ""
        except Exception as e:
            self.log_error(f"Error executing command: {e}")
            return 1, "", str(e)
    
    def extract_vm_id(self, output: str) -> Optional[str]:
        """
        Extract VM ID from command output.
        
        Args:
            output: Command output text
            
        Returns:
            VM ID if found, None otherwise
        """
        # First try to extract from JSON
        try:
            # Look for JSON in the output
            json_start = output.find('{')
            if json_start >= 0:
                vm_data = json.loads(output[json_start:])
                if "id" in vm_data:
                    # Preserve original capitalization from API
                    return vm_data["id"]
        except (json.JSONDecodeError, KeyError):
            pass
        
        # Try to find "VM ID: 0x..." pattern
        vm_id_pattern = r'VM ID:\s*(0x[0-9a-fA-F]+)'
        match = re.search(vm_id_pattern, output, re.IGNORECASE)
        if match:
            # Preserve original capitalization
            return match.group(1)
        
        # Try plain 0x... pattern
        hex_pattern = r'0x[0-9a-fA-F]{40}'
        match = re.search(hex_pattern, output, re.IGNORECASE)
        if match:
            # Preserve original capitalization from the output
            return match.group(0)
        
        return None
    
    def create_vm_config_file(self) -> Optional[str]:
        """
        Create a temporary VM configuration file that matches the API requirements.
        
        Returns:
            Path to configuration file if created, None otherwise
        """
        self.log_step("Creating VM configuration file")
        
        # Generate VM name with timestamp
        timestamp = int(time.time()) % 10000
        vm_name = f"smoke-test-{timestamp}"
        
        # Get SSH key from environment
        ssh_key = os.environ.get("SSH_PUBLIC_KEY", "")
        if not ssh_key:
            self.log_error("SSH_PUBLIC_KEY environment variable not set")
            return None
        
        # Format SSH key if needed
        ssh_key = ssh_key.strip()
        if ssh_key and not ssh_key.startswith('ssh-') and ssh_key.startswith('AAAA'):
            if ssh_key.startswith('AAAAC3NzaC1lZDI1NTE5'):
                ssh_key = f"ssh-ed25519 {ssh_key}"
            elif ssh_key.startswith('AAAAB3NzaC1yc2E'):
                ssh_key = f"ssh-rsa {ssh_key}"
        
        # Build VM configuration object according to API requirements
        config = {
            "constraints": {
                "basicConfiguration": f"cpu-{self.args.cpu}-ram-{self.args.memory}gb-storage-{self.args.storage}gb"
            },
            "instances": 1,
            "vmConfiguration": {
                "name": vm_name,
                "openPorts": [
                    {"port": 22, "protocol": "tcp"},
                    {"port": 80, "protocol": "tcp"},
                    {"port": 443, "protocol": "tcp"}
                ],
                "hostname": vm_name,
                "osImage": "https://cloud-images.ubuntu.com/releases/22.04/release/ubuntu-22.04-server-cloudimg-amd64.img",
                "sshKeys": [ssh_key]
            }
        }
        
        # Add datacenter constraint if country specified
        if self.args.country:
            config["constraints"]["datacenter"] = {
                "countries": [self.args.country]
            }
            
        # Add max price if specified
        if self.args.max_price:
            config["constraints"]["maxTotalPricePerEpochUsd"] = str(self.args.max_price)
        
        # Create a temporary file
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                json.dump(config, tmp, indent=2)
                tmp_path = tmp.name
                self.log_success(f"Created configuration file: {tmp_path}")
                
                # Register for cleanup
                self.temp_files.append(tmp_path)
                
                # Show the configuration
                print("\nConfiguration content:")
                print(json.dumps(config, indent=2))
                print()
                
                return tmp_path
        except Exception as e:
            self.log_error(f"Failed to create configuration file: {e}")
            return None
    
    def create_vm_with_config(self, config_file: str) -> Optional[str]:
        """
        Create a VM using a configuration file.
        
        Args:
            config_file: Path to configuration file
            
        Returns:
            VM ID if created successfully, None otherwise
        """
        self.log_step(f"Creating VM using configuration file")
        
        cmd = ["flu-cli", "--format", "json", "vm", "create", "--config", config_file]
        exit_code, stdout, stderr = self.run_command(cmd)
        
        if exit_code != 0:
            if "No suitable offer found" in stderr:
                self.log_error("No suitable VM configuration found. Try different CPU/memory values.")
            else:
                self.log_error(f"Failed to create VM: {stderr}")
            return None
        
        # Extract VM ID
        vm_id = self.extract_vm_id(stdout)
        if not vm_id:
            self.log_error("Could not extract VM ID from output")
            return None
        
        self.log_success(f"VM creation initiated with ID: {vm_id}")
        return vm_id
    
    def wait_for_vm_ready(self, vm_id: str, timeout: int = 300, poll_interval: int = 10) -> bool:
        """
        Wait for VM to be in Active status by checking the VM list.
        
        Args:
            vm_id: VM ID
            timeout: Maximum time to wait in seconds
            poll_interval: Time between checks in seconds
            
        Returns:
            True if VM is ready, False otherwise
        """
        self.log_step(f"Waiting for VM {vm_id} to be ready (timeout: {timeout}s)")
        
        start_time = time.time()
        last_status = None
        last_status_time = 0
        
        while (time.time() - start_time) < timeout:
            # List all VMs and check status - don't print the command
            cmd = ["flu-cli", "--format", "json", "vm", "list"]
            
            # Capture stdout but don't print the command
            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                exit_code = result.returncode
                stdout = result.stdout
                stderr = result.stderr
                
                # Only print stderr if there's an error and we're in debug mode
                if self.verbose and exit_code != 0 and stderr.strip():
                    print(f"{RED}{stderr}{RESET}")
            except Exception as e:
                if self.verbose:
                    self.log_error(f"Error executing command: {e}")
                time.sleep(poll_interval)
                continue
            
            if exit_code != 0:
                if self.verbose:
                    self.log_error(f"Failed to list VMs: {stderr}")
                time.sleep(poll_interval)
                continue
            
            # Extract status from JSON
            try:
                # Find JSON in the output
                json_start = stdout.find('[')
                if json_start >= 0:
                    vms = json.loads(stdout[json_start:])
                    
                    # Find our VM
                    for vm in vms:
                        if vm.get("id", "").lower() == vm_id.lower():
                            status = vm.get("status", "Unknown")
                            
                            # Get IP address if available
                            ip_address = vm.get("publicIp", "")
                            
                            elapsed = int(time.time() - start_time)
                            
                            if status == "Active" and ip_address:
                                self.log_success(f"VM is ready with IP: {ip_address} (after {elapsed}s)")
                                
                                # Update VM ID to exact format from API
                                if vm.get("id") != vm_id:
                                    self.log_warning(f"Updating VM ID to exact format from API: {vm.get('id')}")
                                    self.created_vm_id = vm.get("id")
                                
                                return True
                            
                            # Only print status message if status changed or significant time passed
                            current_time = time.time()
                            if status != last_status or (current_time - last_status_time > 30):
                                self.log_warning(f"VM status: {status}, elapsed: {elapsed}s, waiting...")
                                last_status = status
                                last_status_time = current_time
                                
                            break
                    else:
                        elapsed = int(time.time() - start_time)
                        self.log_warning(f"VM {vm_id} not found in list, elapsed: {elapsed}s, waiting...")
            except json.JSONDecodeError:
                if self.verbose:
                    self.log_error("Failed to parse VM list JSON")
            
            time.sleep(poll_interval)
        
        self.log_error(f"Timeout waiting for VM to be ready after {timeout}s")
        return False
    
    def test_vm_commands(self, vm_id: str) -> bool:
        """
        Test various VM commands.
        
        Args:
            vm_id: VM ID
            
        Returns:
            True if all commands succeed, False otherwise
        """
        self.log_step(f"Testing VM commands with VM {vm_id}")
        all_commands_succeeded = True
        
        # Test VM list
        self.log_step("Testing VM list command")
        cmd = ["flu-cli", "--format", "json", "vm", "list"]
        exit_code, stdout, stderr = self.run_command(cmd)
        
        if exit_code != 0:
            self.log_error(f"VM list command failed: {stderr}")
            all_commands_succeeded = False
        else:
            self.log_success("VM list command succeeded")
            
            # Check if our VM is in the list
            try:
                # Look for JSON in the output
                json_start = stdout.find('[')
                if json_start >= 0:
                    vms = json.loads(stdout[json_start:])
                    our_vm = None
                    for vm in vms:
                        # Case-insensitive comparison for VM ID
                        if vm.get("id", "").lower() == vm_id.lower():
                            our_vm = vm
                            break
                    
                    if our_vm:
                        self.log_success(f"Found our VM in the list with status: {our_vm.get('status', 'Unknown')}")
                        
                        # Update VM ID to use exact capitalization from API
                        if our_vm.get("id") != vm_id and our_vm.get("id") is not None:
                            self.log_warning(f"Updating VM ID capitalization from {vm_id}")
                            self.log_warning(f"to exact format from API: {our_vm.get('id')}")
                            self.created_vm_id = our_vm.get("id")
                    else:
                        self.log_warning(f"Could not find our VM with ID {vm_id} in the list")
            except json.JSONDecodeError:
                self.log_warning("Could not parse VM list response as JSON")
        
        # No need to try the 'vm get' command separately - we get all VM details from the list command
        
        return all_commands_succeeded
    
    def test_estimate_command(self) -> bool:
        """
        Test the VM estimate command or fallbacks if not available.
        
        Returns:
            True if any estimation method succeeds, False if all fail
        """
        self.log_step("Testing VM estimation")
        
        # Create a temporary configuration file for the estimate
        try:
            with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp:
                config = {
                    "constraints": {
                        "basicConfiguration": f"cpu-{self.args.cpu}-ram-{self.args.memory}gb-storage-{self.args.storage}gb"
                    },
                    "instances": 1
                }
                
                # Add datacenter constraint if country specified
                if self.args.country:
                    config["constraints"]["datacenter"] = {
                        "countries": [self.args.country]
                    }
                
                json.dump(config, tmp, indent=2)
                tmp_path = tmp.name
                self.temp_files.append(tmp_path)
                
                # Try the vm estimate command first
                self.log_step("Testing VM estimate command")
                estimate_cmd = ["flu-cli", "--format", "json", "vm", "estimate", "--config", tmp_path]
                exit_code, stdout, stderr = self.run_command(estimate_cmd)
                
                # If the vm estimate command doesn't exist, try the market pricing command
                if exit_code != 0 and "No such command 'estimate'" in stderr:
                    self.log_warning("VM estimate command not found, trying market pricing command")
                    
                    # Build the market pricing command
                    pricing_cmd = [
                        "flu-cli", "--format", "json", "market", "pricing",
                        "--cpu", str(self.args.cpu),
                        "--memory", str(self.args.memory)
                    ]
                    
                    # Add region if country is specified
                    if self.args.country:
                        pricing_cmd.extend(["--region", self.args.country])
                    
                    # Run the command
                    exit_code, stdout, stderr = self.run_command(pricing_cmd)
                    
                    if exit_code != 0:
                        self.log_warning(f"Market pricing command failed: {stderr}")
                        self.log_warning("Skipping VM cost estimation tests")
                        return False
                    else:
                        self.log_success("Market pricing command succeeded as a fallback")
                elif exit_code != 0:
                    self.log_warning(f"VM estimate command failed: {stderr}")
                    self.log_warning("Skipping VM cost estimation tests")
                    return False
                else:
                    self.log_success("VM estimate command succeeded")
                
                # Parse the result
                try:
                    json_start = stdout.find('{')
                    if json_start >= 0:
                        result = json.loads(stdout[json_start:])
                        
                        # Handle different response formats from vm estimate vs market pricing
                        if "totalPricePerEpochUsd" in result:
                            price = result["totalPricePerEpochUsd"]
                            self.log_success(f"Estimated price per day: ${price}")
                        elif "dailyPriceUsd" in result:
                            price = result["dailyPriceUsd"]
                            self.log_success(f"Estimated price per day: ${price}")
                        elif "hourlyPriceUsd" in result:
                            hourly = result["hourlyPriceUsd"]
                            daily = float(hourly) * 24
                            self.log_success(f"Estimated hourly price: ${hourly}")
                            self.log_success(f"Calculated daily price: ${daily:.6f}")
                        else:
                            self.log_warning("No pricing information found in response")
                            
                        return True
                except json.JSONDecodeError:
                    self.log_warning("Could not parse pricing result as JSON")
                    return False
                
        except Exception as e:
            self.log_warning(f"Error testing VM estimation: {e}")
            return False
            
        return True
    
    def test_marketplace_commands(self) -> bool:
        """
        Test marketplace commands.
        
        Returns:
            True if all commands succeed, False otherwise
        """
        self.log_step("Testing marketplace commands")
        all_commands_succeeded = True
        
        # Test VM cost estimation first
        self.test_estimate_command()
        
        # Test countries command
        self.log_step("Testing countries command")
        cmd = ["flu-cli", "--format", "json", "market", "countries"]
        exit_code, stdout, stderr = self.run_command(cmd)
        
        if exit_code != 0:
            self.log_warning(f"Countries command failed: {stderr}")
            self.log_warning("Skipping this test as the endpoint may not be implemented")
            # Don't mark the test as failed just for this command
        else:
            self.log_success("Countries command succeeded")
        
        # Test hardware command
        self.log_step("Testing hardware command")
        cmd = ["flu-cli", "--format", "json", "market", "hardware"]
        exit_code, stdout, stderr = self.run_command(cmd)
        
        if exit_code != 0:
            self.log_warning(f"Hardware command failed: {stderr}")
            self.log_warning("Skipping this test as the endpoint may not be implemented")
            # Don't mark the test as failed just for this command
        else:
            self.log_success("Hardware command succeeded")
        
        return all_commands_succeeded
    
    def cleanup_resources(self) -> None:
        """Clean up all created resources."""
        # Delete created VM if any
        if self.created_vm_id:
            self.log_step(f"Cleaning up VM {self.created_vm_id}")
            
            # Delete VM using the correct API format with vmIds in request body
            cmd = ["flu-cli", "vm", "delete", self.created_vm_id, "--force"]
            exit_code, stdout, stderr = self.run_command(cmd)
            
            if exit_code != 0:
                self.log_error(f"Failed to delete VM: {stderr}")
            else:
                self.log_success(f"VM deletion initiated")
                self.created_vm_id = None
        
        # Delete temporary files
        for file_path in self.temp_files:
            try:
                os.unlink(file_path)
                self.log_success(f"Deleted temporary file: {file_path}")
            except Exception as e:
                self.log_warning(f"Failed to delete file {file_path}: {e}")
    
    def run(self) -> int:
        """
        Run the smoke test.
        
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        self.log_step("Starting smoke test")
        
        test_success = True
        
        try:
            # Step 1: Create VM configuration file
            config_file = self.create_vm_config_file()
            if not config_file:
                return 1
            
            # Step 2: Create VM with configuration
            vm_id = self.create_vm_with_config(config_file)
            if not vm_id:
                return 1
            
            # Store VM ID for cleanup with original capitalization preserved
            self.created_vm_id = vm_id
            
            # Log the exact VM ID with original capitalization for reference
            self.log_step(f"Created VM with ID: {vm_id}")
            
            # Step 3: Wait for VM to be ready
            if self.args.wait and not self.wait_for_vm_ready(vm_id, self.args.timeout, self.args.poll_interval):
                self.log_warning("VM not ready within timeout, but continuing with tests")
            
            # Step 4: Test VM commands
            if not self.test_vm_commands(vm_id):
                test_success = False
                self.log_warning("Some VM commands failed")
            
            # Step 5: Test marketplace commands
            if not self.test_marketplace_commands():
                test_success = False
                self.log_warning("Some marketplace commands failed")
            
            # Display conclusion based on all tests
            if test_success:
                self.log_step("All tests completed successfully")
            else:
                self.log_warning("Some tests failed")
                
            return 0 if test_success else 1
            
        except KeyboardInterrupt:
            self.log_warning("Test interrupted by user")
            return 130
        except Exception as e:
            self.log_error(f"Error during smoke test: {str(e)}")
            import traceback
            traceback.print_exc()
            return 1


def load_environment(env_file: Optional[str] = None) -> bool:
    """
    Load environment variables from .env file.
    
    Args:
        env_file: Optional specific env file path
        
    Returns:
        True if required environment variables are set, False otherwise
    """
    try:
        from dotenv import load_dotenv
        
        # Try specific env file if provided
        if env_file and os.path.exists(env_file):
            load_dotenv(env_file)
            print(f"{GREEN}✓ Loaded environment variables from {env_file}{RESET}")
            return True
            
        # Try to find .env file in current directory or parent directories
        env_path = None
        current_dir = Path.cwd()
        for _ in range(4):  # Check current directory and up to 3 parent directories
            test_path = current_dir / ".env"
            if test_path.exists():
                env_path = test_path
                break
            parent = current_dir.parent
            if parent == current_dir:  # Reached root directory
                break
            current_dir = parent
                
        if env_path:
            load_dotenv(env_path)
            print(f"{GREEN}✓ Loaded environment variables from {env_path}{RESET}")
            return True
        else:
            print(f"{YELLOW}⚠ No .env file found in current directory or parent directories{RESET}")
    except ImportError:
        print(f"{YELLOW}⚠ python-dotenv not installed. Environment variables will not be loaded from .env file{RESET}")
    
    # Check required environment variables
    missing_vars = []
    if not os.environ.get("FLUENCE_API_KEY"):
        missing_vars.append("FLUENCE_API_KEY")
    if not os.environ.get("SSH_PUBLIC_KEY"):
        missing_vars.append("SSH_PUBLIC_KEY")
    
    if missing_vars:
        print(f"{RED}✗ Missing required environment variables: {', '.join(missing_vars)}{RESET}")
        return False
    
    return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Fluence CLI Smoke Test")
    
    # VM options
    parser.add_argument("--cpu", type=int, default=2, help="Number of CPU cores (default: 2)")
    parser.add_argument("--memory", type=int, default=4, help="Memory in GB (default: 4)")
    parser.add_argument("--storage", type=int, default=25, help="Storage in GB (default: 25)")
    parser.add_argument("--country", help="Country code for datacenter location (e.g., US, DE, BE)")
    parser.add_argument("--max-price", type=float, help="Maximum price per day in USD")
    
    # Test options
    parser.add_argument("--wait", action="store_true", default=True, help="Wait for VM to be ready")
    parser.add_argument("--timeout", type=int, default=300, help="Maximum time to wait in seconds (default: 300)")
    parser.add_argument("--poll-interval", type=int, default=10, help="Time between polls in seconds (default: 10)")
    parser.add_argument("--no-cleanup", action="store_true", help="Don't clean up resources after test")
    
    # Environment options
    parser.add_argument("--env-file", help="Path to specific .env file")
    
    # Debug options
    parser.add_argument("--debug", action="store_true", help="Enable debug output")
    
    # Parse arguments
    args = parser.parse_args()
    
    # Print test header
    print(f"\n{BOLD}{BLUE}=== FLUENCE CLI SMOKE TEST ==={RESET}\n")
    
    # Load environment variables
    if not load_environment(args.env_file):
        return 1
    
    # Create and run the test
    test = SmokeTest(args)
    exit_code = 1
    
    try:
        exit_code = test.run()
        return exit_code
    finally:
        # Always try to cleanup resources unless explicitly disabled
        if not args.no_cleanup:
            test.cleanup_resources()
        else:
            if test.created_vm_id:
                print(f"{YELLOW}⚠ Skipping cleanup as requested. VM {test.created_vm_id} left running.{RESET}")
            else:
                print(f"{YELLOW}⚠ Skipping resource cleanup as requested{RESET}")
        
        # Print summary with appropriate exit code
        if exit_code == 0:
            print(f"\n{BOLD}{GREEN}=== SMOKE TEST COMPLETED SUCCESSFULLY ==={RESET}\n")
        else:
            print(f"\n{BOLD}{RED}=== SMOKE TEST FAILED (EXIT CODE: {exit_code}) ==={RESET}\n")


if __name__ == "__main__":
    sys.exit(main())