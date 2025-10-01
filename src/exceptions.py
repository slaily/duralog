from dataclasses import dataclass


class DuraLogError(Exception):
    """Base exception for all duralog errors."""

    pass


@dataclass
class DuraLogConfigurationError(DuraLogError):
    """Raised for invalid configuration or setup issues."""

    message: str


@dataclass
class DuraLogCorruptionError(DuraLogError):
    """Raised when a corrupt record is detected during reading."""

    file_path: str
    offset: int
    reason: str
    original_error: Exception = None


@dataclass
class DuraLogIOError(DuraLogError):
    """Wraps a low-level OS error during a file operation."""

    file_path: str
    message: str
    original_error: Exception
