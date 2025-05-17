# macOS Tools

A collection of useful command-line utilities for macOS system management and maintenance. This toolkit provides various commands to help with everyday macOS tasks, system information monitoring, and maintenance operations.

![GitHub license](https://img.shields.io/github/license/roshangautam/macos-tools)
![Python Version](https://img.shields.io/badge/python-3.6%2B-blue)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey)

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
  - [System Information](#system-information)
  - [Cleanup Utilities](#cleanup-utilities)
  - [Port Management](#port-management)
  - [Homebrew Management](#homebrew-management)
  - [Xcode Cleanup](#xcode-cleanup)
  - [Network Tools](#network-tools)
- [Why macOS Tools?](#why-macos-tools)
- [Safety Features](#safety-features)
- [Contributing](#contributing)
- [License](#license)

## Features

- **System Information**: Get detailed information about your macOS system, including:
  - OS version
  - Processor details
  - Memory usage statistics
  
- **Cleanup Utilities**: Clean temporary files and caches:
  - User Library caches
  - System logs
  - Application caches
  - Temporary files
  - System temporary folders
  - With safety checks to prevent removing critical files
  
- **Port Management**: Manage network ports and associated processes:
  - List processes using specific ports
  - Kill processes on selected ports
  - Scan port ranges for availability
  - Built-in presets for common port groups (web, database, development)

- **Homebrew Management**: Maintain your Homebrew installation:
  - Update Homebrew and all formulae
  - Clean up old versions and cache files
  - Check for common problems with brew doctor
  - Calculate disk space used by Homebrew
  - List explicitly installed formulae
  
- **Xcode Cleanup**: Free up disk space by cleaning Xcode files:
  - Clean derived data directory
  - Manage archives (with option to keep latest)
  - Remove old device support files
  - Clean simulator data
  - All cleanup operations with dry-run option
  
- **Network Tools**: Manage network settings and diagnose issues:
  - Flush DNS cache
  - View network interface information
  - Show DNS configuration
  - Configure proxy settings

## Prerequisites

- macOS operating system
- Python 3.6 or higher
- pip (Python package manager)
- [Homebrew](https://brew.sh/) (for installation via Homebrew)

## Installation

### Option 1: Install via Homebrew (Recommended)

```bash
# Tap this repository
brew tap roshangautam/macos-tools https://github.com/roshangautam/macos-tools.git

# Install the package
brew install macos-tools
```

### Option 2: Install from source

1. Clone this repository:
   ```bash
   git clone https://github.com/roshangautam/macos-tools.git
   cd macos-tools
   ```

2. Install the package in development mode:
   ```bash
   python -m pip install -e .
   ```
   
   Or install it directly with pip:
   ```bash
   pip install git+https://github.com/roshangautam/macos-tools.git
   ```

### From PyPI (coming soon)

```bash
pip install macos-tools
```

## Usage

### System Information

Get detailed information about your macOS system:

```bash
# Display system information
macos-tools system-info
```

Example output:
```
System: Darwin
macOS Version: 12.6
Processor: arm64

Memory Information:
Pages free: 134.22 MB
Pages active: 1857.81 MB
Pages inactive: 1808.46 MB
...
```

### Cleanup Temporary Files

Clean up temporary files and caches to free up disk space:

```bash
# Default mode (simulation only - won't delete files)
macos-tools cleanup-temp

# Clean specific locations
macos-tools cleanup-temp --caches --logs

# Clean all supported locations
macos-tools cleanup-temp --all

# Actually perform the cleanup (use with caution)
macos-tools cleanup-temp --force

# Clean specific locations and actually delete files
macos-tools cleanup-temp --caches --tmp --force
```

#### Cleanup Options

| Option | Description |
|--------|-------------|
| `--force` | Actually perform cleanup (default is simulation) |
| `--caches` | Clean ~/Library/Caches |
| `--logs` | Clean ~/Library/Logs |
| `--app-caches` | Clean ~/Library/Application Support/Caches |
| `--tmp` | Clean /tmp directory |
| `--var-folders` | Clean /private/var/folders (use with caution) |
| `--all` | Clean all of the above locations |

### Port Management

Manage network ports and processes running on them:

```bash
# List processes using common web and development ports
macos-tools ports list

# List processes using specific port
macos-tools ports list --port 8080

# List processes on common web ports (80, 443, 3000, 8000, 8080, 8888)
macos-tools ports list --web

# List processes on database ports (3306, 5432, 27017, etc.)
macos-tools ports list --db

# Kill process on specific port (with confirmation)
macos-tools ports kill --port 8080

# Force kill process without confirmation
macos-tools ports kill --port 8080 --force --yes

# Scan common ports
macos-tools ports scan --common

# Scan specific port range
macos-tools ports scan --start 3000 --end 4000

# Show only open ports in JSON format
macos-tools ports scan --open-only --json
```

### Homebrew Management

Maintain your Homebrew installation with these commands:

```bash
# Update Homebrew and all formulae
macos-tools brew update

# Clean up old versions and cache files (simulation)
macos-tools brew cleanup

# Actually perform cleanup
macos-tools brew cleanup --dry-run

# Check for common problems
macos-tools brew doctor

# Show disk space used by Homebrew
macos-tools brew size

# List explicitly installed formulae
macos-tools brew leaves

# Show dependencies for explicit installs
macos-tools brew leaves --with-deps

# Output any command in JSON format
macos-tools brew leaves --json
```

### Xcode Cleanup

Free up gigabytes of disk space by cleaning Xcode files:

```bash
# Clean derived data (simulation)
macos-tools xcode cleanup derived-data --dry-run

# Actually clean derived data
macos-tools xcode cleanup derived-data

# Clean archives but keep latest version for each project
macos-tools xcode cleanup archives --keep-latest

# Clean device support files but keep latest for each iOS version
macos-tools xcode cleanup device-support --keep-latest

# Clean simulator data
macos-tools xcode cleanup simulators

# Clean everything (with dry run)
macos-tools xcode cleanup all --dry-run

# Clean everything but keep latest archives and device support
macos-tools xcode cleanup all --keep-latest --force
```

### Network Tools

Manage network settings and diagnose issues:

```bash
# Flush DNS cache
macos-tools network dns-flush

# Show network interface information
macos-tools network info

# Show only DNS information
macos-tools network info --dns

# Show only IP information for a specific interface
macos-tools network info --ip --interface en0

# Output in JSON format
macos-tools network info --json
```

## Why macOS Tools?

macOS accumulates temporary files, caches, and logs over time that can consume significant disk space. This toolkit provides a safe and efficient way to:

1. Monitor your system's health and performance
2. Clean unnecessary files to free up disk space
3. Automate routine maintenance tasks
4. Provide targeted cleanup for specific system areas

## Safety Features

- Simulation mode by default (no files deleted unless `--force` is used)
- Exclusion patterns for critical system files
- Progress bars to show cleanup progress
- Human-readable size formatting
- Detailed reporting of space savings

## Contributing

Contributions are welcome! Here's how you can contribute:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-new-feature`
3. Add your changes and commit: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin feature/my-new-feature`
5. Submit a pull request

### Development Setup

```bash
# Clone the repository
git clone https://github.com/roshangautam/macos-tools.git
cd macos-tools

# Create and activate a virtual environment
python -m venv venv
source venv/bin/activate

# Install development dependencies
pip install -e ".[dev]"
```

### Adding New Commands

To add a new command to the toolkit:

1. Add your command function to `src/cli.py` following the Click command pattern
2. Update the documentation and README with usage instructions
3. Add tests for your new command

## License

MIT License - See the [LICENSE](LICENSE) file for details.

