# macOS Tools

A collection of useful command-line utilities for macOS system management and maintenance. This toolkit provides various commands to help with everyday macOS tasks, system information monitoring, and maintenance operations.

![GitHub license](https://img.shields.io/github/license/roshangautam/macos-tools)
![Python Version](https://img.shields.io/badge/python-3.6%2B-blue)
![Platform](https://img.shields.io/badge/platform-macOS-lightgrey)

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

## Prerequisites

- macOS operating system
- Python 3.6 or higher
- pip (Python package manager)

## Installation

### From GitHub

```bash
# Clone the repository
git clone https://github.com/roshangautam/macos-tools.git
cd macos-tools

# Install the package
pip install -e .
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

1. Add your command function to `macos_tools/cli.py` following the Click command pattern
2. Update the documentation and README with usage instructions
3. Add tests for your new command

## License

MIT License - See the [LICENSE](LICENSE) file for details.

