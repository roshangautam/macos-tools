# macOS Tools

A collection of useful command-line tools for macOS. This project uses [Click](https://click.palletsprojects.com/) to create a CLI with various utilities for common macOS tasks.

## Installation

Clone the repository and install:

```bash
git clone <repository-url>
cd macos-tools
pip install -e .
```

## Available Commands

- `system-info`: Display system information
- `cleanup-temp`: Clean up temporary files (simulation only, add --force to actually perform)

## Usage

```bash
# Get system information
macos-tools system-info

# Clean up temporary files (simulation)
macos-tools cleanup-temp
```

## Adding New Tools

To add a new tool, edit the `macos_tools/cli.py` file and add a new command following the existing pattern:

```python
@cli.command()
def your_new_command():
    """Description of your command."""
    # Your implementation here
    click.echo("Command output")
```

## Requirements

- Python 3.6+
- Click package
- macOS operating system

