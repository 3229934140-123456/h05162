"""Delete command - Delete a note."""
import argparse
from typing import Any, Dict

from noteman.commands.base import Command, register_command
from noteman.core.errors import ExitCode
from noteman.storage.store import NoteStore


@register_command
class DeleteCommand(Command):
    """Delete a note."""

    name = "delete"
    description = "Delete a note"
    help = """Delete a note.

Examples:
  noteman delete <note_id>
  noteman delete <note_id> --force
"""
    aliases = ["rm", "remove"]

    def register_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Register arguments for the delete command."""
        parser.add_argument(
            "note_id",
            help="Note ID to delete",
        )
        parser.add_argument(
            "-f",
            "--force",
            action="store_true",
            help="Skip confirmation prompt",
        )

    def execute(
        self,
        args: argparse.Namespace,
        config: Dict[str, Any],
        store: NoteStore,
    ) -> int:
        """Execute the delete command."""
        note = store.get(args.note_id)

        if not args.force:
            date_format = config["display"]["date_format"]
            created_str = self.format_date(note.created_at, date_format)

            print(f"Note to delete:")
            print(f"  ID:     {note.id}")
            print(f"  Title:  {note.title}")
            print(f"  Created: {created_str}")
            if note.tags:
                print(f"  Tags:   {', '.join(note.tags)}")

            response = input("\nAre you sure you want to delete this note? [y/N]: ")
            if response.lower() not in ("y", "yes"):
                print("Deletion cancelled.")
                return ExitCode.SUCCESS

        store.delete(args.note_id)
        print(f"Note deleted: {args.note_id}")

        return ExitCode.SUCCESS
