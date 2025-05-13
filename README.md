# Fluence CLI

A command-line tool for managing Fluence VMs. This CLI provides a convenient interface to the Fluence API, allowing you to create, manage, and monitor virtual machines in the Fluence network.

## API Documentation

This CLI interacts with the Fluence API:
- API Swagger UI: https://api.fluence.dev/swagger-ui/ 
- Official Documentation: https://fluence.dev/docs/build/api/overview

Refer to the official documentation for detailed information about API endpoints, parameters, and responses.

## Using from the GitHub Repository

```bash
# Clone the repository
git clone https://github.com/your-org/fluence-cli.git
cd fluence-cli

# Set up environment
cp env.example .env
# Edit .env with your credentials
nano .env

# Install dependencies with uv
uv pip install -e .

# Run the CLI
flu-cli --help
```

## Configuration

The CLI requires configuration before use. Follow these steps to set up your environment:

1. Create a `.env` file with your API key and SSH key:

```bash
# Create from template
cp env.example .env

# Edit with your credentials
nano .env
```

2. Add the following to your `.env` file:

```
FLUENCE_API_KEY=<your api key from console>

# SSH key for VM access
SSH_PUBLIC_KEY="<your PUBLIC ssh key string">

# Optional API URL override
FLUENCE_API_URL=https://api.fluence.dev
```

3. Optionally create a configuration file for VM creation:

```bash
# Create a sample config.toml file
nano config.toml
```

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
# List all VMs
flu-cli vm list

# Get details for a specific VM
flu-cli vm get <vm_id>

# Create a new VM
flu-cli vm create [name] --cpu 2 --memory 4 [--wait]

# Create a VM with custom configuration
flu-cli vm create --config config.toml

# Estimate VM cost without creating
flu-cli vm estimate --cpu 2 --memory 4

# Delete a VM
flu-cli vm delete <vm_id>

# Scale VM resources
flu-cli vm scale <vm_id> --cpu 4 --memory 8
```

### Marketplace Commands

```bash
# List available countries
flu-cli market countries

# Get pricing for a VM configuration
flu-cli market pricing --cpu 2 --memory 4 [--region US]

# List available hardware options
flu-cli market hardware
```

### Configuration Commands

```bash
# Show current configuration
flu-cli config show

# Initialize default configuration
flu-cli config init
```

## Using Format Options

You can use global format options with any command:

```bash
# JSON output for scripting
flu-cli --format json vm list

# Compact output for quick viewing
flu-cli -f compact vm list

# Debug mode with JSON output
flu-cli --debug --format json vm create test-vm --cpu 2 --memory 4
```

## Using Configuration Files for VM Creation

For more complex VM configurations, you can create a TOML configuration file:

```toml
# Fluence VM Configuration

[constraints]
basicConfiguration = "cpu-2-ram-4gb-storage-25gb"

[constraints.datacenter]
countries = ["US"]

[[constraints.hardware.cpu]]
manufacturer = "AMD"
architecture = "ZEN"

instances = 1

[vmConfiguration]
name = "fluence-vm"
osImage = "<your image url>"            # <- update
sshKeys = ["your public ssh key"]       # <- update

[[vmConfiguration.openPorts]]
# opened by default
port = 22
protocol = "tcp"

# optional
[[vmConfiguration.openPorts]]
port = 80
protocol = "tcp"
```

Then create the VM with:

```bash
flu-cli vm create --config config.toml
```

## Running the Smoke Test

The CLI includes a comprehensive smoke test that verifies all functionality by creating a test VM, running various commands, and cleaning up resources.

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

```
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

The smoke test performs the following steps:
1. Creates a VM configuration file matching the API requirements
2. Creates a test VM using the configuration
3. Waits for the VM to be ready
4. Tests all CLI commands (list, get, market, etc.)
5. Cleans up resources unless `--no-cleanup` is specified

## Environment Variables

The CLI uses the following environment variables:

| Variable | Description |
|----------|-------------|
| `FLUENCE_API_KEY` | API key for authentication (required) |
| `SSH_PUBLIC_KEY` | SSH public key for VM access (required) |
| `FLUENCE_API_URL` | API URL (optional, defaults to `https://api.fluence.dev`) |
| `DOTENV_PATH` | Custom path to .env file (optional) |