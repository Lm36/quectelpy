"""
Network-specific response parsers.

Parses responses for network, signal, and registration commands.
"""

import logging
from typing import Optional

from .base import ResponseParser
from ..types import (
    NetworkInfo,
    SignalQuality,
    CurrentOperator,
    RegistrationStatus,
    ModelInfo
)
from ..exceptions import ATParseError

logger = logging.getLogger(__name__)


class ModelInfoParser(ResponseParser[ModelInfo]):
    """Parser for ATI (model info) response."""

    def parse(self, response: list[str]) -> ModelInfo:
        """
        Parse ATI response.

        Expected format:
            Quectel
            EC25
            Revision: EC25EFAR06A03M4G
        """
        if len(response) != 3:
            raise ATParseError(
                f"Expected 3 lines for model info, got {len(response)}",
                command="ATI",
                response=response
            )

        manufacturer = response[0]
        model = response[1]
        revision = response[2].replace("Revision:", "").strip()

        return ModelInfo(
            manufacturer=manufacturer,
            model=model,
            revision=revision
        )


class SignalQualityParser(ResponseParser[SignalQuality]):
    """Parser for AT+CSQ (signal quality) response."""

    def parse(self, response: list[str]) -> SignalQuality:
        """
        Parse AT+CSQ response.

        Expected format: "+CSQ: 24,99"
        """
        if not response:
            raise ATParseError(
                "Empty signal quality response",
                command="AT+CSQ",
                response=response
            )

        try:
            rssi_str, ber_str = response[0].split(",")
            return SignalQuality(rssi=int(rssi_str), ber=int(ber_str))
        except (ValueError, IndexError) as e:
            raise ATParseError(
                f"Failed to parse signal quality: {response[0]}",
                command="AT+CSQ",
                response=response
            ) from e


class NetworkInfoParser(ResponseParser[NetworkInfo]):
    """Parser for AT+QNWINFO (network info) response."""

    def parse(self, response: list[str]) -> NetworkInfo:
        """
        Parse AT+QNWINFO response.

        Expected format: '"LTE","310410","LTE BAND 4",5110'
        """
        if not response:
            raise ATParseError(
                "Empty network info response",
                command="AT+QNWINFO",
                response=response
            )

        parts = [p.strip().strip('"') for p in response[0].split(",")]

        if len(parts) != 4:
            raise ATParseError(
                f"Expected 4 parts in network info, got {len(parts)}",
                command="AT+QNWINFO",
                response=response
            )

        rat, operator, band, cell_id_str = parts

        try:
            cell_id = int(cell_id_str)
        except ValueError as e:
            raise ATParseError(
                f"Invalid cell_id in network info: {cell_id_str}",
                command="AT+QNWINFO",
                response=response
            ) from e

        return NetworkInfo(
            rat=rat,
            operator=operator,
            band=band,
            cell_id=cell_id
        )


class CurrentOperatorParser(ResponseParser[Optional[CurrentOperator]]):
    """Parser for AT+COPS? (current operator) response."""

    def parse(self, response: list[str]) -> Optional[CurrentOperator]:
        """
        Parse AT+COPS? response.

        Expected format: "0,0,\"AT&T\",7"
        Returns None if response is "0" (no operator)
        """
        if not response:
            raise ATParseError(
                "Empty operator response",
                command="AT+COPS?",
                response=response
            )

        # Check for "not registered" response
        if response[0] == '0':
            return None

        try:
            mode_str, format_str, oper, act_str = response[0].split(',', 3)
            return CurrentOperator(
                mode=int(mode_str),
                format=int(format_str),
                oper=oper.strip('"'),
                act=int(act_str)
            )
        except (ValueError, IndexError) as e:
            raise ATParseError(
                f"Failed to parse operator info: {response[0]}",
                command="AT+COPS?",
                response=response
            ) from e


class RegistrationStatusParser(ResponseParser[RegistrationStatus]):
    """Parser for AT+CREG?/AT+CGREG? (registration status) response."""

    def parse(self, response: list[str]) -> RegistrationStatus:
        """
        Parse AT+CREG?/AT+CGREG? response.

        Expected formats:
            "0,1"               (minimal)
            "2,1,\"1234\",\"5678\"" (with location)
            "2,1,\"1234\",\"5678\",7" (with location and act)
        """
        if not response:
            raise ATParseError(
                "Empty registration status response",
                command="AT+CREG?",
                response=response
            )

        try:
            parts = response[0].split(",")

            n = int(parts[0])
            stat = int(parts[1])
            lac = parts[2].strip('"') if len(parts) > 2 else None
            ci = parts[3].strip('"') if len(parts) > 3 else None
            act = int(parts[4]) if len(parts) > 4 else None

            return RegistrationStatus(
                n=n,
                stat=stat,
                lac=lac,
                ci=ci,
                act=act
            )
        except (ValueError, IndexError) as e:
            raise ATParseError(
                f"Failed to parse registration status: {response[0]}",
                command="AT+CREG?",
                response=response
            ) from e
