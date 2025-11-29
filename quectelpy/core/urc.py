"""
Unsolicited Result Code (URC) handler.

Manages URC queuing, callbacks, and dispatching in a thread-safe manner.
"""

import logging
import threading
from collections import deque
from typing import Callable, Dict, Deque, Optional

logger = logging.getLogger(__name__)

# Type alias for URC callbacks
URCCallback = Callable[[str], None]


class URCHandler:
    """
    Handles unsolicited result codes from the modem.

    Features:
    - Bounded queue to prevent memory issues
    - Callback registration system
    - Thread-safe operations
    - Error handling for misbehaving callbacks
    """

    def __init__(
        self,
        max_queue_size: int = 1000,
        log_urcs: bool = False
    ) -> None:
        """
        Initialize URC handler.

        Args:
            max_queue_size: Maximum number of URCs to queue (prevents memory leak)
            log_urcs: Whether to log URCs at INFO level
        """
        self.log_urcs = log_urcs
        self._max_queue_size = max_queue_size

        # Bounded queue for URC storage
        self._urc_queue: Deque[str] = deque(maxlen=max_queue_size)

        # Callback registry: prefix -> callback function
        self._callbacks: Dict[str, URCCallback] = {}

        # Thread safety
        self._lock = threading.Lock()

        logger.info(f"Initialized URC handler (max_queue_size={max_queue_size})")

    def register_callback(self, prefix: str, callback: URCCallback) -> None:
        """
        Register a callback for URCs matching a prefix.

        Args:
            prefix: URC prefix to match (e.g., "+CMTI" for SMS notifications)
            callback: Function to call when URC is received.
                     Signature: callback(line: str) -> None

        Example:

        .. code-block:: python

            handler.register_callback("+CMTI", lambda line: print(f"New SMS: {line}"))
        """
        with self._lock:
            self._callbacks[prefix] = callback
            logger.info(f"Registered URC callback for prefix: {prefix}")

    def unregister_callback(self, prefix: str) -> bool:
        """
        Unregister a URC callback.

        Args:
            prefix: URC prefix to unregister

        Returns:
            True if callback was removed, False if not found
        """
        with self._lock:
            if prefix in self._callbacks:
                del self._callbacks[prefix]
                logger.info(f"Unregistered URC callback for prefix: {prefix}")
                return True
            return False

    def clear_callbacks(self) -> None:
        """Clear all registered callbacks."""
        with self._lock:
            count = len(self._callbacks)
            self._callbacks.clear()
            logger.info(f"Cleared {count} URC callbacks")

    def handle_urc(self, line: str) -> None:
        """
        Process a URC line.

        Adds to queue and dispatches to matching callbacks.

        Args:
            line: URC line to handle
        """
        if self.log_urcs:
            logger.info(f"URC received: {line}")
        else:
            logger.debug(f"URC received: {line}")

        # Add to queue (automatically drops oldest if full)
        with self._lock:
            self._urc_queue.append(line)

        # Dispatch to callbacks
        self._dispatch_callbacks(line)

    def _dispatch_callbacks(self, line: str) -> None:
        """
        Dispatch URC to matching callbacks.

        Args:
            line: URC line to dispatch
        """
        # Get callbacks (outside lock to prevent deadlock if callback is slow)
        with self._lock:
            callbacks_to_call = [
                (prefix, cb) for prefix, cb in self._callbacks.items()
                if line.startswith(prefix)
            ]

        # Call callbacks outside lock
        for prefix, callback in callbacks_to_call:
            try:
                callback(line)
                logger.debug(f"URC callback for '{prefix}' executed successfully")
            except Exception as e:
                logger.error(f"URC callback for '{prefix}' failed: {e}", exc_info=True)

    def get_urc_queue(self) -> list[str]:
        """
        Get a copy of the current URC queue.

        Returns:
            List of URCs in queue (oldest first)
        """
        with self._lock:
            return list(self._urc_queue)

    def pop_urc(self) -> Optional[str]:
        """
        Pop the oldest URC from the queue.

        Returns:
            Oldest URC or None if queue is empty
        """
        with self._lock:
            if self._urc_queue:
                return self._urc_queue.popleft()
            return None

    def clear_queue(self) -> int:
        """
        Clear the URC queue.

        Returns:
            Number of URCs that were cleared
        """
        with self._lock:
            count = len(self._urc_queue)
            self._urc_queue.clear()
            logger.info(f"Cleared {count} URCs from queue")
            return count

    def queue_size(self) -> int:
        """
        Get current queue size.

        Returns:
            Number of URCs in queue
        """
        with self._lock:
            return len(self._urc_queue)

    def get_callbacks(self) -> Dict[str, URCCallback]:
        """
        Get registered callbacks (for debugging).

        Returns:
            Dictionary mapping prefixes to callbacks
        """
        with self._lock:
            return dict(self._callbacks)
