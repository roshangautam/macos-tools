#!/usr/bin/env python3
import os
import subprocess
from pathlib import Path


def main():
    project_root = Path(__file__).parent.parent
    python_files = list((project_root / "src").glob("**/*.py"))

    print(f"Formatting {len(python_files)} Python files...")

    # Run isort
    subprocess.run(["isort", *python_files], check=True)

    # Run black
    subprocess.run(["black", *python_files], check=True)

    # Verify with flake8
    print("Running flake8 for style verification...")
    subprocess.run(["flake8", *python_files], check=False)


if __name__ == "__main__":
    main()
