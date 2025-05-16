from setuptools import setup, find_packages

setup(
    name="macos-tools",
    version="0.1.0",
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        "click",
    ],
    entry_points={
        "console_scripts": [
            "macos-tools=macos_tools.cli:cli",
        ],
    },
    author="Roshan Gautam",
    author_email="your.email@example.com",
    description="A collection of common tools for macOS",
    keywords="macos, tools, utilities",
    python_requires=">=3.6",
)

