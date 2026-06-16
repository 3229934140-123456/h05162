"""
"""Setup script for Noteman."""
from setuptools import setup, find_packages

setup(
    name="noteman",
    version="0.1.0",
    description="A Git-style note management CLI tool",
    author="Noteman Team",
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=[
        # PyYAML is optional for YAML config support
        "PyYAML>=6.0; extra == 'yaml'",
    ],
    extras_require={
        "yaml": ["PyYAML>=6.0"],
        "dev": [
            "pytest>=7.0",
            "pytest-cov>=4.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "noteman=noteman.core.dispatcher:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: End Users/Desktop",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Scheduling",
        "Topic :: Text Processing :: General",
    ],
)
