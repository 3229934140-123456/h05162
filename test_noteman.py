#!/usr/bin/env python
"""Test script for noteman."""
import os
import sys
import tempfile
import shutil
from pathlib import Path

# Add the project directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

os.environ["NOTEMAN_DATA_DIR"] = str(Path(__file__).parent / "test_data")
if os.path.exists(os.environ["NOTEMAN_DATA_DIR"]):
    shutil.rmtree(os.environ["NOTEMAN_DATA_DIR"])

from noteman.core.dispatcher import main

def test_command(args, description):
    """Run a command and print results."""
    print(f"\n{'='*60}")
    print(f"TEST: {description}")
    print(f"Command: noteman {' '.join(args)}")
    print(f"{'-'*60}")
    try:
        result = main(args)
        print(f"\nExit code: {result}")
    except SystemExit as e:
        print(f"\nExit code: {e.code}")
    print()

if __name__ == "__main__":
    print("=" * 60)
    print("Testing Noteman CLI Framework")
    print("=" * 60)
    print(f"Data directory: {os.environ['NOTEMAN_DATA_DIR']}")

    test_command(["--version"], "Show version")
    test_command(["--help"], "Show help")
    test_command(["init"], "Initialize notes directory")
    test_command(["config", "show"], "Show configuration")
    test_command(["config", "get", "--all"], "Get all config keys")
    test_command(["config", "get", "data_dir"], "Get data_dir config")
    test_command(["config", "get", "display.color"], "Get display.color config")

    test_command(["add", "-t", "work", "-t", "python", "-c", "Python is a great programming language.", "Python Learning Notes"], "Add note with content")
    test_command(["add", "-t", "personal", "-c", "Remember to buy milk and bread.", "Shopping List"], "Add second note")
    test_command(["add", "-t", "work", "-t", "meeting", "-c", "Discuss project timeline and milestones.", "Project Meeting"], "Add third note")

    test_command(["list"], "List all notes")
    test_command(["list", "-t", "work"], "List notes with tag 'work'")
    test_command(["list", "--sort", "title", "--reverse"], "List notes sorted by title (ascending)")
    test_command(["list", "-n", "2"], "List only 2 notes")

    test_command(["tag", "list", "--count"], "List all tags with counts")

    test_command(["search", "python"], "Search for 'python'")
    test_command(["search", "milk"], "Search for 'milk'")
    test_command(["search", "--no-content", "work"], "Search for 'work' in title only")

    test_command(["list"], "List notes to get an ID")

    print("\n" + "=" * 60)
    print("Testing complete!")
    print("=" * 60)
