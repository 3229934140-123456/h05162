"""Add command - Create a new note."""
import argparse
import subprocess
import sys
import tempfile
import os
from typing import Any, Dict

from noteman.commands.base import Command, register_command
from noteman.core.errors import ExitCode
from noteman.storage.store import NoteStore


@register_command
class AddCommand(Command):
    """Add a new note."""

    name = "add"
    description = "Add a new note"
    help = """Add a new note.

Examples:
  noteman add "My Note Title"
  noteman add "Meeting Notes" -t work -t meeting
  noteman add --editor "My Note Title"
  noteman add -f note.md "Imported Note"
"""
    aliases = ["new", "create"]

    def register_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Register arguments for the add command."""
        parser.add_argument(
            "title",
            nargs="?",
            help="Note title (required unless using --file)",
        )
        parser.add_argument(
            "-t",
            "--tag",
            action="append",
            default=[],
            help="Add a tag (can be used multiple times)",
        )
        parser.add_argument(
            "-c",
            "--content",
            default=None,
            help="Note content (if not specified, opens editor)",
        )
        parser.add_argument(
            "-e",
            "--editor",
            action="store_true",
            help="Open editor to write content",
        )
        parser.add_argument(
            "-f",
            "--file",
            help="Read content from file",
        )

    def _read_from_editor(self, config: Dict[str, Any]) -> str:
        """Open editor and read content.

        Args:
            config: Configuration dictionary.

        Returns:
            Content string from editor.
        """
        editor = config.get("editor", "vim")

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".md", delete=False, encoding="utf-8"
        ) as f:
            f.write("# Write your note content here\n")
            temp_path = f.name

        try:
            subprocess.run([editor, temp_path], check=True)
            with open(temp_path, "r", encoding="utf-8") as f:
                content = f.read()
            return content.strip()
        finally:
            try:
                os.unlink(temp_path)
            except Exception:
                pass

    def _read_from_file(self, filepath: str) -> str:
        """Read content from a file.

        Args:
            filepath: Path to the file.

        Returns:
            Content string.
        """
        path = os.path.expanduser(filepath)
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()

    def execute(
        self,
        args: argparse.Namespace,
        config: Dict[str, Any],
        store: NoteStore,
    ) -> int:
        """Execute the add command."""
        title = args.title

        if title is None and not args.file:
            print("Error: Title is required unless using --file", file=sys.stderr)
            return ExitCode.USAGE_ERROR

        if args.file:
            content = self._read_from_file(args.file)
            if not title:
                title = os.path.basename(args.file).rsplit(".", 1)[0]
        elif args.content is not None:
            content = args.content
        elif args.editor:
            content = self._read_from_editor(config)
        else:
            content = self._read_from_editor(config)

        note = store.create(title=title, content=content, tags=args.tag)
        note = store.save(note)

        date_format = config["display"]["date_format"]
        created_str = self.format_date(note.created_at, date_format)

        print(f"Note created:")
        print(f"  ID:     {note.id}")
        print(f"  Title:  {note.title}")
        print(f"  Created: {created_str}")
        if note.tags:
            print(f"  Tags:   {', '.join(note.tags)}")

        return ExitCode.SUCCESS
