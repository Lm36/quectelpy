"""
Device information manager.

Handles device-related operations: IMEI, model info, firmware, SIM state, etc.
"""

import logging
from typing import TYPE_CHECKING

from ..types import ModelInfo, SIMState, EquipmentStatus
from ..parsers.network import ModelInfoParser
from ..parsers.base import SimpleValueParser, IntValueParser
from ..exceptions import ATParseError, SIMError

if TYPE_CHECKING:
    from ..core import ModemCore

logger = logging.getLogger(__name__)


class DeviceManager:
    """
    Manages device information and status.

    Provides methods for querying device identity, firmware, and SIM state.
    """

    def __init__(self, modem_core: "ModemCore") -> None:
        """
        Initialize device manager.

        Args:
            modem_core: ModemCore instance for AT command execution
        """
        self.modem = modem_core

        # Parsers
        self._model_parser = ModelInfoParser()
        self._simple_parser = SimpleValueParser()
        self._int_parser = IntValueParser()

        logger.debug("Initialized DeviceManager")

    def get_model_info(self) -> ModelInfo:
        """
        Get modem model information.

        Returns:
            ModelInfo with manufacturer, model, and revision

        Example:

        .. code-block:: python

            model = modem.device.get_model_info()
            print(f"{model.manufacturer} {model.model} {model.revision}")
        """
        logger.info("Getting model info")
        response = self.modem.send_at("ATI", strip_ok=True)
        model_info = self._model_parser.parse(response)
        logger.debug(f"Model info: {model_info}")
        return model_info

    def get_imei(self) -> str:
        """
        Get device IMEI (International Mobile Equipment Identity).

        Returns:
            15-digit IMEI string

        Example:

        .. code-block:: python

            imei = modem.device.get_imei()
            print(f"IMEI: {imei}")
        """
        logger.info("Getting IMEI")
        response = self.modem.send_at("AT+GSN", strip_ok=True, remove_cmd_prefix=True)
        imei = self._simple_parser.parse(response)
        logger.debug(f"IMEI: {imei}")
        return imei

    def get_firmware_version(self) -> str:
        """
        Get device firmware version.

        Returns:
            Firmware version string

        Example:

        .. code-block:: python

            firmware = modem.device.get_firmware_version()
            print(f"Firmware: {firmware}")
        """
        logger.info("Getting firmware version")
        response = self.modem.send_at("AT+QGMR", strip_ok=True)
        firmware = self._simple_parser.parse(response)
        logger.debug(f"Firmware: {firmware}")
        return firmware

    def get_sim_state(self) -> SIMState:
        """
        Get SIM card state.

        Returns:
            SIMState enum value

        Raises:
            SIMError: If SIM is not ready (PIN required, PUK required, etc.)

        Example:

        .. code-block:: python

            sim_state = modem.device.get_sim_state()
            if sim_state == SIMState.READY:
                print("SIM is ready")
            elif sim_state == SIMState.SIM_PIN:
                print("SIM PIN required")
        """
        logger.info("Getting SIM state")
        response = self.modem.send_at("AT+CPIN?", strip_ok=True, remove_cmd_prefix=True)
        state_str = self._simple_parser.parse(response)

        try:
            sim_state = SIMState(state_str)
        except ValueError:
            logger.warning(f"Unknown SIM state: {state_str}")
            # Return the raw value if not in enum
            return SIMState.NOT_INSERTED

        logger.debug(f"SIM state: {sim_state}")

        # Raise error if SIM is not ready
        if sim_state != SIMState.READY:
            raise SIMError(
                f"SIM not ready: {sim_state.value}",
                command="AT+CPIN?",
                response=response
            )

        return sim_state

    def get_equipment_status(self) -> EquipmentStatus:
        """
        Get mobile equipment activity status.

        Returns:
            EquipmentStatus enum value

        Example:

        .. code-block:: python

            status = modem.device.get_equipment_status()
            if status == EquipmentStatus.READY:
                print("Equipment is ready")
        """
        logger.info("Getting equipment status")
        response = self.modem.send_at("AT+CPAS", strip_ok=True, remove_cmd_prefix=True)

        try:
            status_code = self._int_parser.parse(response)
            status = EquipmentStatus(status_code)
        except (ValueError, ATParseError) as e:
            raise ATParseError(
                "Failed to parse equipment status",
                command="AT+CPAS",
                response=response
            ) from e

        logger.debug(f"Equipment status: {status}")
        return status

    def change_imei(self, new_imei: str) -> str:
        """
        Change device IMEI.

        **WARNING**: Changing IMEI may be illegal in your jurisdiction.
        This function is provided for testing and development purposes only.
        Use at your own risk.

        Args:
            new_imei: New 15-digit IMEI

        Returns:
            New IMEI after change

        Raises:
            EC25Error: If IMEI change fails

        Example:

        .. code-block:: python

            # Generate valid IMEI at: https://www.imei.info/
            new_imei = modem.device.change_imei("123456789012345")
        """
        logger.warning(f"Attempting to change IMEI to {new_imei}")

        current_imei = self.get_imei()

        if new_imei == current_imei:
            logger.info("IMEI already matches, skipping change")
            return new_imei

        # command not in quectel manual
        cmd = f'AT+EGMR=1,7,"{new_imei}"'
        self.modem.send_at(cmd)

        updated_imei = self.get_imei()

        if updated_imei != new_imei:
            raise ATParseError(
                f"IMEI change failed. Expected {new_imei}, got {updated_imei}",
                command=cmd
            )

        logger.info(f"IMEI changed successfully: {current_imei} -> {updated_imei}")
        return updated_imei

    def set_echo_mode(self, enabled: bool) -> None:
        """
        Set AT command echo mode on the device.

        Args:
            enabled: True to enable echo (ATE1), False to disable (ATE0)

        Example:

        .. code-block:: python

            modem.device.set_echo_mode(False)  # Disable echo for clean responses
            modem.device.set_echo_mode(True)   # Enable echo for debugging
        """
        cmd = "ATE1" if enabled else "ATE0"
        logger.info(f"Setting echo mode: {'ON' if enabled else 'OFF'} via {cmd}")
        self.modem.send_at(cmd)
