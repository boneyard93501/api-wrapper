"""
Configuration management for the Fluence CLI.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dotenv import load_dotenv


def find_config_file(filename: str) -> Optional[Path]:
    """
    Find a configuration file by looking in current directory and parent directories.
    
    Args:
        filename: Name of the file to find
        
    Returns:
        Path to the file if found, None otherwise
    """
    current_path = Path.cwd()
    
    # Try current directory and up to 3 parent directories
    for _ in range(4):
        file_path = current_path / filename
        if file_path.exists():
            return file_path
        
        # Move up one directory
        parent = current_path.parent
        if parent == current_path:  # Reached root directory
            break
        current_path = parent
    
    return None


def load_environment() -> None:
    """
    Load environment variables from .env file.
    This should be called at the start of the program.
    """
    # Check for custom .env path
    env_path = os.environ.get("DOTENV_PATH")
    if env_path and Path(env_path).exists():
        load_dotenv(env_path)
        return
    
    # Try to find .env file in current directory or parent directories
    env_path = find_config_file(".env")
    
    if env_path:
        load_dotenv(env_path)
    else:
        # Check if we're running in a CI/CD environment or config exists directly in env vars
        if not os.environ.get("FLUENCE_API_KEY"):
            print("No .env file found. Using existing environment variables.")


def load_yaml_config() -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Returns:
        Dict containing configuration values
        
    Raises:
        FileNotFoundError: If config.yaml is not found
        ValueError: If config.yaml is invalid
    """
    config_path = find_config_file("fluence.yaml")
    
    if not config_path:
        return get_default_config()
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        
        if not config:
            return get_default_config()
            
        return config
    except Exception as e:
        print(f"Error loading fluence.yaml: {str(e)}. Using default configuration.")
        return get_default_config()


def get_default_config() -> Dict[str, Any]:
    """Get default configuration."""
    return {
        "api": {
            "url": "https://api.fluence.dev"
        },
        "vm": {
            "cpu_count": 2,
            "memory_gb": 4,
            "storage_gb": 25,
            "region": "US",
            "name_prefix": "fluence-"
        },
        "hardware": {
            "cpu": {
                "manufacturer": "AMD",
                "architecture": "ZEN"
            }
        },
        "network": {
            "open_ports": [
                {"port": 22, "protocol": "tcp"},
                {"port": 80, "protocol": "tcp"},
                {"port": 443, "protocol": "tcp"}
            ]
        }
    }


def get_config() -> Dict[str, Any]:
    """
    Get configuration from environment variables and config file.
    
    Returns:
        Dict containing configuration values
    
    Raises:
        ValueError: If required configuration is missing
    """
    # Load YAML config
    yaml_config = load_yaml_config()
    
    # Start with environment variables for sensitive values
    config = {
        "FLUENCE_API_KEY": os.environ.get("FLUENCE_API_KEY"),
        "SSH_PUBLIC_KEY": os.environ.get("SSH_PUBLIC_KEY"),
    }
    
    # Check required environment variables
    if not config["FLUENCE_API_KEY"]:
        raise ValueError("FLUENCE_API_KEY is not set in environment variables")
    
    if not config["SSH_PUBLIC_KEY"]:
        raise ValueError("SSH_PUBLIC_KEY is not set in environment variables")
    
    # Add values from YAML config
    config["FLUENCE_API_URL"] = yaml_config.get("api", {}).get("url", "https://api.fluence.dev")
    
    # VM config
    vm_config = yaml_config.get("vm", {})
    config["VM_CPU_COUNT"] = vm_config.get("cpu_count", 2)
    config["VM_MEMORY_GB"] = vm_config.get("memory_gb", 4)
    config["VM_STORAGE_GB"] = vm_config.get("storage_gb", 25)
    config["VM_REGION"] = vm_config.get("region", "US")
    config["VM_NAME_PREFIX"] = vm_config.get("name_prefix", "fluence-")
    
    # Hardware config
    hardware_config = yaml_config.get("hardware", {})
    cpu_config = hardware_config.get("cpu", {})
    config["CPU_MANUFACTURER"] = cpu_config.get("manufacturer", "AMD")
    config["CPU_ARCHITECTURE"] = cpu_config.get("architecture", "ZEN")
    
    # Network config
    network_config = yaml_config.get("network", {})
    config["OPEN_PORTS"] = network_config.get("open_ports", [
        {"port": 22, "protocol": "tcp"},
        {"port": 80, "protocol": "tcp"},
        {"port": 443, "protocol": "tcp"}
    ])
    
    return config


def create_default_config() -> None:
    """
    Create a default configuration file in the current directory.
    """
    default_config = get_default_config()
    
    with open("fluence.yaml", 'w') as f:
        yaml.dump(default_config, f, default_flow_style=False)
    
    print("Created default configuration file: fluence.yaml")


def create_env_template() -> None:
    """
    Create a template .env file in the current directory.
    """
    env_content = """# Fluence API configuration
FLUENCE_API_KEY=your_api_key_here
SSH_PUBLIC_KEY=your_ssh_public_key_here

# Optional API URL override
# FLUENCE_API_URL=https://api.fluence.dev
"""
    
    with open(".env.example", 'w') as f:
        f.write(env_content)
    
    print("Created environment template file: .env.example")
    print("Copy this file to .env and update with your credentials.")