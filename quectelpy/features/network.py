"""
Network manager.

Handles network registration, signal quality, operators, and GPRS operations.
"""

import logging
from typing import TYPE_CHECKING, Optional

from ..types import (
    NetworkInfo,
    SignalQuality,
    CurrentOperator,
    RegistrationStatus
)
from ..parsers.network import (
    NetworkInfoParser,
    SignalQualityParser,
    CurrentOperatorParser,
    RegistrationStatusParser
)
from ..parsers.base import IntValueParser
from ..exceptions import ATParseError, NetworkError

if TYPE_CHECKING:
    from ..core import ModemCore

logger = logging.getLogger(__name__)


class NetworkManager:
    """
    Manages network operations.

    Provides methods for network registration, signal monitoring,
    operator selection, and GPRS attachment.
    """

    def __init__(self, modem_core: "ModemCore") -> None:
        """
        Initialize network manager.

        Args:
            modem_core: ModemCore instance for AT command execution
        """
        self.modem = modem_core

        # Parsers
        self._network_info_parser = NetworkInfoParser()
        self._signal_parser = SignalQualityParser()
        self._operator_parser = CurrentOperatorParser()
        self._reg_status_parser = RegistrationStatusParser()
        self._int_parser = IntValueParser()

        logger.debug("Initialized NetworkManager")

    def get_signal_quality(self) -> SignalQuality:
        """
        Get signal quality.

        Returns:
            SignalQuality with RSSI and BER values

        Example:

        .. code-block:: python

            signal = modem.network.get_signal_quality()
            if signal.is_valid:
                print(f"Signal: {signal.rssi_dbm} dBm")
            else:
                print("No signal")
        """
        logger.info("Getting signal quality")
        response = self.modem.send_at("AT+CSQ", strip_ok=True, remove_cmd_prefix=True)
        signal = self._signal_parser.parse(response)
        logger.debug(f"Signal quality: RSSI={signal.rssi}, BER={signal.ber}")
        return signal

    def get_network_info(self) -> NetworkInfo:
        """
        Get current network information.

        Returns:
            NetworkInfo with RAT, operator, band, and cell ID

        Example:

        .. code-block:: python

            net_info = modem.network.get_network_info()
            print(f"RAT: {net_info.rat}, Band: {net_info.band}")
        """
        logger.info("Getting network info")
        response = self.modem.send_at("AT+QNWINFO", strip_ok=True, remove_cmd_prefix=True)
        net_info = self._network_info_parser.parse(response)
        logger.debug(f"Network info: {net_info}")
        return net_info

    def get_current_operator(self) -> Optional[CurrentOperator]:
        """
        Get current network operator.

        Returns:
            CurrentOperator or None if not registered

        Example:

        .. code-block:: python

            operator = modem.network.get_current_operator()
            if operator:
                print(f"Operator: {operator.oper}")
            else:
                print("Not registered to any operator")
        """
        logger.info("Getting current operator")
        response = self.modem.send_at("AT+COPS?", strip_ok=True, remove_cmd_prefix=True)
        operator = self._operator_parser.parse(response)

        if operator:
            logger.debug(f"Current operator: {operator.oper}")
        else:
            logger.debug("No operator (not registered)")

        return operator

    def get_registration_status(self) -> RegistrationStatus:
        """
        Get network registration status.

        Returns:
            RegistrationStatus with registration state and location info

        Example:

        .. code-block:: python

            reg_status = modem.network.get_registration_status()
            if reg_status.is_registered:
                print(f"Registered: {reg_status.state}")
                if reg_status.lac:
                    print(f"LAC: {reg_status.lac}, CI: {reg_status.ci}")
            else:
                print(f"Not registered: {reg_status.state}")
        """
        logger.info("Getting registration status")
        response = self.modem.send_at("AT+CREG?", strip_ok=True, remove_cmd_prefix=True)
        reg_status = self._reg_status_parser.parse(response)
        logger.debug(f"Registration status: {reg_status}")
        return reg_status

    def get_gprs_registration_status(self) -> RegistrationStatus:
        """
        Get GPRS network registration status.

        Returns:
            RegistrationStatus for GPRS network

        Example:

        .. code-block:: python

            gprs_status = modem.network.get_gprs_registration_status()
            if gprs_status.is_registered:
                print("GPRS registered")
        """
        logger.info("Getting GPRS registration status")
        response = self.modem.send_at("AT+CGREG?", strip_ok=True, remove_cmd_prefix=True)
        gprs_status = self._reg_status_parser.parse(response)
        logger.debug(f"GPRS registration status: {gprs_status}")
        return gprs_status

    def get_gprs_attachment_status(self) -> bool:
        """
        Get GPRS attachment status.

        Returns:
            True if attached to GPRS service, False otherwise

        Example:

        .. code-block:: python

            if modem.network.get_gprs_attachment_status():
                print("Attached to GPRS")
            else:
                print("Not attached to GPRS")
        """
        logger.info("Getting GPRS attachment status")
        response = self.modem.send_at("AT+CGATT?", strip_ok=True, remove_cmd_prefix=True)

        try:
            status = self._int_parser.parse(response)
        except ATParseError as e:
            raise ATParseError(
                "Failed to parse GPRS attachment status",
                command="AT+CGATT?",
                response=response
            ) from e

        attached = bool(status)
        logger.debug(f"GPRS attached: {attached}")
        return attached

    def attach_gprs(self) -> None:
        """
        Attach to GPRS service.

        Raises:
            NetworkError: If attachment fails

        Example:

        .. code-block:: python

            modem.network.attach_gprs()
            print("Attached to GPRS")
        """
        logger.info("Attaching to GPRS service")

        # Check if already attached
        if self.get_gprs_attachment_status():
            logger.info("Already attached to GPRS")
            return

        # Request attachment
        try:
            self.modem.send_at("AT+CGATT=1")
            logger.info("GPRS attachment requested")
        except Exception as e:
            raise NetworkError(
                "Failed to attach to GPRS service",
                command="AT+CGATT=1"
            ) from e

    def detach_gprs(self) -> None:
        """
        Detach from GPRS service.

        Example:

        .. code-block:: python

            modem.network.detach_gprs()
            print("Detached from GPRS")
        """
        logger.info("Detaching from GPRS service")

        # Check if already detached
        if not self.get_gprs_attachment_status():
            logger.info("Already detached from GPRS")
            return

        # Request detachment
        try:
            self.modem.send_at("AT+CGATT=0")
            logger.info("GPRS detachment requested")
        except Exception as e:
            raise NetworkError(
                "Failed to detach from GPRS service",
                command="AT+CGATT=0"
            ) from e

    def wait_for_registration(self, timeout: float = 30.0, check_interval: float = 2.0) -> bool:
        """
        Wait for network registration.

        Args:
            timeout: Maximum time to wait in seconds
            check_interval: Time between checks in seconds

        Returns:
            True if registered, False if timeout

        Example:

        .. code-block:: python

            if modem.network.wait_for_registration(timeout=60):
                print("Registered to network")
            else:
                print("Registration timeout")
        """
        import time

        logger.info(f"Waiting for network registration (timeout={timeout}s)")
        start_time = time.monotonic()

        while time.monotonic() - start_time < timeout:
            try:
                reg_status = self.get_registration_status()
                if reg_status.is_registered:
                    logger.info(f"Registered to network: {reg_status.state}")
                    return True

                logger.debug(f"Not registered yet: {reg_status.state}")
            except Exception as e:
                logger.warning(f"Error checking registration: {e}")

            time.sleep(check_interval)

        logger.warning("Network registration timeout")
        return False
