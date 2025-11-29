"""
Core modem class coordinating transport, protocol, and URC handling.

This is the foundation that feature managers build upon.
"""

import logging
import threading
import time
from typing import Optional

from .transport import Transport
from .protocol import ATProtocol
from .urc import URCHandler, URCCallback
from ..exceptions import DeviceDisconnectedError

logger = logging.getLogger(__name__)


class ModemCore:
    """
    Core modem functionality.

    Coordinates:
    - Transport layer (serial communication)
    - Protocol layer (AT command execution)
    - URC handling (unsolicited result codes)
    - Reader thread (continuous modem monitoring)

    This class provides the foundation for feature-specific managers.
    """

    def __init__(
        self,
        transport: Transport,
        timeout: float = 1.0,
        log_urcs: bool = False,
        max_urc_queue_size: int = 1000,
        on_disconnect: Optional[callable] = None
    ) -> None:
        """
        Initialize modem core.

        Args:
            transport: Transport instance for communication
            timeout: Default timeout for AT commands
            log_urcs: Whether to log URCs at INFO level
            max_urc_queue_size: Maximum URCs to queue
            on_disconnect: Optional callback for disconnection events
        """
        self.transport = transport
        self.protocol = ATProtocol(transport, default_timeout=timeout)
        self.urc_handler = URCHandler(
            max_queue_size=max_urc_queue_size,
            log_urcs=log_urcs
        )

        # Reader thread management
        self._reader_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._running = False
        self._on_disconnect = on_disconnect

        # Error handling
        self._consecutive_errors = 0
        self._max_consecutive_errors = 5
        self._disconnected = False

        logger.info("Initialized ModemCore")

    def start(self) -> None:
        """
        Start the modem reader thread.

        The reader thread continuously reads from the transport and routes
        lines to either the protocol (for solicited responses) or URC handler
        (for unsolicited result codes).
        """
        if self._running:
            logger.warning("ModemCore already started")
            return

        # Reset disconnected state on start
        self._disconnected = False
        self._consecutive_errors = 0

        self._stop_event.clear()
        self._reader_thread = threading.Thread(
            target=self._reader_loop,
            daemon=True,
            name="ModemReaderThread"
        )
        self._reader_thread.start()
        self._running = True
        logger.info("Started modem reader thread")

    def stop(self) -> None:
        """
        Stop the modem reader thread.

        Waits for the thread to terminate gracefully.
        """
        if not self._running:
            return

        logger.info("Stopping modem reader thread...")
        self._stop_event.set()

        if self._reader_thread:
            self._reader_thread.join(timeout=1.0)
            if self._reader_thread.is_alive():
                logger.warning("Reader thread did not terminate in time")

        self._running = False
        logger.info("Stopped modem reader thread")

    def close(self) -> None:
        """
        Close the modem connection.

        Stops the reader thread and closes the transport.
        """
        logger.info("Closing modem connection")
        self.stop()
        self.transport.close()
        logger.info("Modem connection closed")

    def _reader_loop(self) -> None:
        """
        Continuously read lines from the modem.

        Classifies each line as either:
        - Solicited response (part of AT command response)
        - URC (unsolicited result code)

        Routes lines accordingly to protocol or URC handler.
        """
        logger.debug("Reader thread started")

        while not self._stop_event.is_set():
            try:
                # Read next line from transport
                line_bytes = self.transport.read_until(b"\r\n")

                # Reset error counter on successful read
                self._consecutive_errors = 0

                if not line_bytes:
                    continue

                # Decode and clean up line
                line = line_bytes.decode("utf-8", errors="ignore").strip()

                if not line:
                    continue

                logger.debug(f"Reader received: {line}")

                # Route line based on context
                self._route_line(line)

            except DeviceDisconnectedError as e:
                # Device is actually disconnected - stop the reader thread
                logger.error("Device disconnected, stopping reader thread")
                self._running = False
                self._disconnected = True

                # Call disconnect callback if provided
                if self._on_disconnect:
                    self._on_disconnect(e)

                break
            except Exception as e:
                # Handle consecutive errors with backoff
                self._consecutive_errors += 1
                logger.error(f"Error in reader loop ({self._consecutive_errors}/{self._max_consecutive_errors}): {e}")

                if self._consecutive_errors >= self._max_consecutive_errors:
                    logger.error(f"Too many consecutive errors ({self._consecutive_errors}), stopping reader thread")
                    self._running = False
                    break

                # Exponential backoff: 0.1s, 0.2s, 0.4s, 0.8s, 1.6s
                backoff_time = 0.1 * (2 ** (self._consecutive_errors - 1))
                time.sleep(backoff_time)

        logger.debug("Reader thread stopped")

    def _route_line(self, line: str) -> None:
        """
        Route a line to either protocol or URC handler.

        Args:
            line: Line to route
        """
        # If we're waiting for a command response
        if self.protocol.is_response_pending():
            # Check if this is a URC or solicited response
            if self.protocol.is_urc(line):
                # It's a URC - send to URC handler
                self.urc_handler.handle_urc(line)
            else:
                # It's part of the solicited response
                self.protocol.append_response_line(line)
        else:
            # No pending command, everything is a URC
            self.urc_handler.handle_urc(line)

    def register_urc_callback(self, prefix: str, callback: URCCallback) -> None:
        """
        Register a callback for URCs matching a prefix.

        Args:
            prefix: URC prefix to match (e.g., "+CMTI")
            callback: Function to call when URC is received

        Example:

        .. code-block:: python

            modem.register_urc_callback("+CMTI", lambda line: print(f"SMS: {line}"))
        """
        self.urc_handler.register_callback(prefix, callback)

    def unregister_urc_callback(self, prefix: str) -> bool:
        """
        Unregister a URC callback.

        Args:
            prefix: URC prefix to unregister

        Returns:
            True if callback was removed
        """
        return self.urc_handler.unregister_callback(prefix)

    def send_at(
        self,
        cmd: str,
        strip_ok: bool = False,
        remove_cmd_prefix: bool = False,
        timeout: Optional[float] = None
    ) -> list[str]:
        """
        Send an AT command.

        This is a convenience wrapper around protocol.send_command().

        Args:
            cmd: AT command (e.g., "AT+CSQ" or "+CSQ")
            strip_ok: Remove "OK" from response
            remove_cmd_prefix: Remove command prefix from first line
            timeout: Command timeout (uses default if None)

        Returns:
            List of response lines

        Raises:
            ATTimeoutError: If command times out
            EC25Error: If command returns ERROR
        """
        return self.protocol.send_command(
            cmd=cmd,
            strip_ok=strip_ok,
            remove_cmd_prefix=remove_cmd_prefix,
            timeout=timeout
        )

    def is_running(self) -> bool:
        """
        Check if the reader thread is running.

        Returns:
            True if running
        """
        return self._running

    def is_disconnected(self) -> bool:
        """
        Check if the device was disconnected during operation.

        This typically indicates a physical disconnection or USB port issue.

        Returns:
            True if device was disconnected, False otherwise
        """
        return self._disconnected

    def __enter__(self):
        """Context manager entry."""
        if not self._running:
            self.start()
        return self

    
    def __exit__(self, *exc):
        """Context manager exit."""
        self.close()
