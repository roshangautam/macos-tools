import pytest
from click.testing import CliRunner

# Test that the CLI can be invoked without errors
def test_cli_basic():
    from src.cli import cli
    
    runner = CliRunner()
    result = runner.invoke(cli, ['--help'])
    assert result.exit_code == 0
    assert "Show this message and exit." in result.output
