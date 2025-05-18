from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="macos-tools",
    version="0.1.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "click>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "macos-tools=cli:cli",
            "mt=cli:cli"
        ],
    },
    python_requires=">=3.9",
    author="Roshan Gautam",
    author_email="contact@roshangautam.com",
    description="A collection of common tools for macOS",
    long_description=long_description,
    long_description_content_type="text/markdown",
    keywords="macos, tools, utilities",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Intended Audience :: System Administrators",
        "License :: OSI Approved :: MIT License",
        "Operating System :: MacOS",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Topic :: System :: Systems Administration",
        "Topic :: Utilities",
    ],
    url="https://github.com/roshangautam/macos-tools",
    project_urls={
        "Bug Reports": "https://github.com/roshangautam/macos-tools/issues",
        "Source": "https://github.com/roshangautam/macos-tools",
    },
)
