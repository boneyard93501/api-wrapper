# FVM CLI (Fluence VM CLI)

A command-line tool for managing Fluence VMs. FVM CLI provides a convenient interface to the Fluence API, allowing you to create, manage and monitor virtual machines in the Fluence network.

## API Documentation

This CLI interacts with the Fluence API v3:
- API Swagger UI: https://api.fluence.dev/swagger-ui/ 
- Official Documentation: https://fluence.dev/docs/build/api/overview

## Using from the GitHub Repository

```bash
# Clone the repository
git clone git@github.com:boneyard93501/api-wrapper.git
cd fluence-cli

# Set up environment
cp env.example .env
# Edit .env with your credentials
nano .env

# Install dependencies with uv
uv pip install -e .

# Run the CLI
fvm-cli --help
```

## Configuration

The CLI uses two configuration files:

### 1. Environment File (.env) - For Secrets Only

Create a `.env` file with your API key, which you need to create on the console, and SSH key:

```bash
# Copy the template
cp .env.example .env

# Edit with your credentials
nano .env
```

Your `.env` file should contain ONLY secrets:
```
# API Key from https://console.fluence.network/settings/api-keys
FLUENCE_API_KEY=your_api_key_here

# SSH Public Key
SSH_PUBLIC_KEY=ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI... user@example.com
```

### 2. Configuration File (config.yaml) - For Settings

Create/edit a `config.yaml` file for all other settings:

```bash
# Create default config
fvm-cli config init

# Edit as needed
nano config.yaml
```

The `config.yaml` contains all non-secret configuration:
```yaml
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

# Hardware Preferences
hardware:
  cpu_manufacturer: AMD
  cpu_architecture: Zen

# Network Configuration
network:
  open_ports:
    - port: 22
      protocol: tcp
    - port: 80
      protocol: tcp
```

The CLI looks for config.yaml in:
1. Current directory
2. `~/.config/fvm-cli/config.yaml`
3. `~/.fvm-cli/config.yaml`

You can also set `FVM_CONFIG_PATH` environment variable to specify a custom location.

## Global Options

All commands support the following global options:

- `--format, -f [table|json|compact]`: Output format (defaults to `table`)
  - `table`: Formatted output with rich formatting
  - `json`: Raw JSON output for scripts and automation
  - `compact`: Minimal output for quick viewing
- `--debug`: Show API requests and responses for troubleshooting

## Commands

### VM Commands

```bash
# List active VMs (default)
fvm-cli vm list

# List ALL VMs including terminated ones
fvm-cli vm list --all

# Show full VM IDs without truncation
fvm-cli vm list --full-id

# Filter by status
fvm-cli vm list --status terminated

# Get details for a specific VM
fvm-cli vm get <vm_id>

# List available OS images
fvm-cli vm images

# Create a new VM
fvm-cli vm create [name] --cpu 2 --memory 4 [--wait] [--image <slug>]

# Create a VM with custom configuration file
fvm-cli vm create --config config.toml

# Estimate VM cost without creating
fvm-cli vm estimate --cpu 2 --memory 4 [--region US]

# Update VM (name and/or ports)
fvm-cli vm update <vm_id> --name new-name --add-port 8080/tcp --remove-port 443/tcp

# Delete a VM
fvm-cli vm delete <vm_id> [--force]
```

Note: The API only supports updating VM name and open ports. CPU/memory scaling is not available.

### Marketplace Commands

```bash
# List available countries
fvm-cli market countries

# List available basic configurations
fvm-cli market configurations

# Get pricing for a VM configuration
fvm-cli market pricing --cpu 2 --memory 4 [--region US]

# List available hardware options
fvm-cli market hardware

# Search marketplace offers
fvm-cli market offers [--cpu 2] [--memory 4] [--region US] [--max-price 5.00]
```

### Configuration Commands

```bash
# Show current configuration
fvm-cli config show

# Initialize default configuration
fvm-cli config init

# Create .env template
fvm-cli config env
```

## Using Format Options

You can use global format options with any command:

```bash
# JSON output for scripting
fvm-cli --format json vm list

# Compact output for quick viewing
fvm-cli -f compact vm list

# Debug mode with JSON output
fvm-cli --debug --format json vm create test-vm --cpu 2 --memory 4
```

## Using Configuration Files for VM Creation

Create a JSON configuration file matching the API schema:

```json
{
  "constraints": {
    "basicConfiguration": "cpu-2-ram-4gb-storage-25gb",
    "datacenter": {
      "countries": ["US"]
    },
    "maxTotalPricePerEpochUsd": "5.00"
  },
  "instances": 1,
  "vmConfiguration": {
    "name": "my-fluence-vm",
    "hostname": "my-hostname",
    "osImage": "https://cloud-images.ubuntu.com/releases/22.04/release/ubuntu-22.04-server-cloudimg-amd64.img",
    "sshKeys": ["ssh-ed25519 AAAAC3NzaC1... user@example.com"],
    "openPorts": [
      {"port": 22, "protocol": "tcp"},
      {"port": 80, "protocol": "tcp"},
      {"port": 443, "protocol": "tcp"}
    ]
  }
}
```

Then create the VM with:

```bash
fvm-cli vm create --config config.json
```

## OS Image Selection

Use the `vm images` command to see available OS images:

```bash
# List available images
fvm-cli vm images

# Create VM with specific image
fvm-cli vm create --image ubuntu-22-04-x64

# Create VM with custom image URL
fvm-cli vm create --image https://example.com/custom-image.qcow2
```

## VM Status Values

The Fluence API uses the following VM status values:
- `Launching` - VM is being created
- `Active` - VM is running and accessible
- `SmallBalance` - Low account balance warning
- `InsufficientFunds` - Account has insufficient funds
- `Terminated` - VM has been terminated
- `Stopped` - VM is stopped

## Running the Smoke Test

The CLI includes a comprehensive smoke test that verifies all functionality:

```bash
# Run with default settings
uv run tests/smoke_test.py

# Run with debug mode to see API requests
uv run tests/smoke_test.py --debug

# Specify custom resources
uv run tests/smoke_test.py --cpu 4 --memory 8 --country US

# Set a maximum price per day
uv run tests/smoke_test.py --max-price 3.50

# Skip cleanup to leave the VM running
uv run tests/smoke_test.py --no-cleanup
```

Available smoke test options:

```text
--cpu CPU               Number of CPU cores (default: 2)
--memory MEMORY         Memory in GB (default: 4)
--storage STORAGE       Storage in GB (default: 25)
--country COUNTRY       Country code for datacenter location (e.g., US, DE, BE)
--max-price MAX_PRICE   Maximum price per day in USD
--wait                  Wait for VM to be ready (default: True)
--timeout TIMEOUT       Maximum time to wait in seconds (default: 300)
--poll-interval POLL    Time between polls in seconds (default: 10)
--no-cleanup            Don't clean up resources after test
--env-file ENV_FILE     Path to specific .env file
--debug                 Enable debug output
```

## Environment Variables

The CLI uses the following environment variables for secrets only:

| Variable | Description | Required |
|----------|-------------|----------|
| `FLUENCE_API_KEY` | API key for authentication | Yes |
| `SSH_PUBLIC_KEY` | SSH public key for VM access | Yes |
| `FVM_CONFIG_PATH` | Custom path to config.yaml | No |
| `DOTENV_PATH` | Custom path to .env file | No |

## Error Handling

The CLI provides detailed error messages for common issues:
- `401 Unauthorized`: Check your API key
- `403 Forbidden`: Your API key lacks required permissions
- `404 Not Found`: Resource doesn't exist
- `422 Unprocessable Entity`: Invalid request data
- `500 Internal Server Error`: Server-side issue

Use `--debug` flag to see full API requests and responses for troubleshooting.
