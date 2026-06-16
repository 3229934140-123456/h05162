"""Init command - Initialize the notes directory."""
import argparse
import os
from pathlib import Path
from typing import Any, Dict

from noteman.commands.base import Command, register_command
from noteman.core.errors import ExitCode
from noteman.storage.store import NoteStore


@register_command
class InitCommand(Command):
    """Initialize the notes directory."""

    name = "init"
    description = "Initialize the notes directory"
    help = """Initialize the notes data directory.

This creates the data directory and initializes an empty notes database.
The directory defaults to ~/.noteman/data but can be overridden with
--data-dir global option or via configuration.

Examples:
  noteman init
  noteman --data-dir ./my_notes init
"""
    aliases = []

    def register_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Register arguments for the init command."""
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="Reinitialize even if directory already exists",
        )

    def execute(
        self,
        args: argparse.Namespace,
        config: Dict[str, Any],
        store: NoteStore,
    ) -> int:
        """Execute the init command."""
        data_dir = Path(config["data_dir"])
        notes_file = data_dir / "notes.json"

        if notes_file.exists() and not args.force:
            print(f"Notes directory already initialized at: {data_dir}")
            print("Use --force to reinitialize (this will delete all existing notes)")
            return ExitCode.SUCCESS

        if notes_file.exists() and args.force:
            try:
                notes_file.unlink()
            except OSError as e:
                print(f"Error deleting existing notes: {e}", file=__import__("sys").stderr)
                return ExitCode.IO_ERROR

        if not notes_file.exists():
            import json

            try:
                notes_file.parent.mkdir(parents=True, exist_ok=True)
                initial_data = {"notes": [], "version": 1, "created_at": __import__("time").time()}
                with open(notes_file, "w", encoding="utf-8") as f:
                    json.dump(initial_data, f, indent=2, ensure_ascii=False)
            except OSError as e:
                print(f"Error initializing notes file: {e}", file=__import__("sys").stderr)
                return ExitCode.IO_ERROR

        print(f"Initialized notes directory at: {data_dir}")
        print(f"Config file: {config.get('config_file', '(none)')}")
        print(f"Editor: {config.get('editor', 'vim')}")

        return ExitCode.SUCCESS
