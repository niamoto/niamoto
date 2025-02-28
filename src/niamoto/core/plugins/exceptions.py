"""
Custom exceptions for the Niamoto plugin system.
"""

from typing import Dict, Any, Optional


class PluginError(Exception):
    """Base exception class for all plugin-related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize plugin error.

        Args:
            message: Error message
            details: Optional dictionary with additional error details
        """
        super().__init__(message)
        self.details = details or {}

    def __str__(self) -> str:
        """Return formatted error message."""
        msg = str(super().__str__())
        if self.details:
            msg += f"\nDetails: {self.details}"
        return msg


class PluginRegistrationError(PluginError):
    """Error raised when plugin registration fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize registration error.

        Args:
            message: Error message
            details: Optional dictionary with additional error details like plugin name
        """
        super().__init__(f"Plugin registration failed: {message}", details)


class PluginNotFoundError(PluginError):
    """Error raised when a requested plugin is not found in the registry."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize not found error.

        Args:
            message: Error message
            details: Optional dictionary with available plugins, requested name, etc.
        """
        super().__init__(f"Plugin not found: {message}", details)


class PluginConfigError(PluginError):
    """Error raised when plugin configuration is invalid."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize configuration error.

        Args:
            message: Error message
            details: Optional dictionary with configuration details, validation errors
        """
        super().__init__(f"Plugin configuration error: {message}", details)


class PluginLoadError(PluginError):
    """Error raised when loading a plugin fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize load error.

        Args:
            message: Error message
            details: Optional dictionary with plugin file path, error details
        """
        super().__init__(f"Plugin loading failed: {message}", details)


class PluginValidationError(PluginError):
    """Error raised when plugin validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize validation error.

        Args:
            message: Error message
            details: Optional dictionary with validation context
        """
        super().__init__(f"Plugin validation failed: {message}", details)


class PluginExecutionError(PluginError):
    """Error raised when plugin execution fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize execution error.

        Args:
            message: Error message
            details: Optional dictionary with execution context, errors
        """
        super().__init__(f"Plugin execution failed: {message}", details)


class PluginDependencyError(PluginError):
    """Error raised when plugin dependencies are missing or incompatible."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize dependency error.

        Args:
            message: Error message
            details: Optional dictionary with dependency information
        """
        super().__init__(f"Plugin dependency error: {message}", details)


class PluginTypeError(PluginError):
    """Error raised when plugin type is invalid or incompatible."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize type error.

        Args:
            message: Error message
            details: Optional dictionary with type information
        """
        super().__init__(f"Plugin type error: {message}", details)


class PluginStateError(PluginError):
    """Error raised when plugin is in an invalid state."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize state error.

        Args:
            message: Error message
            details: Optional dictionary with state information
        """
        super().__init__(f"Plugin state error: {message}", details)
