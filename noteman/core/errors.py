"""Error handling module with exit codes and user-friendly messages.

Error propagation flow:
    Storage layer errors -> Command layer -> Dispatcher -> CLI layer -> User
"""
import sys
from typing import Optional


class ExitCode:
    """Standard exit codes for the CLI application."""
    SUCCESS = 0
    GENERAL_ERROR = 1
    CONFIG_ERROR = 2
    STORAGE_ERROR = 3
    VALIDATION_ERROR = 4
    NOT_FOUND_ERROR = 5
    PERMISSION_ERROR = 6
    USAGE_ERROR = 64
    DATA_ERROR = 65
    IO_ERROR = 74


class NotemanError(Exception):
    """Base exception class for all Noteman errors."""

    def __init__(
        self,
        message: str,
        exit_code: int = ExitCode.GENERAL_ERROR,
        hint: Optional[str] = None,
    ):
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code
        self.hint = hint

    def __str__(self) -> str:
        output = f"Error: {self.message}"
        if self.hint:
            output += f"\nHint: {self.hint}"
        return output


class ConfigError(NotemanError):
    """Configuration-related errors."""

    def __init__(self, message: str, hint: Optional[str] = None):
        super().__init__(message, ExitCode.CONFIG_ERROR, hint)


class StorageError(NotemanError):
    """Storage-related errors."""

    def __init__(self, message: str, hint: Optional[str] = None):
        super().__init__(message, ExitCode.STORAGE_ERROR, hint)


class ValidationError(NotemanError):
    """Data validation errors."""

    def __init__(self, message: str, hint: Optional[str] = None):
        super().__init__(message, ExitCode.VALIDATION_ERROR, hint)


class NotFoundError(NotemanError):
    """Resource not found errors."""

    def __init__(self, message: str, hint: Optional[str] = None):
        super().__init__(message, ExitCode.NOT_FOUND_ERROR, hint)


class PermissionError(NotemanError):
    """Permission-related errors."""

    def __init__(self, message: str, hint: Optional[str] = None):
        super().__init__(message, ExitCode.PERMISSION_ERROR, hint)


class UsageError(NotemanError):
    """Command usage errors."""

    def __init__(self, message: str, hint: Optional[str] = None):
        super().__init__(message, ExitCode.USAGE_ERROR, hint)


def handle_error(error: Exception) -> int:
    """Handle exceptions and return appropriate exit code.

    Args:
        error: The exception to handle.

    Returns:
        Exit code for the process.
    """
    if isinstance(error, NotemanError):
        print(str(error), file=sys.stderr)
        return error.exit_code

    print(f"Unexpected error: {error}", file=sys.stderr)
    return ExitCode.GENERAL_ERROR
