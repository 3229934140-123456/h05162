"""Config command - View and manage configuration."""
import argparse
import json
from typing import Any, Dict

from noteman.commands.base import Command, register_command
from noteman.core.errors import ExitCode
from noteman.config.loader import get_config_value
from noteman.storage.store import NoteStore


@register_command
class ConfigCommand(Command):
    """View and manage configuration."""

    name = "config"
    description = "View and manage configuration"
    help = """View the current merged configuration.

Shows the effective configuration after merging defaults, config file,
environment variables, and command line arguments.

Examples:
  noteman config show
  noteman config get data_dir
  noteman config get display.color
  noteman config get --all
"""
    aliases = []

    def register_arguments(self, parser: argparse.ArgumentParser) -> None:
        """Register arguments for the config command."""
        subparsers = parser.add_subparsers(
            dest="config_action",
            title="subcommands",
        )

        show_parser = subparsers.add_parser(
            "show",
            help="Show full configuration",
            description="Show the full merged configuration",
        )
        show_parser.add_argument(
            "--raw",
            action="store_true",
            help="Show raw JSON output",
        )

        get_parser = subparsers.add_parser(
            "get",
            help="Get a specific configuration value",
            description="Get a specific configuration value",
        )
        get_parser.add_argument(
            "key",
            nargs="?",
            help="Configuration key (e.g., display.color)",
        )
        get_parser.add_argument(
            "--all",
            "-a",
            action="store_true",
            help="Show all configuration keys",
        )

    def _format_config(self, config: Dict[str, Any], indent: int = 0) -> str:
        """Format configuration for display."""
        lines = []
        prefix = "  " * indent

        for key, value in sorted(config.items()):
            if isinstance(value, dict):
                lines.append(f"{prefix}{key}:")
                lines.append(self._format_config(value, indent + 1))
            else:
                lines.append(f"{prefix}{key}: {value!r}")

        return "\n".join(lines)

    def _print_all_keys(self, config: Dict[str, Any], prefix: str = "") -> None:
        """Print all configuration keys in dot notation."""
        for key, value in sorted(config.items()):
            full_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                self._print_all_keys(value, full_key)
            else:
                print(f"  {full_key} = {value!r}")

    def execute(
        self,
        args: argparse.Namespace,
        config: Dict[str, Any],
        store: NoteStore,
    ) -> int:
        """Execute the config command."""
        action = getattr(args, "config_action", None)

        if not action:
            action = "show"

        if action == "show":
            if args.raw:
                print(json.dumps(config, indent=2, ensure_ascii=False))
            else:
                print("Current configuration:")
                print("=" * 50)
                print(self._format_config(config))
                print("=" * 50)
            return ExitCode.SUCCESS

        if action == "get":
            if getattr(args, "all", False):
                print("All configuration keys:")
                print()
                self._print_all_keys(config)
                return ExitCode.SUCCESS

            if not args.key:
                print("Error: Key is required unless using --all", file=__import__("sys").stderr)
                return ExitCode.USAGE_ERROR

            value = get_config_value(config, args.key)
            if value is None:
                print(f"Key not found: {args.key}")
                return ExitCode.NOT_FOUND_ERROR

            if isinstance(value, dict):
                print(json.dumps(value, indent=2, ensure_ascii=False))
            else:
                print(value)
            return ExitCode.SUCCESS

        print(f"Unknown action: {action}", file=__import__("sys").stderr)
        return ExitCode.USAGE_ERROR
