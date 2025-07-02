"""
API client for interacting with the Fluence API.
"""

import time
import json
import requests
from typing import Dict, Any, Optional, List, Callable, Union


class FluenceAPIClient:
    """Client for interacting with the Fluence API."""
    
    def __init__(self, api_key: str, api_url: str = "https://api.fluence.dev", debug: bool = False):
        """
        Initialize the Fluence API client.
        
        Args:
            api_key: API key for authentication
            api_url: Base URL for the API
            debug: Whether to enable debug output
        """
        self.api_key = api_key
        self.api_url = api_url
        self.debug = debug
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # Rate limiting state
        self.last_request_time = 0
        self.min_request_interval = 0.5  # seconds
    
    def _wait_for_rate_limit(self):
        """Ensure requests aren't sent too quickly."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.min_request_interval:
            sleep_time = self.min_request_interval - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Make a request to the Fluence API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request data (for POST/PUT)
            params: Query parameters
            
        Returns:
            Response JSON
            
        Raises:
            Exception: If the request fails
        """
        # Wait for rate limiting
        self._wait_for_rate_limit()
        
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        
        if self.debug:
            print(f"url: {url}")
            print(f"headers: {self.headers}")
            print(f"method: {method}")
            
            if data:
                print(f"data: {json.dumps(data, indent=2)}")
            if params:
                print(f"params: {json.dumps(params, indent=2)}")
        
        try:
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                json=data,
                params=params
            )
            
            if self.debug:
                print(f"response status: {response.status_code}")
                try:
                    print(f"response: {json.dumps(response.json(), indent=2)}")
                except:
                    print(f"response: {response.text}")
            
            # Handle error responses with better parsing
            if response.status_code >= 400:
                error_message = f"API request failed: {response.status_code}"
                
                # Try to get error details from response
                try:
                    error_data = response.json()
                    if isinstance(error_data, dict) and "error" in error_data:
                        error_detail = error_data["error"]
                        error_message = f"API Error ({response.status_code}): {error_detail}"
                    else:
                        error_message += f" - {response.reason}"
                except:
                    error_message += f" - {response.reason}"
                
                # Add specific handling for common status codes
                if response.status_code == 401:
                    error_message = "Authentication failed. Please check your API key."
                elif response.status_code == 403:
                    error_message = "Access forbidden. Your API key may not have the required permissions."
                elif response.status_code == 404:
                    error_message = f"Resource not found: {url}"
                elif response.status_code == 422:
                    error_message = "Invalid request data. " + error_message
                
                raise Exception(error_message)
            
            # Parse response
            if response.text and response.text.strip():
                return response.json()
            else:
                return {}
                
        except requests.exceptions.RequestException as e:
            raise Exception(f"Request failed: {str(e)}")
    
    def list_vms(self) -> List[Dict[str, Any]]:
        """
        List all VMs.
        
        Returns:
            List of VM objects
        """
        return self._make_request("GET", "vms/v3")
    
    def get_vm(self, vm_id: str) -> Dict[str, Any]:
        """
        Get VM details.
        
        Args:
            vm_id: VM ID
            
        Returns:
            VM details
        """
        # Get all VMs and find the specific one by ID
        all_vms = self._make_request("GET", "vms/v3")
        
        # Find the VM with matching ID (case-insensitive comparison)
        for vm in all_vms:
            if vm.get("id", "").lower() == vm_id.lower():
                return vm
                
        # VM not found
        raise Exception(f"VM with ID {vm_id} not found")
    
    def get_vm_status(self, vm_ids: List[str]) -> List[Dict[str, Any]]:
        """
        Get status for specific VMs using the status endpoint.
        
        Args:
            vm_ids: List of VM IDs
            
        Returns:
            List of VM status objects
        """
        # Use the /vms/v3/status endpoint with comma-separated IDs
        params = {
            "ids": ",".join(vm_ids)
        }
        return self._make_request("GET", "vms/v3/status", params=params)
    
    def create_vm(self, name: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Create a new VM.
        
        Args:
            name: VM name (note: this is stored in config, not used directly)
            config: VM configuration
            
        Returns:
            List of created VM details
        """
        result = self._make_request("POST", "vms/v3", data=config)
        # API returns an array, ensure we return it as-is
        if isinstance(result, list):
            return result
        else:
            # Wrap in list if single object returned (backward compatibility)
            return [result]
    
    def delete_vm(self, vm_id: str) -> Dict[str, Any]:
        """
        Delete a VM.
        
        Args:
            vm_id: VM ID
            
        Returns:
            Deletion result
        """
        data = {
            "vmIds": [vm_id]
        }
        return self._make_request("DELETE", "vms/v3", data=data)
    
    def update_vm(self, vm_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update VM configuration (name and/or open ports).
        
        Args:
            vm_id: VM ID
            updates: Dictionary with optional 'vmName' and/or 'openPorts' keys
            
        Returns:
            Update result
        """
        # Build update request according to API schema
        update_data = {
            "updates": [
                {
                    "id": vm_id,
                    **updates  # This will include vmName and/or openPorts if provided
                }
            ]
        }
        
        return self._make_request("PATCH", "vms/v3", data=update_data)
    
    def get_available_countries(self) -> List[str]:
        """
        Get available countries.
        
        Returns:
            List of country codes
        """
        try:
            return self._make_request("GET", "marketplace/countries")
        except Exception as e:
            if self.debug:
                print(f"Error getting available countries: {str(e)}")
            return []
    
    def get_vm_pricing(self, cpu: int, memory: int, region: Optional[str] = None) -> Dict[str, Any]:
        """
        Get VM pricing estimate.
        
        Args:
            cpu: Number of CPU cores
            memory: Memory in GB
            region: Region code (optional)
            
        Returns:
            Pricing information
        """
        # Build request body for estimate
        data = {
            "constraints": {
                "basicConfiguration": f"cpu-{cpu}-ram-{memory}gb-storage-25gb"
            },
            "instances": 1
        }
        
        # Add datacenter constraint if region is specified
        if region:
            data["constraints"]["datacenter"] = {
                "countries": [region]
            }
            
        try:
            result = self._make_request("POST", "vms/v3/estimate", data=data)
            
            # Add calculated hourly price if not present
            if "totalPricePerEpoch" in result and "hourlyPriceUsd" not in result:
                daily_price = float(result["totalPricePerEpoch"])
                result["hourlyPriceUsd"] = f"{daily_price / 24:.6f}"
                result["dailyPriceUsd"] = result["totalPricePerEpoch"]
                
            return result
        except Exception as e:
            if self.debug:
                print(f"Error getting pricing estimate: {e}")
            return {"dailyPriceUsd": "Unknown", "hourlyPriceUsd": "Unknown"}
    
    def estimate_vm(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Estimate VM cost without creating it.
        
        Args:
            config: VM configuration dictionary
                
        Returns:
            Estimation result with pricing information
        """
        try:
            result = self._make_request("POST", "vms/v3/estimate", data=config)
            
            # Add calculated hourly price if not present
            if "totalPricePerEpoch" in result and "hourlyPriceUsd" not in result:
                daily_price = float(result["totalPricePerEpoch"])
                result["hourlyPriceUsd"] = f"{daily_price / 24:.6f}"
                
            return result
        except Exception as e:
            if self.debug:
                print(f"Error getting VM cost estimate: {e}")
            return {"totalPricePerEpochUsd": "Unknown", "hourlyPriceUsd": "Unknown"}
    
    def get_hardware_options(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get available hardware options.
        
        Returns:
            Dictionary of hardware options
        """
        try:
            return self._make_request("GET", "marketplace/hardware")
        except Exception as e:
            if self.debug:
                print(f"Error getting hardware options: {str(e)}")
            return {"cpu": [], "memory": [], "storage": []}
    
    def get_basic_configurations(self) -> List[str]:
        """
        Get available basic configurations from the API.
        
        Returns:
            List of configuration strings
        """
        try:
            return self._make_request("GET", "marketplace/basic_configurations")
        except Exception as e:
            if self.debug:
                print(f"Error getting basic configurations: {str(e)}")
            # Return default configurations as fallback
            return [
                "cpu-1-ram-1gb-storage-25gb",
                "cpu-1-ram-2gb-storage-25gb", 
                "cpu-2-ram-2gb-storage-25gb",
                "cpu-2-ram-4gb-storage-25gb",
                "cpu-4-ram-8gb-storage-25gb"
            ]
    
    def get_default_images(self) -> List[Dict[str, Any]]:
        """
        Get list of default OS images.
        
        Returns:
            List of OS image objects with metadata
        """
        try:
            return self._make_request("GET", "vms/v3/default_images")
        except Exception as e:
            if self.debug:
                print(f"Error getting default images: {str(e)}")
            return []
    
    def get_marketplace_offers(self, constraints: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Search marketplace for available compute offers.
        
        Args:
            constraints: Optional constraints for filtering offers
            
        Returns:
            List of marketplace offerings
        """
        data = constraints or {}
        try:
            return self._make_request("POST", "marketplace/offers", data=data)
        except Exception as e:
            if self.debug:
                print(f"Error getting marketplace offers: {str(e)}")
            return []
    
    def add_ssh_key(self, name: str, public_key: str) -> Dict[str, Any]:
        """
        Add a new SSH key.
        
        Args:
            name: Display name for the key
            public_key: SSH public key in OpenSSH format
            
        Returns:
            Created SSH key details
        """
        # Validate and format SSH key
        formatted_key = self._format_ssh_key(public_key)
        
        data = {
            "name": name,
            "publicKey": formatted_key
        }
        
        return self._make_request("POST", "ssh_keys", data=data)
    
    def list_ssh_keys(self) -> List[Dict[str, Any]]:
        """
        List all SSH keys.
        
        Returns:
            List of SSH key objects
        """
        return self._make_request("GET", "ssh_keys")
    
    def delete_ssh_key(self, fingerprint: str) -> Dict[str, Any]:
        """
        Delete an SSH key.
        
        Args:
            fingerprint: SSH key fingerprint
            
        Returns:
            Deletion result
        """
        data = {
            "fingerprint": fingerprint
        }
        return self._make_request("DELETE", "ssh_keys", data=data)
    
    def _format_ssh_key(self, key: str) -> str:
        """
        Ensures SSH key is properly formatted with correct algorithm prefix.
        
        Args:
            key: SSH key to format
            
        Returns:
            Properly formatted SSH key
            
        Raises:
            ValueError: If key format is invalid
        """
        key = key.strip()
        
        # If key already has proper format, return as-is
        if key.startswith(('ssh-rsa ', 'ssh-ed25519 ', 'ecdsa-sha2-')):
            return key
        
        # Try to detect key type from the base64 content
        if key.startswith('AAAA'):
            if key.startswith('AAAAC3NzaC1lZDI1NTE5'):
                return f"ssh-ed25519 {key}"
            elif key.startswith('AAAAB3NzaC1yc2E'):
                return f"ssh-rsa {key}"
            elif key.startswith('AAAAE2VjZHNhLXNoYTItbmlzdHA'):
                # ECDSA keys need more specific detection
                if 'bmlzdHAyNTY' in key:  # nistp256
                    return f"ecdsa-sha2-nistp256 {key}"
                elif 'bmlzdHAzODQ' in key:  # nistp384
                    return f"ecdsa-sha2-nistp384 {key}"
                elif 'bmlzdHA1MjE' in key:  # nistp521
                    return f"ecdsa-sha2-nistp521 {key}"
        
        raise ValueError(
            "Invalid SSH key format. Key must be in OpenSSH format "
            "(ssh-rsa, ssh-ed25519, or ecdsa-sha2-*)"
        )

    def wait_for_vm_status(self, vm_id: str, status: str, timeout: int = 300, 
                         check_interval: int = 5, callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Wait for a VM to reach a specific status.
        
        Args:
            vm_id: VM ID
            status: Status to wait for (case-sensitive: Active, Launching, etc.)
            timeout: Maximum time to wait in seconds
            check_interval: Time between checks in seconds
            callback: Optional callback function to call with VM data and elapsed time
            
        Returns:
            VM details once it reaches the desired status
            
        Raises:
            TimeoutError: If VM doesn't reach the desired status within the timeout
        """
        start_time = time.time()
        elapsed = 0
        
        while elapsed < timeout:
            try:
                # Use the more efficient status endpoint when available
                vm_status_list = self.get_vm_status([vm_id])
                if vm_status_list:
                    vm_data = vm_status_list[0]
                    # Get full VM data if needed
                    if "resources" not in vm_data:
                        vm_data = self.get_vm(vm_id)
                else:
                    # Fallback to getting full VM data
                    vm_data = self.get_vm(vm_id)
                    
                current_status = vm_data.get("status", "")
                
                # If callback is provided, call it with VM data and elapsed time
                if callback:
                    callback(vm_data, elapsed)
                
                # Check if VM has reached the desired status (case-sensitive)
                if current_status == status:
                    return vm_data
            except Exception as e:
                if self.debug:
                    print(f"Error checking VM status: {e}")
            
            # Wait for next check
            time.sleep(check_interval)
            elapsed = time.time() - start_time
        
        raise TimeoutError(f"Timeout waiting for VM {vm_id} to reach status '{status}'")