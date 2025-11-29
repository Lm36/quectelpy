"""
Exceptions for QuectelPy library.

Provides detailed error information for debugging modem communication issues.
"""

from typing import Optional


class EC25Error(Exception):
    """
    Base exception for Quectel modem errors.

    All QuectelPy exceptions inherit from this class.
    """

    def __init__(
        self,
        message: str,
        command: Optional[str] = None,
        response: Optional[list[str]] = None
    ) -> None:
        """
        Initialize exception with context.

        Args:
            message: Error description
            command: AT command that caused the error (if applicable)
            response: Modem response (if applicable)
        """
        self.command = command
        self.response = response
        super().__init__(message)

    def __str__(self) -> str:
        """Format error message with context."""
        parts = [super().__str__()]

        if self.command:
            parts.append(f"Command: {self.command}")

        if self.response:
            parts.append(f"Response: {self.response}")

        return " | ".join(parts)


class ATTimeoutError(EC25Error):
    """
    Raised when an AT command times out.

    This typically indicates:
    - Modem is not responding
    - Serial connection issue
    - Command takes longer than timeout
    """
    pass


class ATParseError(EC25Error):
    """
    Raised when an AT command response cannot be parsed.

    This indicates:
    - Unexpected response format
    - Missing expected fields
    - Invalid data in response
    """
    pass


class TransportError(EC25Error):
    """
    Raised when transport layer fails.

    This indicates:
    - Serial port issues
    - Connection lost
    - Hardware communication failure
    """
    pass


class DeviceDisconnectedError(TransportError):
    """
    Raised when device is disconnected during operation.

    This is a fatal error that requires closing and reopening the connection.
    """
    pass


class ModemNotStartedError(EC25Error):
    """
    Raised when attempting to use modem before starting reader thread.
    """
    pass


class SIMError(EC25Error):
    """
    Raised when SIM card operations fail.

    This indicates:
    - SIM not inserted
    - SIM PIN required
    - SIM locked
    """
    pass


class NetworkError(EC25Error):
    """
    Raised when network operations fail.

    This indicates:
    - Not registered to network
    - No signal
    - Network rejected registration
    """
    pass


class SMSError(EC25Error):
    """
    Raised when SMS operations fail.

    This indicates:
    - SMS send failure
    - Invalid message format
    - Storage full
    - Invalid message index
    - PDU encoding/decoding error
    """
    pass

