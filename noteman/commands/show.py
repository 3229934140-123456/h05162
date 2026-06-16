"""Show command - Display detailed note information."""
import argparse
import textwrap
from typing import Any, Dict

from noteman.commands.base import Command, register_command
from noteman.core.errors import ExitCode, NotFoundError
from noteman.storage.store import NoteStore


@register_command
class ShowCommand(Command):
    """Show detailed note information."""

    name = "show"
    description = "Show detailed note information"
    help = """Display full details of a note.

Examples:
  noteman show <note_id>
  noteman show --no-content <note_id>
"""
    aliases = ["view", "cat"]

    def register_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Register arguments for the show command."""
        parser.add_argument(
            "note_id",
            help="Note ID to display",
        )
        parser.add_argument(
            "--no-content",
            action="store_true",
            help="Don't show note content",
        )
        parser.add_argument(
            "--raw",
            action="store_true",
            help="Show raw JSON output",
        )

    def execute(
        self,
        args: argparse.Namespace,
        config: Dict[str, Any],
        store: NoteStore,
    ) -> int:
        """Execute the show command."""
        note = store.get(args.note_id)

        if args.raw:
            import json

            print(json.dumps(note.to_dict(), indent=2, ensure_ascii=False))
            return ExitCode.SUCCESS

        date_format = config["display"]["date_format"]
        created_str = self.format_date(note.created_at, date_format)
        updated_str = self.format_date(note.updated_at, date_format)

        print("=" * 60)
        print(f"ID:      {note.id}")
        print(f"Title:   {note.title}")
        print(f"Created: {created_str}")
        print(f"Updated: {updated_str}")
        if note.tags:
            print(f"Tags:    {', '.join(note.tags)}")
        print("=" * 60)

        if not args.no_content and note.content:
            print()
            print(textwrap.dedent(note.content))
            print()
            print("=" * 60)

        return ExitCode.SUCCESS
