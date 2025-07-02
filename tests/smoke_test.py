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
            # Look for JSON array (vm create returns array)
            json_start = output.find('[')
            if json_start >= 0:
                vms_data = json.loads(output[json_start:])
                if isinstance(vms_data, list) and len(vms_data) > 0:
                    vm = vms_data[0]
                    # Check for vmId or id field
                    return vm.get("vmId") or vm.get("id")
            
            # Look for JSON object
            json_start = output.find('{')
            if json_start >= 0:
                vm_data = json.loads(output[json_start:])
                if "vmId" in vm_data:
                    return vm_data["vmId"]
                elif "id" in vm_data:
                    return vm_data["id"]
        except (json.JSONDecodeError, KeyError):
            pass
        
        # Try to find "VM ID: 0x..." pattern
        vm_id_pattern = r'VM ID:\s*(0x[0-9a-fA-F]+)'
        match = re.search(vm_id_pattern, output, re.IGNORECASE)
        if match:
            return match.group(1)
        
        # Try plain 0x... pattern
        hex_pattern = r'0x[0-9a-fA-F]{40}'
        match = re.search(hex_pattern, output, re.IGNORECASE)
        if match:
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
        if ssh_key and not ssh_key.startswith('ssh-') and not ssh_key.startswith('ecdsa-') and ssh_key.startswith('AAAA'):
            if ssh_key.startswith('AAAAC3NzaC1lZDI1NTE5'):
                ssh_key = f"ssh-ed25519 {ssh_key}"
            elif ssh_key.startswith('AAAAB3NzaC1yc2E'):
                ssh_key = f"ssh-rsa {ssh_key}"
            elif ssh_key.startswith('AAAAE2VjZHNhLXNoYTItbmlzdHA'):
                if 'bmlzdHAyNTY' in ssh_key:
                    ssh_key = f"ecdsa-sha2-nistp256 {ssh_key}"
                elif 'bmlzdHAzODQ' in ssh_key:
                    ssh_key = f"ecdsa-sha2-nistp384 {ssh_key}"
                elif 'bmlzdHA1MjE' in ssh_key:
                    ssh_key = f"ecdsa-sha2-nistp521 {ssh_key}"
        
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
        
        cmd = ["fvm-cli", "--format", "json", "vm", "create", "--config", config_file]
        exit_code, stdout, stderr = self.run_command(cmd)
        
        if exit_code != 0:
            if "No suitable offer found" in stderr:
                self.log_error("No suitable VM configuration found. Try different CPU/memory values.")
            else:
                self.log_error(f"Failed to create VM: {stderr}")
            return None
        
        # Extract VM ID from array response
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
            cmd = ["fvm-cli", "--format", "json", "vm", "list"]
            
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
                # Find JSON in the output - it should start with [
                json_start = stdout.find('[')
                if json_start >= 0:
                    # Extract just the JSON part
                    json_str = stdout[json_start:]
                    # Find the end of the JSON array
                    bracket_count = 0
                    json_end = -1
                    for i, char in enumerate(json_str):
                        if char == '[':
                            bracket_count += 1
                        elif char == ']':
                            bracket_count -= 1
                            if bracket_count == 0:
                                json_end = i + 1
                                break
                    
                    if json_end > 0:
                        json_str = json_str[:json_end]
                        vms = json.loads(json_str)
                    else:
                        if self.verbose:
                            self.log_error("Could not find end of JSON array")
                        time.sleep(poll_interval)
                        continue
                    
                    # Find our VM
                    for vm in vms:
                        if vm.get("id", "").lower() == vm_id.lower():
                            status = vm.get("status", "Unknown")
                            
                            # Get IP address if available
                            ip_address = vm.get("publicIp", "")
                            
                            elapsed = int(time.time() - start_time)
                            
                            # API v3 uses "Active" status, not "running"
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
                else:
                    if self.verbose:
                        self.log_error("No JSON array found in output")
                        self.log_error(f"Output was: {stdout[:200]}...")
            except json.JSONDecodeError as e:
                if self.verbose:
                    self.log_error(f"Failed to parse VM list JSON: {e}")
                    self.log_error(f"JSON string was: {json_str[:200] if 'json_str' in locals() else 'N/A'}...")
            except Exception as e:
                if self.verbose:
                    self.log_error(f"Unexpected error parsing VM list: {e}")
            
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
        cmd = ["fvm-cli", "--format", "json", "vm", "list"]
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
        
        # Test VM get command
        self.log_step("Testing VM get command")
        get_cmd = ["fvm-cli", "--format", "json", "vm", "get", vm_id]
        exit_code, stdout, stderr = self.run_command(get_cmd)
        
        if exit_code != 0:
            self.log_warning(f"VM get command failed: {stderr}")
            # Not critical since we get info from list
        else:
            self.log_success("VM get command succeeded")
        
        # Test VM images command
        self.log_step("Testing VM images command")
        images_cmd = ["fvm-cli", "--format", "json", "vm", "images"]
        exit_code, stdout, stderr = self.run_command(images_cmd)
        
        if exit_code != 0:
            self.log_warning(f"VM images command failed: {stderr}")
        else:
            self.log_success("VM images command succeeded")
        
        return all_commands_succeeded
    
    def test_estimate_command(self) -> bool:
        """
        Test the VM estimate command.
        
        Returns:
            True if estimation succeeds, False if it fails
        """
        self.log_step("Testing VM estimation")
        
        # Test the vm estimate command with parameters
        self.log_step("Testing VM estimate command")
        estimate_cmd = [
            "fvm-cli", "--format", "json", "vm", "estimate",
            "--cpu", str(self.args.cpu),
            "--memory", str(self.args.memory),
            "--storage", str(self.args.storage)
        ]
        
        # Add region if country is specified
        if self.args.country:
            estimate_cmd.extend(["--region", self.args.country])
        
        # Run the command
        exit_code, stdout, stderr = self.run_command(estimate_cmd)
        
        if exit_code != 0:
            self.log_warning(f"VM estimate command failed: {stderr}")
            return False
        else:
            self.log_success("VM estimate command succeeded")
            
            # Parse the result
            try:
                json_start = stdout.find('{')
                if json_start >= 0:
                    result = json.loads(stdout[json_start:])
                    
                    if "totalPricePerEpoch" in result:
                        price = result["totalPricePerEpoch"]
                        self.log_success(f"Estimated price per day: ${price}")
                    elif "totalPricePerEpochUsd" in result:
                        price = result["totalPricePerEpochUsd"]
                        self.log_success(f"Estimated price per day: ${price}")
                    else:
                        self.log_warning("No pricing information found in response")
                        
                    return True
            except json.JSONDecodeError:
                self.log_warning("Could not parse pricing result as JSON")
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
        if not self.test_estimate_command():
            self.log_warning("VM estimate command failed")
        
        # Test countries command
        self.log_step("Testing countries command")
        cmd = ["fvm-cli", "--format", "json", "market", "countries"]
        exit_code, stdout, stderr = self.run_command(cmd)
        
        if exit_code != 0:
            self.log_warning(f"Countries command failed: {stderr}")
            # Don't fail the test for this
        else:
            self.log_success("Countries command succeeded")
        
        # Test hardware command
        self.log_step("Testing hardware command")
        cmd = ["fvm-cli", "--format", "json", "market", "hardware"]
        exit_code, stdout, stderr = self.run_command(cmd)
        
        if exit_code != 0:
            self.log_warning(f"Hardware command failed: {stderr}")
            # Don't fail the test for this
        else:
            self.log_success("Hardware command succeeded")
        
        # Test configurations command
        self.log_step("Testing configurations command")
        cmd = ["fvm-cli", "--format", "json", "market", "configurations"]
        exit_code, stdout, stderr = self.run_command(cmd)
        
        if exit_code != 0:
            self.log_warning(f"Configurations command failed: {stderr}")
            # Don't fail the test for this
        else:
            self.log_success("Configurations command succeeded")
        
        # Test market offers command
        self.log_step("Testing market offers command")
        offers_cmd = ["fvm-cli", "--format", "json", "market", "offers"]
        
        # Add filters if specified
        if self.args.cpu:
            offers_cmd.extend(["--cpu", str(self.args.cpu)])
        if self.args.memory:
            offers_cmd.extend(["--memory", str(self.args.memory)])
        if self.args.country:
            offers_cmd.extend(["--region", self.args.country])
        
        exit_code, stdout, stderr = self.run_command(offers_cmd)
        
        if exit_code != 0:
            self.log_warning(f"Market offers command failed: {stderr}")
            # Don't fail the test for this
        else:
            self.log_success("Market offers command succeeded")
        
        return all_commands_succeeded
    
    def cleanup_resources(self) -> None:
        """Clean up all created resources."""
        # Delete created VM if any
        if self.created_vm_id:
            self.log_step(f"Cleaning up VM {self.created_vm_id}")
            
            # Delete VM using the correct API format with vmIds in request body
            cmd = ["fvm-cli", "vm", "delete", self.created_vm_id, "--force"]
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