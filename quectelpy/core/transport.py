"""
Transport layer abstraction for modem communication.

Provides abstractions for serial communication with dependency injection support.
"""

import logging
import threading
from abc import ABC, abstractmethod
from typing import Optional
import serial
from serial import SerialException

from ..exceptions import EC25Error, DeviceDisconnectedError

logger = logging.getLogger(__name__)


class Transport(ABC):
    """Abstract base class for modem transport."""

    @abstractmethod
    def write(self, data: bytes) -> int:
        """
        Write data to the transport.

        Args:
            data: Bytes to write

        Returns:
            Number of bytes written

        Raises:
            EC25Error: If write fails
        """
        pass

    @abstractmethod
    def read_until(self, terminator: bytes = b"\r\n", timeout: Optional[float] = None) -> bytes:
        """
        Read from transport until terminator is found.

        Args:
            terminator: Byte sequence marking end of data
            timeout: Optional timeout in seconds

        Returns:
            Bytes read including terminator

        Raises:
            EC25Error: If read fails
        """
        pass

    @abstractmethod
    def reset_input_buffer(self) -> None:
        """Clear the input buffer."""
        pass

    @abstractmethod
    def is_open(self) -> bool:
        """Check if transport is open."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close the transport."""
        pass


class SerialTransport(Transport):
    """Serial port transport implementation."""

    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout: float = 1.0
    ) -> None:
        """
        Initialize serial transport.

        Args:
            port: Serial port path (e.g., /dev/ttyUSB2)
            baudrate: Baud rate for serial communication
            timeout: Read timeout in seconds

        Raises:
            EC25Error: If serial port cannot be opened
        """
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout

        try:
            self._serial = serial.Serial(
                port=port,
                baudrate=baudrate,
                timeout=timeout
            )
            logger.info(f"Opened serial port {port} at {baudrate} baud")
        except SerialException as e:
            logger.error(f"Failed to open serial port {port}: {e}")
            raise EC25Error(f"Failed to open serial port {port}: {e}") from e

    def write(self, data: bytes) -> int:
        """Write data to serial port."""
        try:
            written = self._serial.write(data)
            logger.debug(f"Wrote {written} bytes: {data}")
            return written
        except SerialException as e:
            logger.error(f"Serial write failed: {e}")
            raise EC25Error(f"Serial write failed: {e}") from e

    def read_until(self, terminator: bytes = b"\r\n", timeout: Optional[float] = None) -> bytes:
        """Read from serial port until terminator."""
        try:
            # Temporarily change timeout if specified
            original_timeout = None
            if timeout is not None:
                original_timeout = self._serial.timeout
                self._serial.timeout = timeout

            data = self._serial.read_until(terminator)

            # Restore original timeout
            if original_timeout is not None:
                self._serial.timeout = original_timeout

            if data:
                logger.debug(f"Read {len(data)} bytes: {data}")

            return data
        except SerialException as e:
            error_str = str(e).lower()

            # Detect device disconnection
            if any(phrase in error_str for phrase in [
                "device disconnected",
                "device reports readiness to read but returned no data",
                "no such device",
                "device not configured",
                "input/output error"
            ]):
                logger.error(f"Device disconnected: {e}")
                raise DeviceDisconnectedError(
                    f"Serial device disconnected: {e}",
                    response=[str(e)]
                ) from e

            # Other serial errors
            logger.error(f"Serial read failed: {e}")
            raise EC25Error(f"Serial read failed: {e}") from e

    def reset_input_buffer(self) -> None:
        """Clear the serial input buffer."""
        try:
            self._serial.reset_input_buffer()
            logger.debug("Reset input buffer")
        except SerialException as e:
            logger.error(f"Failed to reset input buffer: {e}")
            raise EC25Error(f"Failed to reset input buffer: {e}") from e

    def is_open(self) -> bool:
        """Check if serial port is open."""
        return self._serial and self._serial.is_open

    def close(self) -> None:
        """Close the serial port."""
        if self._serial and self._serial.is_open:
            self._serial.close()
            logger.info(f"Closed serial port {self.port}")


class MockTransport(Transport):
    """
    Mock transport for testing.

    Simulates modem responses without requiring hardware.
    """

    def __init__(self) -> None:
        """Initialize mock transport."""
        self._open = True
        self._input_buffer: list[bytes] = []
        self._response_queue: list[list[str]] = []
        self._lock = threading.Lock()
        logger.info("Initialized MockTransport")

    def add_response(self, lines: list[str]) -> None:
        """
        Queue a response to be returned by read_until.

        Args:
            lines: List of response lines (e.g., ["+CSQ: 24,99", "OK"])
        """
        with self._lock:
            self._response_queue.append(lines)
            logger.debug(f"Added mock response: {lines}")

    def write(self, data: bytes) -> int:
        """Simulate writing data."""
        if not self._open:
            raise DeviceDisconnectedError(
                "MockTransport is closed (simulating device disconnection)",
                response=["MockTransport closed"]
            )

        logger.debug(f"Mock write: {data}")
        return len(data)

    def read_until(self, terminator: bytes = b"\r\n", timeout: Optional[float] = None) -> bytes:
        """
        Simulate reading from modem.

        Returns queued responses one line at a time.
        """
        if not self._open:
            raise DeviceDisconnectedError(
                "MockTransport is closed (simulating device disconnection)",
                response=["MockTransport closed"]
            )

        with self._lock:
            # Check if we have buffered input
            if self._input_buffer:
                return self._input_buffer.pop(0)

            # Get next response from queue
            if self._response_queue:
                current_response = self._response_queue[0]
                if current_response:
                    line = current_response.pop(0)

                    # Remove empty response from queue
                    if not current_response:
                        self._response_queue.pop(0)

                    # Add terminator and return
                    result = (line + "\r\n").encode("utf-8")
                    logger.debug(f"Mock read: {result}")
                    return result

        # No data available
        return b""

    def reset_input_buffer(self) -> None:
        """Clear mock input buffer."""
        with self._lock:
            self._input_buffer.clear()
            logger.debug("Reset mock input buffer")

    def is_open(self) -> bool:
        """Check if mock transport is open."""
        return self._open

    def close(self) -> None:
        """Close mock transport."""
        self._open = False
        logger.info("Closed MockTransport")

    def clear_responses(self) -> None:
        """Clear all queued responses (useful for testing)."""
        with self._lock:
            self._response_queue.clear()
            logger.debug("Cleared mock response queue")
