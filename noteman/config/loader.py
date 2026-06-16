"""Configuration loader with priority-based merging.

Priority order (highest to lowest):
    1. Command line arguments
    2. Environment variables (NOTEMAN_*)
    3. Configuration file (~/.noteman/config.yaml or NOTEMAN_CONFIG)
    4. Default values

Environment variable mapping:
    NOTEMAN_DATA_DIR  -> data_dir
    NOTEMAN_EDITOR    -> editor
    NOTEMAN_LOG_LEVEL -> log_level
"""
import os
import json
import copy
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

from noteman.core.errors import ConfigError


DEFAULT_CONFIG: Dict[str, Any] = {
    "data_dir": "~/.noteman/data",
    "editor": "vim",
    "log_level": "info",
    "storage": {
        "format": "json",
        "pretty_print": True,
    },
    "display": {
        "color": True,
        "pager": False,
        "date_format": "%Y-%m-%d %H:%M:%S",
    },
    "search": {
        "case_sensitive": False,
        "include_content": True,
        "include_tags": True,
    },
}

ENV_PREFIX = "NOTEMAN_"

ENV_MAPPING: Dict[str, str] = {
    "NOTEMAN_DATA_DIR": "data_dir",
    "NOTEMAN_EDITOR": "editor",
    "NOTEMAN_LOG_LEVEL": "log_level",
    "NOTEMAN_CONFIG": "config_file",
}


def _deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge two dictionaries.

    Args:
        base: The base dictionary to merge into.
        override: The dictionary with values to override.

    Returns:
        A new dictionary with merged values.
    """
    result = copy.deepcopy(base)
    for key, value in override.items():
        if (
            key in result
            and isinstance(result[key], dict)
            and isinstance(value, dict)
        ):
            result[key] = _deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def _load_config_file(filepath: Path) -> Dict[str, Any]:
    """Load configuration from a file.

    Supports YAML and JSON formats.

    Args:
        filepath: Path to the configuration file.

    Returns:
        Dictionary of configuration values.

    Raises:
        ConfigError: If the file cannot be loaded or parsed.
    """
    if not filepath.exists():
        return {}

    try:
        content = filepath.read_text(encoding="utf-8")
    except OSError as e:
        raise ConfigError(
            f"Cannot read config file: {filepath}",
            hint=f"Check file permissions: {e}",
        ) from e

    if not content.strip():
        return {}

    suffix = filepath.suffix.lower()

    if suffix in (".yaml", ".yml"):
        try:
            import yaml

            return yaml.safe_load(content) or {}
        except ImportError:
            raise ConfigError(
                "YAML support requires PyYAML package",
                hint="Install with: pip install pyyaml",
            )
        except yaml.YAMLError as e:
            raise ConfigError(
                f"Invalid YAML in config file: {e}",
                hint="Check syntax or use JSON format instead",
            ) from e
    elif suffix == ".json":
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            raise ConfigError(
                f"Invalid JSON in config file: {e}",
                hint="Check syntax of your JSON config",
            ) from e
    else:
        raise ConfigError(
            f"Unsupported config file format: {suffix}",
            hint="Use .yaml, .yml, or .json extension",
        )


def _load_env_vars() -> Dict[str, Any]:
    """Load configuration from environment variables.

    Returns:
        Dictionary of configuration values from environment.
    """
    env_config: Dict[str, Any] = {}

    for env_var, config_key in ENV_MAPPING.items():
        if env_var == "NOTEMAN_CONFIG":
            continue
        value = os.environ.get(env_var)
        if value is not None:
            keys = config_key.split(".")
            current = env_config
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            current[keys[-1]] = _parse_env_value(value)

    return env_config


def _parse_env_value(value: str) -> Any:
    """Parse environment variable value to appropriate Python type.

    Args:
        value: The string value from environment.

    Returns:
        Parsed value (bool, int, float, or string).
    """
    lower_value = value.lower()

    if lower_value in ("true", "yes", "1"):
        return True
    if lower_value in ("false", "no", "0"):
        return False

    try:
        return int(value)
    except ValueError:
        pass

    try:
        return float(value)
    except ValueError:
        pass

    return value


def _get_config_file_path(explicit_path: Optional[str] = None) -> Optional[Path]:
    """Determine the configuration file path.

    Args:
        explicit_path: Explicit path from command line or env var.

    Returns:
        Path to the config file or None if not found.
    """
    if explicit_path:
        path = Path(explicit_path).expanduser()
        if path.exists():
            return path
        return None

    env_path = os.environ.get("NOTEMAN_CONFIG")
    if env_path:
        path = Path(env_path).expanduser()
        if path.exists():
            return path

    for candidate in [
        Path("~/.noteman/config.yaml").expanduser(),
        Path("~/.noteman/config.yml").expanduser(),
        Path("~/.noteman/config.json").expanduser(),
        Path("./.noteman.yaml").expanduser(),
        Path("./.noteman.json").expanduser(),
    ]:
        if candidate.exists():
            return candidate

    return None


def _expand_paths(config: Dict[str, Any]) -> Dict[str, Any]:
    """Expand user home directory in path values.

    Args:
        config: Raw configuration dictionary.

    Returns:
        Configuration with expanded paths.
    """
    config = copy.deepcopy(config)

    if "data_dir" in config:
        config["data_dir"] = str(Path(config["data_dir"]).expanduser())

    return config


def _merge_cli_args(config: Dict[str, Any], cli_args: Dict[str, Any]) -> Dict[str, Any]:
    """Merge command line arguments into configuration.

    Args:
        config: Current configuration.
        cli_args: Command line arguments (only non-None values).

    Returns:
        Merged configuration.
    """
    cli_config = copy.deepcopy(config)

    if cli_args.get("data_dir"):
        cli_config["data_dir"] = cli_args["data_dir"]
    if cli_args.get("editor"):
        cli_config["editor"] = cli_args["editor"]
    if cli_args.get("log_level"):
        cli_config["log_level"] = cli_args["log_level"]
    if cli_args.get("no_color"):
        cli_config["display"]["color"] = False
    if cli_args.get("config"):
        cli_config["config_file"] = cli_args["config"]

    return cli_config


def load_config(cli_args: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Load and merge configuration from all sources.

    Priority (highest to lowest):
        1. CLI arguments
        2. Environment variables
        3. Configuration file
        4. Default values

    Args:
        cli_args: Command line arguments dictionary.

    Returns:
        Final merged configuration.

    Raises:
        ConfigError: If configuration cannot be loaded.
    """
    cli_args = cli_args or {}

    config_file_path = _get_config_file_path(cli_args.get("config"))

    file_config = _load_config_file(config_file_path) if config_file_path else {}

    env_config = _load_env_vars()

    config = copy.deepcopy(DEFAULT_CONFIG)
    config = _deep_merge(config, file_config)
    config = _deep_merge(config, env_config)
    config = _expand_paths(config)
    config = _merge_cli_args(config, cli_args)

    config["config_file"] = str(config_file_path) if config_file_path else None

    return config


def get_config_value(config: Dict[str, Any], key: str, default: Any = None) -> Any:
    """Get a nested configuration value using dot notation.

    Args:
        config: Configuration dictionary.
        key: Dot-separated key path (e.g., "display.color").
        default: Default value if key not found.

    Returns:
        The configuration value or default.
    """
    keys = key.split(".")
    value = config

    for k in keys:
        if isinstance(value, dict) and k in value:
            value = value[k]
        else:
            return default

    return value
