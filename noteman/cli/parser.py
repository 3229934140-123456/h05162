"""CLI parser for Git-style command line interface.

This module handles the two-level argument parsing:
    1. Global options parsed first (before subcommand)
    2. Subcommand-specific options parsed after subcommand name

Argument parsing flow:
    Command line: noteman [global options] <subcommand> [subcommand options]

Global options (examples):
    --config       Path to config file
    --data-dir     Override data directory
    --editor       Override editor
    --no-color     Disable colored output
    --log-level    Set logging level
    --version      Show version
    --help         Show help

The parser dynamically discovers and registers subcommands from the
CommandRegistry, so adding new commands doesn't require changes here.
"""
import argparse
import sys
from typing import Any, Dict, Optional, Tuple

from noteman import __version__
from noteman.commands.base import Command, CommandRegistry


class CLIParser:
    """Two-level CLI parser with global and subcommand options.

    This parser implements the Git-style CLI interface where global
    options come before the subcommand name, and subcommand-specific
    options come after.

    The parser dynamically loads all registered commands from the
    CommandRegistry, making it easy to add new commands without
    modifying this core.

    Usage:
        parser = CLIParser()
        parser.load_commands()
        args, command_instance = parser.parse_args(sys.argv[1:])
    """

    def __init__(self, prog: str = "noteman"):
        """Initialize the CLI parser.

        Args:
            prog: Program name for help text.
        """
        self.prog = prog
        self.global_parser = self._create_global_parser()
        self.subparsers = None
        self.command_parsers: Dict[str, argparse.ArgumentParser] = {}
        self.command_instances: Dict[str, Command] = {}
        self.main_parser: Optional[argparse.ArgumentParser] = None

    def _create_global_parser(self) -> argparse.ArgumentParser:
        """Create the parser for global options.

        Returns:
            ArgumentParser for global options.
        """
        parser = argparse.ArgumentParser(
            prog=self.prog,
            add_help=False,
            description="Noteman - A Git-style note management tool",
        )

        parser.add_argument(
            "--config",
            type=str,
            help="Path to configuration file",
        )
        parser.add_argument(
            "--data-dir",
            type=str,
            help="Override data directory path",
        )
        parser.add_argument(
            "--editor",
            type=str,
            help="Override default editor",
        )
        parser.add_argument(
            "--log-level",
            choices=["debug", "info", "warning", "error", "critical"],
            help="Set logging level",
        )
        parser.add_argument(
            "--no-color",
            action="store_true",
            help="Disable colored output",
        )
        parser.add_argument(
            "--version",
            action="store_true",
            help="Show version information",
        )

        return parser

    def load_commands(self) -> None:
        """Load all commands from the registry and create subparsers.

        This method iterates over all registered commands and creates
        a subparser for each one, allowing each command to declare
        its own arguments.

        This is the key to the plugin architecture: new commands are
        automatically picked up from the registry without any changes
        to this code.
        """
        self.main_parser = argparse.ArgumentParser(
            prog=self.prog,
            description="Noteman - A Git-style note management tool",
            parents=[self.global_parser],
            formatter_class=argparse.RawDescriptionHelpFormatter,
        )

        self.subparsers = self.main_parser.add_subparsers(
            title="commands",
            dest="command",
            description="Available commands:",
            help="For command-specific help, run 'noteman <command> --help'",
        )

        for name, command_class in CommandRegistry.get_all().items():
            command_instance = command_class()
            self.command_instances[name] = command_instance

            subparser = self.subparsers.add_parser(
                name,
                help=command_instance.description,
                description=command_instance.help or command_instance.description,
                aliases=getattr(command_instance, "aliases", []),
                formatter_class=argparse.RawDescriptionHelpFormatter,
            )

            command_instance.register_arguments(subparser)

            self.command_parsers[name] = subparser

            for alias in getattr(command_instance, "aliases", []):
                self.command_parsers[alias] = subparser

    def _parse_global_only(
        self, argv: Optional[list] = None
    ) -> Tuple[argparse.Namespace, list]:
        """Parse only global options, leaving the rest for subcommand.

        Args:
            argv: Command line arguments (default: sys.argv[1:]).

        Returns:
            Tuple of (global_args, remaining_args).
        """
        argv = argv if argv is not None else sys.argv[1:]

        global_args, remaining = self.global_parser.parse_known_args(argv)

        return global_args, remaining

    def parse_args(
        self, argv: Optional[list] = None
    ) -> Tuple[argparse.Namespace, Optional[Command]]:
        """Parse all command line arguments.

        This implements the two-level parsing:
        1. First check for --version or --help at global level
        2. Then parse everything including subcommands

        Args:
            argv: Command line arguments (default: sys.argv[1:]).

        Returns:
            Tuple of (parsed_args, command_instance or None).

        Raises:
            SystemExit: If --version or --help is handled.
        """
        if self.main_parser is None:
            self.load_commands()

        argv = argv if argv is not None else sys.argv[1:]

        if "--version" in argv or "-v" in argv:
            print(f"noteman {__version__}")
            sys.exit(0)

        parsed_args = self.main_parser.parse_args(argv)

        command_name = getattr(parsed_args, "command", None)
        command_instance = None

        if command_name:
            command_instance = self.command_instances.get(command_name)
            if command_instance is None:
                for name, cmd in self.command_instances.items():
                    if command_name in getattr(cmd, "aliases", []):
                        command_instance = cmd
                        break

        return parsed_args, command_instance

    def get_command_help(self, command_name: str) -> str:
        """Get help text for a specific command.

        Args:
            command_name: Name of the command.

        Returns:
            Help text string.
        """
        parser = self.command_parsers.get(command_name)
        if parser:
            return parser.format_help()
        return f"Unknown command: {command_name}"

    def get_global_help(self) -> str:
        """Get help text for global options.

        Returns:
            Global help text string.
        """
        return self.global_parser.format_help()

    def get_full_help(self) -> str:
        """Get full help text including all commands.

        Returns:
            Full help text string.
        """
        if self.main_parser is None:
            self.load_commands()
        return self.main_parser.format_help()
