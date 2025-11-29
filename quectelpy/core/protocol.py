"""
AT command protocol handler.

Manages AT command execution, response parsing, and URC detection.
"""

import logging
import threading
import time
from typing import Optional

from .transport import Transport
from ..exceptions import ATTimeoutError, ATParseError, EC25Error

logger = logging.getLogger(__name__)


class ATProtocol:
    """
    AT command protocol handler.

    Manages thread-safe AT command execution and response handling.
    Works in conjunction with URCHandler for URC separation.
    """

    def __init__(
        self,
        transport: Transport,
        default_timeout: float = 1.0
    ) -> None:
        """
        Initialize AT protocol handler.

        Args:
            transport: Transport instance for communication
            default_timeout: Default timeout for AT commands in seconds
        """
        self.transport = transport
        self.default_timeout = default_timeout

        # Thread safety for AT commands
        self._at_lock = threading.Lock()

        # Response handling
        self._resp_buffer: list[str] = []
        self._resp_done_event = threading.Event()

        # Command tracking for URC detection and echo stripping
        self._full_cmd: Optional[str] = None
        self._norm_prefix: Optional[str] = None
        self._resp_prefix: Optional[str] = None
        self._sent_cmd: Optional[str] = None  # Track exact command sent for echo detection

        logger.info("Initialized AT protocol handler")

    def send_command(
        self,
        cmd: str = "AT",
        strip_ok: bool = False,
        remove_cmd_prefix: bool = False,
        timeout: Optional[float] = None
    ) -> list[str]:
        """
        Send an AT command and wait for the solicited response.

        Thread-safe execution with proper URC separation via reader thread.

        Args:
            cmd: AT command to send (e.g., "AT+CSQ" or "+CSQ")
            strip_ok: Remove "OK" from response lines
            remove_cmd_prefix: Remove command prefix from first response line
            timeout: Command timeout in seconds (uses default if None)

        Returns:
            List of response lines

        Raises:
            ATTimeoutError: If command times out
            EC25Error: If command returns ERROR
            ATParseError: If write fails
        """
        with self._at_lock:
            # Clear previous response
            self._resp_buffer = []
            self._resp_done_event.clear()

            # Normalize command
            cmd = self._normalize_command(cmd)

            # Precompute prefixes for smart URC detection
            self._precompute_prefixes(cmd)

            # Store sent command for echo detection
            self._sent_cmd = cmd.strip()

            logger.debug(f"Sending AT command: {cmd.strip()}")

            # Clear input buffer and send command
            self.transport.reset_input_buffer()
            written = self.transport.write(cmd.encode("utf-8"))
            if not written:
                raise ATParseError(f"Failed to write AT command: {cmd}")

            # Wait for response
            timeout_val = timeout if timeout is not None else self.default_timeout
            end_time = time.monotonic() + timeout_val

            while not self._resp_done_event.is_set():
                if time.monotonic() > end_time:
                    logger.error(f"AT command timed out: {cmd.strip()}")
                    raise ATTimeoutError(f"AT command timed out: {cmd.strip()}")
                time.sleep(0.01)

            # Retrieve response
            lines = list(self._resp_buffer)

            # Strip echo if present (detection-based, not state-based)
            if lines and self._sent_cmd and lines[0] == self._sent_cmd:
                logger.debug(f"Stripping echo line: {lines[0]}")
                lines = lines[1:]

            logger.debug(f"Received response: {lines}")

            # Process response
            if lines and lines[-1] == "OK":
                if strip_ok:
                    lines = lines[:-1]
            elif lines and lines[-1] == "ERROR":
                logger.error(f"AT command returned ERROR: {cmd.strip()}")
                raise EC25Error(f"AT command {cmd.strip()} returned ERROR")

            if remove_cmd_prefix and lines:
                lines[0] = self._remove_cmd_response(lines[0])

            return lines

    def _normalize_command(self, cmd: str) -> str:
        """
        Normalize AT command format.

        Ensures command starts with "AT" and ends with "\r\n".
        """
        # Add AT prefix if missing
        if not cmd.upper().startswith("AT"):
            cmd = "AT" + cmd

        # Add line terminator if missing
        if not cmd.endswith("\r\n"):
            cmd += "\r\n"

        return cmd

    def _precompute_prefixes(self, cmd: str) -> None:
        """
        Precompute command prefixes for efficient response parsing.

        Args:
            cmd: Normalized AT command (e.g., "AT+CREG?\r\n")
        """
        raw = cmd.strip()

        # Remove AT prefix
        if raw.upper().startswith("AT"):
            raw = raw[2:]

        # Remove line terminators
        raw = raw.replace("\r", "").replace("\n", "")

        # Store full command (e.g., "+CREG?")
        self._full_cmd = raw

        # Extract normalized prefix (e.g., "+CREG")
        self._norm_prefix = raw.replace("?", "").split("=")[0]

        # Build response prefix (e.g., "+CREG:")
        self._resp_prefix = self._norm_prefix + ":"

        logger.debug(f"Command prefixes - full: {self._full_cmd}, "
                    f"norm: {self._norm_prefix}, resp: {self._resp_prefix}")

    def _remove_cmd_response(self, response: str) -> str:
        """
        Remove "+CMD:" prefix from a response line.

        Uses precomputed prefix for efficiency.

        Args:
            response: Response line (e.g., "+CREG: 0,1")

        Returns:
            Response with prefix removed (e.g., "0,1")
        """
        if self._resp_prefix and response.startswith(self._resp_prefix):
            return response[len(self._resp_prefix):].strip()
        return response

    def is_urc(self, line: str) -> bool:
        """
        Determine if a line is an unsolicited result code.

        Uses command context to distinguish URCs from solicited responses.

        Args:
            line: Line to classify

        Returns:
            True if line is a URC, False if solicited response
        """
        # Lines not starting with '+' are not URCs
        if not line.startswith("+"):
            return False

        # If we're waiting for a response and have a prefix
        if not self._resp_done_event.is_set() and self._norm_prefix:
            # It's a solicited response if it matches our command prefix
            return not line.startswith(self._norm_prefix + ":")

        # Otherwise, it's a URC
        return True

    def append_response_line(self, line: str) -> bool:
        """
        Append a line to the response buffer.

        Args:
            line: Response line to append

        Returns:
            True if this completes the response (OK/ERROR received)
        """
        self._resp_buffer.append(line)

        # Check for completion
        if line == "OK" or line == "ERROR":
            self._resp_done_event.set()
            return True

        return False

    def is_response_pending(self) -> bool:
        """
        Check if we're currently waiting for a command response.

        Returns:
            True if response is pending
        """
        return not self._resp_done_event.is_set()

    def get_current_prefix(self) -> Optional[str]:
        """
        Get the current command's normalized prefix.

        Returns:
            Current command prefix or None
        """
        return self._norm_prefix

    