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
            
            # Handle error responses
            if response.status_code >= 400:
                error_message = f"API request failed: {response.status_code} {response.reason} for url: {url}"
                
                # Try to get error details from response
                try:
                    error_details = response.json()
                    if isinstance(error_details, dict) and "error" in error_details:
                        error_message += f" - Details: {json.dumps(error_details)}"
                except:
                    pass
                
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
        raise Exception(f"VM with ID {vm_id} not found in the list of VMs")
        
    def create_vm(self, name: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new VM.
        
        Args:
            name: VM name
            config: VM configuration
            
        Returns:
            Created VM details
        """
        return self._make_request("POST", "vms/v3", data=config)
    
    def delete_vm(self, vm_id: str) -> Dict[str, Any]:
        """
        Delete a VM.
        
        Args:
            vm_id: VM ID
            
        Returns:
            Deletion result
        """
        # Use correct API format with vmIds array in request body
        # The endpoint is DELETE /vms/v3, not DELETE /vms/v3/{vm_id}
        # The VM ID is passed in the request body, not in the URL
        data = {
            "vmIds": [vm_id]
        }
        return self._make_request("DELETE", "vms/v3", data=data)
    
    def scale_vm(self, vm_id: str, cpu: int, memory: int, cpu_manufacturer: str = None, cpu_architecture: str = None) -> Dict[str, Any]:
        """
        Scale VM resources.
        
        Args:
            vm_id: VM ID
            cpu: Number of CPU cores
            memory: Memory in GB
            cpu_manufacturer: CPU manufacturer (optional)
            cpu_architecture: CPU architecture (optional)
            
        Returns:
            Updated VM details
        """
        data = {
            "cpu": cpu,
            "memory": memory
        }
        
        if cpu_manufacturer:
            data["cpu_manufacturer"] = cpu_manufacturer
        
        if cpu_architecture:
            data["cpu_architecture"] = cpu_architecture
        
        return self._make_request("PUT", f"vms/v3/{vm_id}/scale", data=data)
    
    def get_available_countries(self) -> List[str]:
        """
        Get available countries.
        
        Returns:
            List of country codes
        """
        # Use correct countries endpoint according to documentation
        try:
            return self._make_request("GET", "marketplace/v3/countries")
        except Exception as e:
            # Handle error gracefully if endpoint not available
            if self.debug:
                print(f"Error getting available countries: {str(e)}")
            return []
    
    def get_vm_pricing(self, cpu: int, memory: int, region: Optional[str] = None) -> Dict[str, Any]:
        """
        Get VM pricing.
        
        Args:
            cpu: Number of CPU cores
            memory: Memory in GB
            region: Region code (optional)
            
        Returns:
            Pricing information
        """
        # FIXED: Use the correct /vms/v3/estimate endpoint with POST method
        # This endpoint expects a request body similar to VM creation
        
        # Build request body
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
            return self._make_request("POST", "vms/v3/estimate", data=data)
        except Exception as e:
            if self.debug:
                print(f"Error getting pricing estimate: {e}")
            # Return a minimal result to avoid crashing
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
            return self._make_request("POST", "vms/v3/estimate", data=config)
        except Exception as e:
            if self.debug:
                print(f"Error getting VM cost estimate: {e}")
            # Return a minimal result to avoid crashing
            return {"totalPricePerEpochUsd": "Unknown", "hourlyPriceUsd": "Unknown"}
    
    def get_hardware_options(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Get available hardware options.
        
        Returns:
            Dictionary of hardware options
        """
        # Use correct hardware options endpoint
        try:
            return self._make_request("GET", "marketplace/v3/hardware")
        except Exception as e:
            # Handle error gracefully if endpoint not available
            if self.debug:
                print(f"Error getting hardware options: {str(e)}")
            # Return empty result
            return {"cpu": [], "memory": [], "storage": []}
    
    def get_basic_configurations(self) -> List[str]:
        """
        Get available basic configurations.
        
        This method is called by the VM commands but the endpoint doesn't exist.
        Instead of making an API call, return a list of standard configurations.
        
        Returns:
            List of configuration strings
        """
        # Return standard configurations instead of making an API call
        # This bypasses the 404 error
        return [
            "cpu-1-ram-1gb-storage-25gb",
            "cpu-1-ram-2gb-storage-25gb",
            "cpu-2-ram-2gb-storage-25gb",
            "cpu-2-ram-4gb-storage-25gb",
            "cpu-4-ram-8gb-storage-25gb"
        ]

    def wait_for_vm_status(self, vm_id: str, status: str, timeout: int = 300, 
                         check_interval: int = 5, callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Wait for a VM to reach a specific status.
        
        Args:
            vm_id: VM ID
            status: Status to wait for
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
                vm_data = self.get_vm(vm_id)
                current_status = vm_data.get("status", "").lower()
                
                # If callback is provided, call it with VM data and elapsed time
                if callback:
                    callback(vm_data, elapsed)
                
                # Check if VM has reached the desired status
                if current_status.lower() == status.lower():
                    return vm_data
            except Exception as e:
                if self.debug:
                    print(f"Error checking VM status: {e}")
            
            # Wait for next check
            time.sleep(check_interval)
            elapsed = time.time() - start_time
        
        raise TimeoutError(f"Timeout waiting for VM {vm_id} to reach status '{status}'")
