"""Base command class for plugin-style command registration.

This module implements the Command base class that all subcommands must inherit
from, and the CommandRegistry that manages command registration and discovery.

Key design:
    - Each command declares its own arguments via `register_arguments`
    - Commands are auto-discovered and registered via `@register_command` decorator
    - New commands can be added without modifying the dispatcher core
    - Commands receive config, store, and parsed args in `execute`
"""
import argparse
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type

from noteman.storage.store import NoteStore


class CommandRegistry:
    """Registry for managing command plugins.

    This registry allows commands to be registered without modifying the
    dispatcher core. Commands use the @register_command decorator to
    register themselves automatically when their module is imported.

    Example:
        @register_command
        class AddCommand(Command):
            name = "add"
            ...
    """

    _commands: Dict[str, Type["Command"]] = {}

    @classmethod
    def register(cls, command_class: Type["Command"]) -> Type["Command"]:
        """Register a command class.

        Args:
            command_class: The Command subclass to register.

        Returns:
            The command class (for decorator chaining).

        Raises:
            ValueError: If command name is already registered.
        """
        if not hasattr(command_class, "name") or not command_class.name:
            raise ValueError(f"Command class {command_class} must define a 'name' attribute")

        name = command_class.name
        if name in cls._commands:
            raise ValueError(f"Command '{name}' is already registered")

        cls._commands[name] = command_class
        return command_class

    @classmethod
    def unregister(cls, name: str) -> None:
        """Unregister a command.

        Args:
            name: Name of the command to unregister.
        """
        if name in cls._commands:
            del cls._commands[name]

    @classmethod
    def get(cls, name: str) -> Optional[Type["Command"]]:
        """Get a command class by name.

        Args:
            name: Name of the command.

        Returns:
            The Command subclass or None if not found.
        """
        return cls._commands.get(name)

    @classmethod
    def get_all(cls) -> Dict[str, Type["Command"]]:
        """Get all registered commands.

        Returns:
            Dictionary mapping command names to command classes.
        """
        return dict(cls._commands)

    @classmethod
    def get_names(cls) -> List[str]:
        """Get sorted list of registered command names.

        Returns:
            Sorted list of command names.
        """
        return sorted(cls._commands.keys())


def register_command(cls: Type["Command"]) -> Type["Command"]:
    """Decorator to register a command class with the registry.

    Args:
        cls: The Command subclass to register.

    Returns:
        The command class.

    Example:
        @register_command
        class AddCommand(Command):
            name = "add"
            description = "Add a new note"
            ...
    """
    return CommandRegistry.register(cls)


class Command(ABC):
    """Abstract base class for all commands.

    Subclasses must implement:
        - name: Command name (used in CLI)
        - description: Short description for help
        - register_arguments(): Declare command-specific arguments
        - execute(): Run the command logic

    Example subclass:
        @register_command
        class ListCommand(Command):
            name = "list"
            description = "List all notes"

            def register_arguments(self, parser):
                parser.add_argument("--tag", help="Filter by tag")
                parser.add_argument("--limit", type=int, help="Limit results")

            def execute(self, args, config, store):
                notes = store.list(tag=args.tag, limit=args.limit)
                for note in notes:
                    print(note)
    """

    name: str = ""
    description: str = ""
    help: str = ""
    aliases: List[str] = []

    def register_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Register command-specific arguments.

        Override this method to add command-line arguments specific
        to this command. The parser is an argparse subparser.

        Args:
            parser: The argparse ArgumentParser for this subcommand.
        """
        pass

    @abstractmethod
    def execute(
        self,
        args: argparse.Namespace,
        config: Dict[str, Any],
        store: NoteStore,
    ) -> int:
        """Execute the command.

        Args:
            args: Parsed command-line arguments.
            config: Merged configuration dictionary.
            store: NoteStore instance for data access.

        Returns:
            Exit code (0 for success, non-zero for failure).
        """
        pass

    def format_date(self, timestamp: float, date_format: str) -> str:
        """Format a timestamp using the configured date format.

        Args:
            timestamp: Unix timestamp.
            date_format: Format string (strftime format).

        Returns:
            Formatted date string.
        """
        import datetime

        return datetime.datetime.fromtimestamp(timestamp).strftime(date_format)

    def print_note_list(
        self,
        notes: List[Any],
        config: Dict[str, Any],
        show_tags: bool = True,
    ) -> None:
        """Print a formatted list of notes.

        Args:
            notes: List of Note objects.
            config: Configuration dictionary.
            show_tags: Whether to show tags.
        """
        if not notes:
            print("No notes found.")
            return

        date_format = config["display"]["date_format"]
        use_color = config["display"]["color"]

        for note in notes:
            created_str = self.format_date(note.created_at, date_format)
            line = f"{note.id}  {created_str}  {note.title}"

            if show_tags and note.tags:
                tags_str = " ".join(f"[{t}]" for t in note.tags)
                line += f"  {tags_str}"

            print(line)
