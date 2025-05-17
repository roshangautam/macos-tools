from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="macos-tools",
    version="0.1.1",
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    include_package_data=True,
    install_requires=[
        "click>=8.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "flake8>=4.0.0",
            "black>=21.0",
            "isort>=5.0.0",
            "mypy>=0.910",
        ],
    },
    entry_points={
        "console_scripts": [
            "macos-tools=src.cli:cli",
        ],
    },
    author="Roshan Gautam",
    author_email="your.email@example.com",
    description="A collection of common tools for macOS",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="macos, tools, utilities",
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
    url="https://github.com/roshangautam/macos-tools",
    project_urls={
        "Bug Reports": "https://github.com/roshangautam/macos-tools/issues",
        "Source": "https://github.com/roshangautam/macos-tools",
    },
)

