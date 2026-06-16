"""Search command - Search notes by keyword."""
import argparse
from typing import Any, Dict

from noteman.commands.base import Command, register_command
from noteman.core.errors import ExitCode
from noteman.storage.store import NoteStore


@register_command
class SearchCommand(Command):
    """Search notes by keyword."""

    name = "search"
    description = "Search notes by keyword"
    help = """Search notes by keyword in title, content, and tags.

Examples:
  noteman search "python"
  noteman search --case-sensitive "Python"
  noteman search --no-content "tag:work"
  noteman search -t work "meeting"
"""
    aliases = ["find", "grep"]

    def register_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Register arguments for the search command."""
        parser.add_argument(
            "query",
            help="Search query",
        )
        parser.add_argument(
            "-t",
            "--tag",
            help="Filter results by tag",
        )
        parser.add_argument(
            "--case-sensitive",
            action="store_true",
            help="Case-sensitive search",
        )
        parser.add_argument(
            "--no-content",
            action="store_true",
            help="Don't search in content",
        )
        parser.add_argument(
            "--no-tags",
            action="store_true",
            help="Don't search in tags",
        )
        parser.add_argument(
            "-n",
            "--limit",
            type=int,
            help="Limit number of results",
        )

    def execute(
        self,
        args: argparse.Namespace,
        config: Dict[str, Any],
        store: NoteStore,
    ) -> int:
        """Execute the search command."""
        results = store.search(
            query=args.query,
            case_sensitive=args.case_sensitive,
            include_content=not args.no_content,
            include_tags=not args.no_tags,
        )

        if args.tag:
            results = [n for n in results if args.tag in n.tags]

        if args.limit:
            results = results[: args.limit]

        print(f"Search results for: '{args.query}'")
        print(f"Found {len(results)} matching notes")
        print()

        self.print_note_list(results, config)

        return ExitCode.SUCCESS
