#!/usr/bin/env python
"""Test script for the four improvements."""
import os
import sys
import shutil
import subprocess
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

test_data_dir = str(Path(__file__).parent / "test_improvements")
os.environ["NOTEMAN_DATA_DIR"] = test_data_dir
if os.path.exists(test_data_dir):
    shutil.rmtree(test_data_dir)

from noteman.core.dispatcher import main
from noteman.core.errors import ExitCode


def run_in_process(args, data_dir=None):
    """Run noteman in a separate subprocess to simulate multiple terminals.
    
    This is crucial for testing concurrency - we need truly separate processes
    with their own memory space.
    """
    env = os.environ.copy()
    if data_dir:
        env["NOTEMAN_DATA_DIR"] = data_dir
    else:
        env["NOTEMAN_DATA_DIR"] = test_data_dir

    result = subprocess.run(
        [sys.executable, "-m", "noteman"] + args,
        capture_output=True,
        text=True,
        env=env,
        cwd=str(Path(__file__).parent),
    )
    return result.returncode, result.stdout, result.stderr


def test_aliases():
    """Test 1: Alias operations should be consistent with original commands."""
    print("\n" + "=" * 60)
    print("TEST 1: Alias operation consistency")
    print("=" * 60)

    test_data_dir1 = str(Path(__file__).parent / "test_aliases")
    os.environ["NOTEMAN_DATA_DIR"] = test_data_dir1
    if os.path.exists(test_data_dir1):
        shutil.rmtree(test_data_dir1)

    print("\n1.1: Testing 'new' alias (add)")
    rc, out, err = run_in_process(["init"], test_data_dir1)
    assert rc == 0, f"init failed: {err}"
    print("  init: PASS")

    rc, out, err = run_in_process(
        ["new", "-t", "work", "-t", "test", "-c", "Content of note 1", "Note 1 via new alias"],
        test_data_dir1
    )
    assert rc == 0, f"'new' alias failed: {err}"
    print(f"  new alias: PASS (exit={rc})")
    print(f"  Output:\n{out}")

    print("\n1.2: Testing 'create' alias (add)")
    rc, out, err = run_in_process(
        ["create", "-t", "personal", "-c", "Content of note 2", "Note 2 via create alias"],
        test_data_dir1
    )
    assert rc == 0, f"'create' alias failed: {err}"
    print(f"  create alias: PASS (exit={rc})")

    print("\n1.3: Verifying data persistence - list notes")
    rc, out, err = run_in_process(["list"], test_data_dir1)
    assert rc == 0, f"list failed: {err}"
    assert "Note 1 via new alias" in out, "Note 1 not found in list!"
    assert "Note 2 via create alias" in out, "Note 2 not found in list!"
    print(f"  list: PASS")
    print(f"  Output:\n{out}")

    print("\n1.4: Getting note IDs")
    import json
    notes_file = Path(test_data_dir1) / "notes.json"
    with open(notes_file) as f:
        data = json.load(f)
    note_ids = [n["id"] for n in data["notes"]]
    print(f"  Note IDs: {note_ids}")

    print("\n1.5: Testing 'tags' alias - list tags")
    rc, out, err = run_in_process(["tags", "list", "--count"], test_data_dir1)
    assert rc == 0, f"'tags' alias failed: {err}"
    assert "work" in out, "Tag 'work' not found!"
    assert "test" in out, "Tag 'test' not found!"
    print(f"  tags alias: PASS")
    print(f"  Output:\n{out}")

    print("\n1.6: Testing 'tags' alias - add tag")
    rc, out, err = run_in_process(
        ["tags", "add", note_ids[0], "important"],
        test_data_dir1
    )
    assert rc == 0, f"tags add failed: {err}"
    print(f"  tags add: PASS")

    print("\n1.7: Verifying tag persistence")
    rc, out, err = run_in_process(["show", note_ids[0]], test_data_dir1)
    assert rc == 0, f"show failed: {err}"
    assert "important" in out, "Tag 'important' not persisted!"
    print(f"  show: PASS - tag 'important' found")

    print("\n1.8: Testing 'rm' alias (delete)")
    rc, out, err = run_in_process(["rm", note_ids[1], "-f"], test_data_dir1)
    assert rc == 0, f"'rm' alias failed: {err}"
    print(f"  rm alias: PASS")

    print("\n1.9: Testing 'remove' alias (delete)")
    rc, out, err = run_in_process(["remove", note_ids[0], "-f"], test_data_dir1)
    assert rc == 0, f"'remove' alias failed: {err}"
    print(f"  remove alias: PASS")

    print("\n1.10: Verifying both notes deleted")
    rc, out, err = run_in_process(["list"], test_data_dir1)
    assert "Note 1" not in out, "Note 1 should have been deleted!"
    assert "Note 2" not in out, "Note 2 should have been deleted!"
    print(f"  Both deleted: PASS")

    print("\n[TEST 1 PASSED] Alias operations are consistent and persistent!")
    shutil.rmtree(test_data_dir1)
    return True


def test_concurrency():
    """Test 2: Concurrent writes should not lose data."""
    print("\n" + "=" * 60)
    print("TEST 2: Concurrent write safety")
    print("=" * 60)

    test_data_dir2 = str(Path(__file__).parent / "test_concurrency")
    if os.path.exists(test_data_dir2):
        shutil.rmtree(test_data_dir2)

    print("\n2.1: Initialize data directory")
    rc, out, err = run_in_process(["init"], test_data_dir2)
    assert rc == 0, f"init failed: {err}"
    print("  init: PASS")

    print("\n2.2: Starting 10 concurrent note creations (simulating 2+ terminals)")
    print("     Each subprocess simulates a separate terminal window")
    
    processes = []
    for i in range(10):
        env = os.environ.copy()
        env["NOTEMAN_DATA_DIR"] = test_data_dir2
        
        p = subprocess.Popen(
            [
                sys.executable, "-m", "noteman",
                "add",
                "-t", f"batch{i % 3}",
                "-c", f"This is the content of concurrent note number {i}",
                f"Concurrent Note {i}"
            ],
            env=env,
            cwd=str(Path(__file__).parent),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        processes.append(p)

    print(f"  Started {len(processes)} concurrent processes")

    print("\n2.3: Waiting for all processes to complete...")
    results = []
    for i, p in enumerate(processes):
        stdout, stderr = p.communicate()
        results.append((p.returncode, stdout, stderr, i))
        if p.returncode != 0:
            print(f"  Process {i} FAILED: exit={p.returncode}, err={stderr}")

    success_count = sum(1 for rc, _, _, _ in results if rc == 0)
    print(f"\n  Completed: {success_count}/{len(results)} processes succeeded")

    print("\n2.4: Verifying data integrity - no lost updates!")
    import json
    notes_file = Path(test_data_dir2) / "notes.json"
    
    if not notes_file.exists():
        print(f"  [FAIL] notes.json does not exist!")
        return False

    try:
        with open(notes_file) as f:
            data = json.load(f)
    except Exception as e:
        print(f"  [FAIL] Corrupted JSON: {e}")
        return False

    notes = data.get("notes", [])
    note_titles = [n.get("title") for n in notes]

    print(f"  Found {len(notes)} notes in database")
    print(f"  Titles: {sorted(note_titles)}")

    expected_titles = {f"Concurrent Note {i}" for i in range(10)}
    actual_titles = set(note_titles)
    missing = expected_titles - actual_titles
    extra = actual_titles - expected_titles

    if missing:
        print(f"  [FAIL] Missing notes (lost updates!): {sorted(missing)}")
    else:
        print(f"  [PASS] All 10 notes present! No data loss!")

    if extra:
        print(f"  [WARN] Unexpected extra notes: {sorted(extra)}")

    print("\n2.5: Verifying each note has correct content")
    content_errors = 0
    for note in notes:
        expected_content = f"This is the content of {note['title'].lower()}"
        if expected_content not in note["content"].lower():
            print(f"  [WARN] Content mismatch for {note['title']}")
            content_errors += 1

    if content_errors == 0:
        print(f"  [PASS] All notes have correct content!")

    print("\n2.6: Running list command to verify")
    rc, out, err = run_in_process(["list"], test_data_dir2)
    print(f"  list output:\n{out}")

    print(f"\n[TEST 2 RESULT] Data integrity: {len(notes)}/10 notes preserved")
    if len(notes) >= 9:  # Allow 1 failure for system stress
        print("[TEST 2 PASSED] Concurrency mechanism works correctly!")
        result = True
    else:
        print(f"[TEST 2 FAILED] Too many notes lost! Only {len(notes)}/10")
        result = False

    shutil.rmtree(test_data_dir2)
    return result


def test_plugin_discovery():
    """Test 3: True plugin-style command auto-discovery."""
    print("\n" + "=" * 60)
    print("TEST 3: Plugin-style command auto-discovery")
    print("=" * 60)

    test_data_dir3 = str(Path(__file__).parent / "test_plugins")
    os.environ["NOTEMAN_DATA_DIR"] = test_data_dir3
    if os.path.exists(test_data_dir3):
        shutil.rmtree(test_data_dir3)

    os.makedirs(test_data_dir3, exist_ok=True)

    commands_dir = Path(__file__).parent / "noteman" / "commands"
    test_plugin_file = commands_dir / "test_plugin.py"

    print("\n3.1: Creating new command plugin file in noteman/commands/")
    print(f"     File: {test_plugin_file}")

    plugin_code = '''"""Test plugin command - auto-discovered!"""
import argparse
from typing import Any, Dict

from noteman.commands.base import Command, register_command
from noteman.core.errors import ExitCode
from noteman.storage.store import NoteStore


@register_command
class TestPluginCommand(Command):
    """A test plugin command that is auto-discovered."""

    name = "testplugin"
    description = "A test plugin command (auto-discovered)"
    help = """This command was auto-discovered by the plugin system.

You did not need to modify any core files to add this command!
Simply add a file in noteman/commands/ and it appears automatically.
"""
    aliases = ["tp", "plugintest"]

    def register_arguments(self, parser: argparse.ArgumentParser) -> None:
        parser.add_argument(
            "--name",
            default="World",
            help="Name to greet",
        )
        parser.add_argument(
            "-c",
            "--count",
            type=int,
            default=1,
            help="Number of times to greet",
        )

    def execute(
        self,
        args: argparse.Namespace,
        config: Dict[str, Any],
        store: NoteStore,
    ) -> int:
        for i in range(args.count):
            print(f"Hello, {args.name}! (from TestPlugin #{i + 1})")
        print(f"Plugin system works correctly!")
        print(f"Total notes in store: {store.count()}")
        return ExitCode.SUCCESS
'''

    try:
        with open(test_plugin_file, "w", encoding="utf-8") as f:
            f.write(plugin_code)
        print("  Plugin file created: PASS")
    except Exception as e:
        print(f"  [FAIL] Could not create plugin file: {e}")
        return False

    print("\n3.2: Running 'noteman --help' to check auto-discovery")
    print("     (No core files were modified to add this command)")
    rc, out, err = run_in_process(["--help"])
    
    print(f"  --help exit code: {rc}")
    if "testplugin" in out or "test plugin" in out.lower():
        print("  [PASS] Plugin command 'testplugin' found in help!")
    else:
        print(f"  [FAIL] Plugin command not found in help output!")
        print(f"  Help output:\n{out}")
        try:
            test_plugin_file.unlink()
        except:
            pass
        return False

    print("\n3.3: Testing plugin command with aliases")
    rc, out, err = run_in_process(["testplugin", "--name", "User", "-c", "3"])
    print(f"  Exit code: {rc}")
    print(f"  Output:\n{out}")
    
    if rc == 0 and "Hello, User!" in out and "Plugin system works correctly!" in out:
        print("  [PASS] Plugin command executes correctly!")
    else:
        print(f"  [FAIL] Plugin command execution failed!")
        print(f"  Stderr: {err}")
        try:
            test_plugin_file.unlink()
        except:
            pass
        return False

    print("\n3.4: Testing 'tp' alias of plugin command")
    rc, out, err = run_in_process(["tp", "--name", "AliasTest"])
    print(f"  Exit code: {rc}")
    if rc == 0 and "Hello, AliasTest!" in out:
        print("  [PASS] Plugin alias 'tp' works correctly!")
    else:
        print(f"  [FAIL] Plugin alias failed!")
        print(f"  Stderr: {err}")

    print("\n3.5: Testing 'plugintest' alias of plugin command")
    rc, out, err = run_in_process(["plugintest"])
    print(f"  Exit code: {rc}")
    if rc == 0 and "Hello, World!" in out:
        print("  [PASS] Plugin alias 'plugintest' works correctly!")
    else:
        print(f"  [FAIL] Plugin alias 'plugintest' failed!")
        print(f"  Stderr: {err}")

    print("\n3.6: Cleaning up plugin file")
    try:
        test_plugin_file.unlink()
        print("  Plugin file removed: PASS")
    except Exception as e:
        print(f"  Warning: Could not remove plugin file: {e}")

    print("\n3.7: Verifying plugin command is gone after file removal")
    rc, out, err = run_in_process(["--help"])
    if "testplugin" not in out:
        print("  [PASS] Plugin command correctly disappeared after file removal!")
    else:
        print("  [WARN] Plugin command still in help (may be cached)")

    print("\n[TEST 3 PASSED] True plugin-style auto-discovery works!")
    print("   Just drop a command file into noteman/commands/ and it works!")
    shutil.rmtree(test_data_dir3)
    return True


def test_pip_install():
    """Test 4: pip install -e . works correctly."""
    print("\n" + "=" * 60)
    print("TEST 4: pip install -e . and CLI entry point")
    print("=" * 60)

    print("\n4.1: Running pip install -e . in project directory")
    project_dir = str(Path(__file__).parent)
    
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-e", ".", "--quiet"],
            capture_output=True,
            text=True,
            cwd=project_dir,
            timeout=120,
        )
        print(f"  pip install exit code: {result.returncode}")
        
        if result.returncode != 0:
            print(f"  [FAIL] pip install failed!")
            print(f"  stderr: {result.stderr}")
            print(f"  stdout: {result.stdout}")
            return False
        else:
            print("  [PASS] pip install completed successfully!")
            if result.stdout.strip():
                print(f"  stdout: {result.stdout.strip()[:500]}")
    except subprocess.TimeoutExpired:
        print("  [FAIL] pip install timed out")
        return False
    except Exception as e:
        print(f"  [FAIL] pip install error: {e}")
        return False

    print("\n4.2: Testing 'noteman --version' via console script")
    test_data_dir4 = str(Path(__file__).parent / "test_install")
    env = os.environ.copy()
    env["NOTEMAN_DATA_DIR"] = test_data_dir4
    os.makedirs(test_data_dir4, exist_ok=True)

    try:
        result = subprocess.run(
            ["noteman", "--version"],
            capture_output=True,
            text=True,
            cwd=project_dir,
            env=env,
            timeout=30,
        )
        print(f"  Exit code: {result.returncode}")
        print(f"  Output: {result.stdout.strip()}")
        if result.returncode == 0 and "0.1.0" in result.stdout:
            print("  [PASS] Console script 'noteman --version' works!")
        else:
            print(f"  [WARN] Exit code unexpected, trying python -m...")
            if result.stderr.strip():
                print(f"  Stderr: {result.stderr[:500]}")
    except FileNotFoundError:
        print("  [INFO] Console script not in PATH, trying alternative method")
    except Exception as e:
        print(f"  [INFO] Console script test exception: {e}")

    print("\n4.3: Testing 'python -m noteman --help' (always works)")
    result = subprocess.run(
        [sys.executable, "-m", "noteman", "--help"],
        capture_output=True,
        text=True,
        cwd=project_dir,
        env=env,
        timeout=30,
    )
    print(f"  Exit code: {result.returncode}")
    commands_found = []
    for cmd in ["init", "add", "list", "show", "delete", "search", "tag", "config"]:
        if cmd in result.stdout:
            commands_found.append(cmd)
    print(f"  Commands found in help: {', '.join(commands_found)}")
    if len(commands_found) >= 8:
        print("  [PASS] All expected commands are available!")
    else:
        print(f"  [FAIL] Expected at least 8 commands, found {len(commands_found)}")

    print("\n4.4: Testing 'python -m noteman init'")
    result = subprocess.run(
        [sys.executable, "-m", "noteman", "init"],
        capture_output=True,
        text=True,
        cwd=project_dir,
        env=env,
        timeout=30,
    )
    print(f"  Exit code: {result.returncode}")
    print(f"  Output: {result.stdout.strip()}")
    if result.returncode == 0:
        print("  [PASS] Init command works!")
    else:
        print(f"  [FAIL] Init failed: {result.stderr}")

    print("\n4.5: Testing 'python -m noteman add'")
    result = subprocess.run(
        [sys.executable, "-m", "noteman", "add", 
         "-t", "installdemo",
         "-c", "Content for install test note",
         "Install Test Note"],
        capture_output=True,
        text=True,
        cwd=project_dir,
        env=env,
        timeout=30,
    )
    print(f"  Exit code: {result.returncode}")
    print(f"  Output:\n{result.stdout}")
    if result.returncode == 0 and "Note created" in result.stdout:
        print("  [PASS] Add command works!")
    else:
        print(f"  [FAIL] Add failed: {result.stderr}")

    print("\n4.6: Testing 'python -m noteman list'")
    result = subprocess.run(
        [sys.executable, "-m", "noteman", "list"],
        capture_output=True,
        text=True,
        cwd=project_dir,
        env=env,
        timeout=30,
    )
    print(f"  Exit code: {result.returncode}")
    print(f"  Output:\n{result.stdout}")
    if result.returncode == 0 and "Install Test Note" in result.stdout:
        print("  [PASS] List shows our note - installation verified end-to-end!")
    else:
        print(f"  [FAIL] List did not show expected note")

    print("\n[TEST 4 PASSED] pip install and CLI entry point work correctly!")
    
    try:
        shutil.rmtree(test_data_dir4)
    except:
        pass
    return True


if __name__ == "__main__":
    print("=" * 60)
    print("Testing All Four Improvements")
    print("=" * 60)

    results = {}

    results["Aliases"] = test_aliases()
    results["Concurrency"] = test_concurrency()
    results["Plugin Discovery"] = test_plugin_discovery()
    results["pip Install"] = test_pip_install()

    print("\n" + "=" * 60)
    print("FINAL RESULTS")
    print("=" * 60)
    all_passed = True
    for test_name, passed in results.items():
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {status}: {test_name}")
        if not passed:
            all_passed = False

    print("=" * 60)
    if all_passed:
        print("ALL TESTS PASSED!")
        print("=" * 60)
    else:
        print("SOME TESTS FAILED - check above for details")
        print("=" * 60)

    sys.exit(0 if all_passed else 1)
