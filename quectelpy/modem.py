"""
Main QuectelModem class.

User-facing API that coordinates all feature managers.
"""

import logging
from typing import Optional

from .core import ModemCore, SerialTransport, Transport, URCCallback
from .features import DeviceManager, NetworkManager, SMSManager

logger = logging.getLogger(__name__)


class QuectelModem:
    """
    Main interface for Quectel modem control.

    Provides a high-level API for modem operations through feature managers:

    - device: Device information and SIM management
    - network: Network registration, signal quality, operators
    - sms: SMS messaging (basic support; more features planned)

    Example usage with context manager:

    .. code-block:: python

        with QuectelModem(port="/dev/ttyUSB2") as modem:
            # Get device info
            model = modem.device.get_model_info()
            print(f"Model: {model.manufacturer} {model.model}")

            # Check signal
            signal = modem.network.get_signal_quality()
            print(f"Signal: {signal.rssi_dbm} dBm")

            # Register URC callback
            modem.register_urc_callback(
                "+CMTI", lambda line: print(f"New SMS: {line}")
            )

    Example usage with manual lifecycle management:

    .. code-block:: python

        modem = QuectelModem(port="/dev/ttyUSB2")
        modem.start()
        # ... use modem ...
        modem.close()
    """

    def __init__(
        self,
        port: Optional[str] = None,
        transport: Optional[Transport] = None,
        baudrate: int = 115200,
        timeout: float = 1.0,
        log_urcs: bool = False,
        max_urc_queue_size: int = 1000,
        auto_start: bool = False,
        on_disconnect: Optional[callable] = None
    ) -> None:
        """
        Initialize QuectelModem.

        Args:
            port: Serial port path (e.g., "/dev/ttyUSB2"). Either port or transport required.
            transport: Custom transport instance (for testing). Overrides port if provided.
            baudrate: Serial port baud rate (default: 115200)
            timeout: AT command timeout in seconds (default: 1.0)
            log_urcs: Log URCs at INFO level instead of DEBUG (default: False)
            max_urc_queue_size: Maximum URCs to queue (default: 1000)
            auto_start: Automatically start reader thread (default: False)
            on_disconnect: Optional callback function called when device disconnects.
                          Signature: callback(exception: Exception) -> None

        Raises:
            ValueError: If neither port nor transport is provided
            EC25Error: If serial port cannot be opened

        Example:

        .. code-block:: python

            # Using serial port (echo disabled automatically on start)
            modem = QuectelModem(port="/dev/ttyUSB2")

            # Keep echo enabled
            modem = QuectelModem(
                port="/dev/ttyUSB2",
                disable_echo_on_start=False
            )

            # With disconnect callback
            def on_disconnect(error):
                print(f"Modem disconnected: {error}")

            modem = QuectelModem(
                port="/dev/ttyUSB2",
                on_disconnect=on_disconnect
            )

            # Using custom transport (for testing)
            from quectelpy.core import MockTransport
            modem = QuectelModem(transport=MockTransport())
        """
        if transport is None and port is None:
            raise ValueError("Either 'port' or 'transport' must be provided")

        if transport is None:
            transport = SerialTransport(
                port=port,
                baudrate=baudrate,
                timeout=timeout
            )
            logger.info(f"Created serial transport for {port}")

        self._core = ModemCore(
            transport=transport,
            timeout=timeout,
            log_urcs=log_urcs,
            max_urc_queue_size=max_urc_queue_size,
            on_disconnect=on_disconnect
        )

        self.device = DeviceManager(self._core)
        self.network = NetworkManager(self._core)
        self.sms = SMSManager(self._core)

        logger.info("Initialized QuectelModem")

        if auto_start:
            self.start()

    def start(self) -> None:
        """
        Start the modem reader thread.

        Must be called before using the modem (unless auto_start=True or using context manager).

        Example:

        .. code-block:: python

            modem = QuectelModem(port="/dev/ttyUSB2")
            modem.start()
            # ... use modem ...
            modem.close()
        """
        self._core.start()
        logger.info("Modem started")

    def stop(self) -> None:
        """
        Stop the modem reader thread.

        Example:

        .. code-block:: python

            modem.stop()
        """
        self._core.stop()
        logger.info("Modem stopped")

    def close(self) -> None:
        """
        Close the modem connection.

        Stops the reader thread and closes the transport.

        Example:

        .. code-block:: python

            modem.close()
        """
        self._core.close()
        logger.info("Modem closed")

    def register_urc_callback(self, prefix: str, callback: URCCallback) -> None:
        """
        Register a callback for unsolicited result codes.

        Args:
            prefix: URC prefix to match (e.g., "+CMTI" for SMS notifications)
            callback: Function to call when URC is received.
                     Signature: callback(line: str) -> None

        Example:

        .. code-block:: python

            def on_sms(line: str):
                print(f"New SMS notification: {line}")

            modem.register_urc_callback("+CMTI", on_sms)

            # Or with lambda
            modem.register_urc_callback(
                "+CREG",
                lambda line: print(f"Registration change: {line}")
            )
        """
        self._core.register_urc_callback(prefix, callback)

    def unregister_urc_callback(self, prefix: str) -> bool:
        """
        Unregister a URC callback.

        Args:
            prefix: URC prefix to unregister

        Returns:
            True if callback was removed, False if not found

        Example:

        .. code-block:: python

            modem.unregister_urc_callback("+CMTI")
        """
        return self._core.unregister_urc_callback(prefix)

    def send_raw_at(
        self,
        cmd: str,
        strip_ok: bool = False,
        remove_cmd_prefix: bool = False,
        timeout: Optional[float] = None
    ) -> list[str]:
        """
        Send a raw AT command.

        For advanced users who need to send commands not covered by feature managers.

        Args:
            cmd: AT command (e.g., "AT+QGMR" or "+QGMR")
            strip_ok: Remove "OK" from response
            remove_cmd_prefix: Remove command prefix from first response line
            timeout: Command timeout in seconds (uses default if None)

        Returns:
            List of response lines

        Raises:
            ATTimeoutError: If command times out
            EC25Error: If command returns ERROR

        Example:

        .. code-block:: python

            response = modem.send_raw_at("AT+QGMR", strip_ok=True)
            firmware = response[0]
            print(f"Firmware: {firmware}")
        """
        return self._core.send_at(
            cmd=cmd,
            strip_ok=strip_ok,
            remove_cmd_prefix=remove_cmd_prefix,
            timeout=timeout
        )

    @property
    def is_running(self) -> bool:
        """
        Check if the modem reader thread is running.

        Returns:
            True if running, False otherwise
        """
        return self._core.is_running()

    @property
    def is_disconnected(self) -> bool:
        """
        Check if the device was disconnected.

        Returns:
            True if device disconnected, False otherwise

        Example:

        .. code-block:: python

            if modem.is_disconnected:
                print("Device was disconnected!")
                # Reconnect or handle error
        """
        return self._core.is_disconnected()

    def __enter__(self):
        """
        Context manager entry.

        Automatically starts the modem if not already running.
        """
        if not self.is_running:
            self.start()
        return self

    def __exit__(self, *exc):
        """
        Context manager exit.

        Automatically closes the modem connection.
        """
        self.close()

    def __repr__(self) -> str:
        """String representation of modem."""
        status = "running" if self.is_running else "stopped"
        return f"<QuectelModem status={status}>"

