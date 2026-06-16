"""Command dispatcher that connects CLI, config, storage, and commands.

Architecture overview:

                ┌─────────────────────────────────────────────────┐
                │                  Main Entry                    │
                └───────────────────┬─────────────────────────────┘
                                    │
                ┌───────────────────▼─────────────────────────────┐
                │                  CLI Parser                     │
                │  (parse global options + subcommand options)    │
                └───────────────────┬─────────────────────────────┘
                                    │
                ┌───────────────────▼─────────────────────────────┐
                │                Config Loader                    │
                │  (merge defaults < file < env < cli args)       │
                └───────────────────┬─────────────────────────────┘
                                    │
                ┌───────────────────▼─────────────────────────────┐
                │                 Note Store                      │
                │  (thread-safe, file-based persistence)          │
                └───────────────────┬─────────────────────────────┘
                                    │
                ┌───────────────────▼─────────────────────────────┐
                │                Dispatcher                       │
                │  (routes to command, manages transaction)       │
                └───────────────────┬─────────────────────────────┘
                                    │
                ┌───────────────────▼─────────────────────────────┐
                │               Command Registry                  │
                │  (auto-discovered commands via decorator)       │
                └───────────────────┬─────────────────────────────┘
                                    │
                ┌───────────────────▼─────────────────────────────┐
                │              Command.execute()                  │
                │  (add, list, show, delete, search, tag...)      │
                └─────────────────────────────────────────────────┘

Error propagation flow:
    Storage errors -> Command layer -> Dispatcher -> Error handler
    All errors are converted to appropriate exit codes and messages.
"""
import sys
import argparse
from typing import Any, Dict, Optional

from noteman.core.errors import ExitCode, handle_error, UsageError, NotemanError
from noteman.config.loader import load_config
from noteman.storage.store import NoteStore
from noteman.cli.parser import CLIParser
from noteman.commands.base import Command, CommandRegistry


class Dispatcher:
    """Main dispatcher that coordinates all components.

    The dispatcher is responsible for:
        1. Parsing command line arguments
        2. Loading configuration with proper priority
        3. Initializing the storage layer
        4. Routing to the appropriate command
        5. Managing transactions for write operations
        6. Handling errors and returning exit codes

    Key feature: The dispatcher has no knowledge of specific commands.
    It relies entirely on the CommandRegistry, so new commands can be
    added without modifying this class.
    """

    def __init__(self):
        """Initialize the dispatcher."""
        self.parser = CLIParser()
        self.config: Optional[Dict[str, Any]] = None
        self.store: Optional[NoteStore] = None

    def _auto_import_commands(self) -> None:
        """Auto-import all command modules to trigger registration.

        This imports all modules in the commands package, which triggers
        the @register_command decorator to register each command class
        with the CommandRegistry.

        To add a new command:
            1. Create a new file in noteman/commands/
            2. Define a Command subclass with @register_command decorator
            3. Add the module name to _COMMAND_MODULES below

        No changes to the dispatcher are needed!
        """
        _COMMAND_MODULES = [
            "noteman.commands.add",
            "noteman.commands.list_cmd",
            "noteman.commands.show",
            "noteman.commands.delete",
            "noteman.commands.search",
            "noteman.commands.tag",
            "noteman.commands.init_cmd",
            "noteman.commands.config_cmd",
        ]

        import importlib

        for module_name in _COMMAND_MODULES:
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                print(f"Warning: Could not import command module {module_name}: {e}", file=sys.stderr)

    def _init(self, cli_args: Dict[str, Any]) -> None:
        """Initialize config and store.

        Args:
            cli_args: Parsed command line arguments as dictionary.
        """
        self._auto_import_commands()
        self.parser.load_commands()

        self.config = load_config(cli_args)

        self.store = NoteStore(
            data_dir=self.config["data_dir"],
            pretty_print=self.config["storage"]["pretty_print"],
        )

    def _is_write_command(self, command_name: Optional[str]) -> bool:
        """Determine if a command needs write access to storage.

        Args:
            command_name: Name of the command.

        Returns:
            True if the command needs write access, False otherwise.
        """
        write_commands = {"add", "delete", "tag", "init"}
        return command_name in write_commands

    def dispatch(self, argv: Optional[list] = None) -> int:
        """Dispatch a command based on command line arguments.

        This is the main entry point that:
            1. Parses arguments
            2. Initializes config and storage
            3. Routes to the appropriate command
            4. Manages transactions
            5. Handles errors

        Args:
            argv: Command line arguments (default: sys.argv[1:]).

        Returns:
            Exit code (0 for success, non-zero for failure).
        """
        argv = argv if argv is not None else sys.argv[1:]

        try:
            self._auto_import_commands()
            self.parser.load_commands()

            try:
                parsed_args, command = self.parser.parse_args(argv)
            except SystemExit as e:
                if e.code == 0:
                    return ExitCode.SUCCESS
                raise UsageError(
                    "Invalid command or arguments",
                    hint="Use 'noteman --help' to see available commands",
                ) from e

            args_dict = vars(parsed_args)

            command_name = args_dict.get("command")

            if not command_name:
                raise UsageError(
                    "No command specified",
                    hint="Use 'noteman --help' to see available commands",
                )

            if command is None:
                raise UsageError(
                    f"Unknown command: {command_name}",
                    hint="Use 'noteman --help' to see available commands",
                )

            self.config = load_config(args_dict)

            self.store = NoteStore(
                data_dir=self.config["data_dir"],
                pretty_print=self.config["storage"]["pretty_print"],
            )

            needs_write = self._is_write_command(command_name)

            if command_name == "init":
                exit_code = command.execute(parsed_args, self.config, self.store)
            else:
                with self.store.transaction(write=needs_write):
                    exit_code = command.execute(parsed_args, self.config, self.store)

            return exit_code if exit_code is not None else ExitCode.SUCCESS

        except NotemanError as e:
            return handle_error(e)
        except SystemExit as e:
            return e.code if e.code is not None else ExitCode.GENERAL_ERROR
        except Exception as e:
            return handle_error(e)


def main(argv: Optional[list] = None) -> int:
    """Main entry point for the CLI application.

    Args:
        argv: Command line arguments.

    Returns:
        Exit code.
    """
    dispatcher = Dispatcher()
    return dispatcher.dispatch(argv)
