"""
Configuration management for the Fluence CLI.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv


def get_config_path() -> Path:
    """Get the path to the configuration file."""
    # Check for custom config path in environment
    if os.environ.get("FVM_CONFIG_PATH"):
        return Path(os.environ["FVM_CONFIG_PATH"])
    
    # Default locations to check
    locations = [
        Path.cwd() / "config.yaml",
        Path.cwd() / "config.yml",
        Path.home() / ".config" / "fvm-cli" / "config.yaml",
        Path.home() / ".fvm-cli" / "config.yaml",
    ]
    
    # Return first existing config file
    for location in locations:
        if location.exists():
            return location
    
    # Return default location if none exist
    return Path.cwd() / "config.yaml"


def load_config_file() -> Dict[str, Any]:
    """Load configuration from YAML file."""
    config_path = get_config_path()
    
    if not config_path.exists():
        raise FileNotFoundError(
            f"Configuration file not found. Please create {config_path} or run 'fvm-cli config init'"
        )
    
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f) or {}
        return config
    except Exception as e:
        raise Exception(f"Error loading config file {config_path}: {str(e)}")


def deep_merge(base: Dict[str, Any], updates: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries."""
    result = base.copy()
    
    for key, value in updates.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    
    return result


def load_environment():
    """Load environment variables from .env file."""
    # Try to find .env file
    env_path = os.environ.get("DOTENV_PATH")
    
    if env_path:
        load_dotenv(env_path)
    else:
        # Try common locations
        locations = [
            Path.cwd() / ".env",
            Path.home() / ".env",
        ]
        
        for location in locations:
            if location.exists():
                load_dotenv(location)
                break


def get_config() -> Dict[str, Any]:
    """
    Get the complete configuration by combining:
    1. YAML config file
    2. Environment variables (for secrets only)
    """
    # Load environment first
    load_environment()
    
    # Load config file
    config = load_config_file()
    
    # Add secrets from environment
    config["FLUENCE_API_KEY"] = os.environ.get("FLUENCE_API_KEY")
    config["SSH_PUBLIC_KEY"] = os.environ.get("SSH_PUBLIC_KEY")
    
    # Validate required secrets
    if not config.get("FLUENCE_API_KEY"):
        raise ValueError("FLUENCE_API_KEY environment variable is required")
    
    if not config.get("SSH_PUBLIC_KEY"):
        raise ValueError("SSH_PUBLIC_KEY environment variable is required")
    
    # Convert nested config to flat format for backward compatibility
    flat_config = {
        "FLUENCE_API_KEY": config["FLUENCE_API_KEY"],
        "SSH_PUBLIC_KEY": config["SSH_PUBLIC_KEY"],
        "FLUENCE_API_URL": config.get("api", {}).get("url", "https://api.fluence.dev"),
        "VM_CPU_COUNT": config.get("vm", {}).get("cpu_count", 2),
        "VM_MEMORY_GB": config.get("vm", {}).get("memory_gb", 4),
        "VM_STORAGE_GB": config.get("vm", {}).get("storage_gb", 25),
        "VM_REGION": config.get("vm", {}).get("region", "US"),
        "VM_NAME_PREFIX": config.get("vm", {}).get("name_prefix", "fvm-"),
        "VM_OS_IMAGE": config.get("vm", {}).get("os_image"),
        "CPU_MANUFACTURER": config.get("hardware", {}).get("cpu_manufacturer"),
        "CPU_ARCHITECTURE": config.get("hardware", {}).get("cpu_architecture"),
        "STORAGE_TYPE": config.get("hardware", {}).get("storage_type"),
        "OPEN_PORTS": config.get("network", {}).get("open_ports", []),
        "DEFAULT_TIMEOUT": config.get("cli", {}).get("default_timeout", 300),
        "POLL_INTERVAL": config.get("cli", {}).get("poll_interval", 10),
    }
    
    return flat_config


def create_default_config():
    """Create a default config.yaml file if it doesn't exist."""
    config_path = Path.cwd() / "config.yaml"
    
    if config_path.exists():
        print(f"Config file already exists at {config_path}")
        return
    
    # Read the default config from a template or create minimal one
    default_yaml = """# FVM CLI Configuration File
# This file contains default values for VM creation and API settings

# API Configuration
api:
  url: https://api.fluence.dev

# Default VM Configuration
vm:
  cpu_count: 2
  memory_gb: 4
  storage_gb: 25
  region: US
  name_prefix: fvm-
  
  # Default OS image (Ubuntu 22.04 LTS)
  os_image: https://cloud-images.ubuntu.com/releases/22.04/release/ubuntu-22.04-server-cloudimg-amd64.img

# Hardware Preferences
hardware:
  cpu_manufacturer: AMD
  cpu_architecture: Zen
  storage_type: SSD

# Network Configuration
network:
  open_ports:
    - port: 22
      protocol: tcp
    - port: 80
      protocol: tcp
    - port: 443
      protocol: tcp

# CLI Behavior
cli:
  default_timeout: 300  # seconds
  poll_interval: 10     # seconds
  output_format: table  # table, json, or compact
"""
    
    with open(config_path, 'w') as f:
        f.write(default_yaml)
    
    print(f"Created default config file at {config_path}")


def create_env_template():
    """Create a .env template file."""
    env_path = Path.cwd() / ".env.example"
    
    template = """# Fluence API Key
# Get your API key from: https://console.fluence.network/settings/api-keys
FLUENCE_API_KEY=your_api_key_here

# SSH Public Key for VM access (NO QUOTES!)
# Get it with: cat ~/.ssh/id_ed25519.pub or cat ~/.ssh/id_rsa.pub
SSH_PUBLIC_KEY=ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... user@example.com
"""
    
    with open(env_path, 'w') as f:
        f.write(template)
    
    print(f"Created .env template at {env_path}")
    print("Copy this to .env and add your actual credentials")