"""Tag command - Manage note tags."""
import argparse
from typing import Any, Dict

from noteman.commands.base import Command, register_command
from noteman.core.errors import ExitCode
from noteman.storage.store import NoteStore


@register_command
class TagCommand(Command):
    """Manage note tags."""

    name = "tag"
    description = "Manage note tags"
    help = """Manage tags for notes.

Subcommands:
  add     Add one or more tags to a note
  remove  Remove one or more tags from a note
  list    List all tags and their usage count

Examples:
  noteman tag add <note_id> work urgent
  noteman tag remove <note_id> old
  noteman tag list
  noteman tag list --count
"""
    aliases = ["tags"]

    def register_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Register arguments for the tag command."""
        subparsers = parser.add_subparsers(
            dest="tag_action",
            title="subcommands",
        )

        add_parser = subparsers.add_parser(
            "add",
            help="Add tags to a note",
            description="Add one or more tags to a note",
        )
        add_parser.add_argument("note_id", help="Note ID")
        add_parser.add_argument("tags", nargs="+", help="Tags to add")

        remove_parser = subparsers.add_parser(
            "remove",
            help="Remove tags from a note",
            description="Remove one or more tags from a note",
        )
        remove_parser.add_argument("note_id", help="Note ID")
        remove_parser.add_argument("tags", nargs="+", help="Tags to remove")

        list_parser = subparsers.add_parser(
            "list",
            help="List all tags",
            description="List all tags across all notes",
        )
        list_parser.add_argument(
            "-c",
            "--count",
            action="store_true",
            help="Show usage count for each tag",
        )

    def _list_tags(self, config: Dict[str, Any], store: NoteStore, show_count: bool) -> int:
        """List all tags with optional usage count."""
        all_tags = store.all_tags()

        if not all_tags:
            print("No tags found.")
            return ExitCode.SUCCESS

        print(f"Found {len(all_tags)} tags:")
        print()

        if show_count:
            notes = store.list()
            tag_counts = {}
            for note in notes:
                for tag in note.tags:
                    tag_counts[tag] = tag_counts.get(tag, 0) + 1

            for tag in all_tags:
                count = tag_counts.get(tag, 0)
                print(f"  {tag:<20} ({count} notes)")
        else:
            for tag in all_tags:
                print(f"  {tag}")

        return ExitCode.SUCCESS

    def execute(
        self,
        args: argparse.Namespace,
        config: Dict[str, Any],
        store: NoteStore,
    ) -> int:
        """Execute the tag command."""
        action = getattr(args, "tag_action", None)

        if not action:
            print("Error: Please specify a subcommand (add, remove, list)", file=__import__("sys").stderr)
            return ExitCode.USAGE_ERROR

        if action == "list":
            return self._list_tags(config, store, args.count)

        if action == "add":
            note = store.get(args.note_id)
            for tag in args.tags:
                note = store.add_tag(args.note_id, tag)
            print(f"Tags added to note {args.note_id}: {', '.join(args.tags)}")
            print(f"Current tags: {', '.join(note.tags)}")
            return ExitCode.SUCCESS

        if action == "remove":
            note = store.get(args.note_id)
            for tag in args.tags:
                note = store.remove_tag(args.note_id, tag)
            print(f"Tags removed from note {args.note_id}: {', '.join(args.tags)}")
            print(f"Current tags: {', '.join(note.tags) if note.tags else '(none)'}")
            return ExitCode.SUCCESS

        print(f"Unknown action: {action}", file=__import__("sys").stderr)
        return ExitCode.USAGE_ERROR
