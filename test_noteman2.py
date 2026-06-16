#!/usr/bin/env python
"""Complete test script for noteman."""
import os
import sys
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

test_data_dir = str(Path(__file__).parent / "test_data2")
os.environ["NOTEMAN_DATA_DIR"] = test_data_dir
if os.path.exists(test_data_dir):
    shutil.rmtree(test_data_dir)

from noteman.core.dispatcher import main
from noteman.core.errors import ExitCode


def test_command(args, description, expected_exit_code=ExitCode.SUCCESS):
    """Run a command and print results."""
    print(f"\n{'='*60}")
    print(f"TEST: {description}")
    print(f"Command: noteman {' '.join(args)}")
    print(f"{'-'*60}")
    result = None
    try:
        result = main(args)
        print(f"\nExit code: {result} (expected: {expected_exit_code})")
        if result == expected_exit_code:
            print("[PASS]")
        else:
            print(f"[FAIL] Unexpected exit code")
    except SystemExit as e:
        result = e.code
        print(f"\nExit code: {e.code} (expected: {expected_exit_code})")
        if e.code == expected_exit_code:
            print("[PASS]")
        else:
            print(f"[FAIL] Unexpected exit code")
    print()
    return result


if __name__ == "__main__":
    print("=" * 60)
    print("Complete Noteman CLI Framework Test")
    print("=" * 60)
    print(f"Data directory: {test_data_dir}")

    test_command(["init"], "Initialize notes directory")

    test_command(["config", "show"], "Show configuration")

    test_command(["add", "-t", "work", "-t", "python", "-c", "Python is great for scripting.", "Python Scripting"], "Add note 1")
    test_command(["add", "-t", "personal", "-c", "Call mom tomorrow.", "Reminders"], "Add note 2")
    test_command(["add", "-t", "work", "-c", "Review pull requests.", "Code Review"], "Add note 3")

    result = test_command(["list"], "List all notes to get IDs")

    print("\n" + "=" * 60)
    print("Testing show command")
    print("=" * 60)

    notes_file = Path(test_data_dir) / "notes.json"
    import json
    with open(notes_file) as f:
        data = json.load(f)
    note_ids = [n["id"] for n in data["notes"]]
    print(f"Note IDs found: {note_ids}")

    if note_ids:
        test_command(["show", note_ids[0]], f"Show note {note_ids[0]}")
        test_command(["show", "--no-content", note_ids[0]], f"Show note without content")
        test_command(["show", "--raw", note_ids[0]], f"Show note raw JSON")
        test_command(["show", "nonexistent"], "Show non-existent note", expected_exit_code=ExitCode.NOT_FOUND_ERROR)

    print("\n" + "=" * 60)
    print("Testing tag add/remove commands")
    print("=" * 60)

    if note_ids:
        test_command(["tag", "add", note_ids[0], "important", "urgent"], f"Add tags to note {note_ids[0]}")
        test_command(["show", note_ids[0]], "Verify tags added")
        test_command(["tag", "remove", note_ids[0], "urgent"], f"Remove tag from note {note_ids[0]}")
        test_command(["show", note_ids[0]], "Verify tag removed")
        test_command(["tag", "list", "--count"], "List all tags with counts")

    print("\n" + "=" * 60)
    print("Testing delete command")
    print("=" * 60)

    if len(note_ids) > 1:
        test_command(["delete", note_ids[1], "-f"], f"Force delete note {note_ids[1]}")
        test_command(["list"], "Verify note deleted")
        test_command(["delete", "nonexistent", "-f"], "Delete non-existent note", expected_exit_code=ExitCode.NOT_FOUND_ERROR)

    print("\n" + "=" * 60)
    print("Testing error handling")
    print("=" * 60)

    test_command([], "No command specified", expected_exit_code=ExitCode.USAGE_ERROR)
    test_command(["add", "-c", "test"], "Add note without title", expected_exit_code=ExitCode.USAGE_ERROR)
    test_command(["unknowncmd"], "Unknown command", expected_exit_code=ExitCode.USAGE_ERROR)
    test_command(["add", "", "-c", "test"], "Empty title", expected_exit_code=ExitCode.VALIDATION_ERROR)

    print("\n" + "=" * 60)
    print("Testing configuration priority")
    print("=" * 60)

    print("Testing config from command line:")
    test_command(["--no-color", "--editor", "nano", "config", "get", "editor"], "Override editor via CLI")
    test_command(["--no-color", "config", "get", "display.color"], "Override color via CLI")

    print("\n" + "=" * 60)
    print("Testing environment variable override")
    print("=" * 60)

    os.environ["NOTEMAN_EDITOR"] = "code"
    test_command(["config", "get", "editor"], "Override editor via env var")
    del os.environ["NOTEMAN_EDITOR"]

    print("\n" + "=" * 60)
    print("Testing search with various options")
    print("=" * 60)

    test_command(["search", "python"], "Search for python")
    test_command(["search", "--case-sensitive", "Python"], "Case-sensitive search")
    test_command(["search", "-t", "work", "review"], "Search with tag filter")

    print("\n" + "=" * 60)
    print("ALL TESTS COMPLETED")
    print("=" * 60)

    # Cleanup
    if os.path.exists(test_data_dir):
        shutil.rmtree(test_data_dir)
    print(f"Cleaned up test data directory: {test_data_dir}")
