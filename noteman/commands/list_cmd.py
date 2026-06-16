"""List command - List all notes."""
import argparse
from typing import Any, Dict

from noteman.commands.base import Command, register_command
from noteman.core.errors import ExitCode
from noteman.storage.store import NoteStore


@register_command
class ListCommand(Command):
    """List all notes."""

    name = "list"
    description = "List all notes"
    help = """List all notes with optional filtering and sorting.

Examples:
  noteman list
  noteman list -t work
  noteman list --sort title --limit 10
  noteman list --reverse
"""
    aliases = ["ls"]

    def register_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Register arguments for the list command."""
        parser.add_argument(
            "-t",
            "--tag",
            help="Filter notes by tag",
        )
        parser.add_argument(
            "-n",
            "--limit",
            type=int,
            help="Limit number of notes to display",
        )
        parser.add_argument(
            "-s",
            "--sort",
            choices=["created_at", "updated_at", "title", "id"],
            default="updated_at",
            help="Sort notes by field (default: updated_at)",
        )
        parser.add_argument(
            "-r",
            "--reverse",
            action="store_true",
            help="Reverse sort order (oldest first)",
        )
        parser.add_argument(
            "--no-tags",
            action="store_true",
            help="Don't show tags in output",
        )

    def execute(
        self,
        args: argparse.Namespace,
        config: Dict[str, Any],
        store: NoteStore,
    ) -> int:
        """Execute the list command."""
        notes = store.list(
            tag=args.tag,
            limit=args.limit,
            sort_by=args.sort,
            reverse=not args.reverse,
        )

        total = store.count()
        print(f"Showing {len(notes)} of {total} notes")
        if args.tag:
            print(f"Filtered by tag: {args.tag}")
        print()

        self.print_note_list(notes, config, show_tags=not args.no_tags)

        return ExitCode.SUCCESS
