"""
SMS manager.

Handles SMS messaging operations (send, receive, storage).
Supports both text mode and PDU mode for maximum compatibility.
"""

import logging
from typing import TYPE_CHECKING, Optional
import time

from ..types import MessageFormat, SMSMessage, SMSStatus, SMSStorage
from ..parsers.base import IntValueParser
from ..parsers.sms import SMSParser
from ..parsers.pdu import encode_sms_submit, calculate_sms_parts, PDUError
from ..exceptions import ATParseError, SMSError

if TYPE_CHECKING:
    from ..core import ModemCore

logger = logging.getLogger(__name__)


class SMSManager:
    """
    Manages SMS messaging operations.

    Features:
    - Send SMS (text and PDU modes)
    - Read SMS by index
    - List messages by status
    - Delete messages
    - SMS storage management
    - Automatic encoding detection
    - Support for long messages (concatenated SMS)
    """

    def __init__(self, modem_core: "ModemCore") -> None:
        """
        Initialize SMS manager.

        Args:
            modem_core: ModemCore instance for AT command execution
        """
        self.modem = modem_core
        self._int_parser = IntValueParser()
        self._sms_parser = SMSParser()
        self._cached_format: Optional[MessageFormat] = None

        logger.debug("Initialized SMSManager")

    def get_message_format(self, use_cache: bool = True) -> MessageFormat:
        """
        Get current SMS message format mode.

        Args:
            use_cache: If True, return cached value if available (default: True)

        Returns:
            MessageFormat.PDU_MODE (0) or MessageFormat.TEXT_MODE (1)

        Example:

        .. code-block:: python

            format_mode = modem.sms.get_message_format()
            if format_mode == MessageFormat.TEXT_MODE:
                print("Using text mode")
        """
        # Return cached value if available and requested
        if use_cache and self._cached_format is not None:
            logger.debug(f"Using cached message format: {self._cached_format}")
            return self._cached_format

        logger.info("Getting message format")
        response = self.modem.send_at("AT+CMGF?", strip_ok=True, remove_cmd_prefix=True)

        try:
            mode = self._int_parser.parse(response)
            message_format = MessageFormat(mode)
        except (ValueError, ATParseError) as e:
            raise ATParseError(
                "Failed to parse message format",
                command="AT+CMGF?",
                response=response
            ) from e

        logger.debug(f"Message format: {message_format}")

        # Cache the result
        self._cached_format = message_format

        return message_format

    def set_message_format(self, mode: MessageFormat) -> None:
        """
        Set SMS message format mode.

        Args:
            mode: MessageFormat.PDU_MODE (0) or MessageFormat.TEXT_MODE (1)

        Example:

        .. code-block:: python

            # Set to text mode for easier SMS sending
            modem.sms.set_message_format(MessageFormat.TEXT_MODE)
        """
        logger.info(f"Setting message format to {mode}")

        # Check current mode
        current_mode = self.get_message_format()
        if current_mode == mode:
            logger.debug("Message format already set to desired mode")
            return

        # Set new mode
        cmd = f"AT+CMGF={mode.value}"
        self.modem.send_at(cmd)

        # Update cache
        self._cached_format = mode

        logger.info(f"Message format changed: {current_mode} -> {mode}")

    def send_sms(
        self,
        number: str,
        message: str,
        encoding: str = "auto",
        request_status: bool = False
    ) -> int:
        """
        Send an SMS message using PDU mode.

        PDU mode is used for maximum compatibility and to support:
        - Unicode characters (via UCS2)
        - Long messages (automatic concatenation)
        - Delivery reports

        Args:
            number: Recipient phone number (with or without +)
            message: Message text
            encoding: "gsm7", "ucs2", or "auto" (default)
            request_status: Request delivery status report

        Returns:
            Message reference number

        Raises:
            SMSError: If sending fails

        Example:

        .. code-block:: python

            # Send simple SMS
            ref = modem.sms.send_sms("+1234567890", "Hello!")

            # Send with Unicode
            ref = modem.sms.send_sms("+1234567890", "Hello 世界!", encoding="ucs2")

            # Request delivery report
            ref = modem.sms.send_sms("+1234567890", "Important", request_status=True)
        """
        logger.info(f"Sending SMS to {number}")

        # Calculate SMS parts
        parts = calculate_sms_parts(message, encoding)
        logger.debug(f"Message will be sent as {parts} part(s)")

        if parts > 1:
            logger.warning("Concatenated SMS (multi-part) not fully implemented")
            logger.warning("Only first 160 chars (GSM7) or 70 chars (UCS2) will be sent")

        # Ensure we're in PDU mode
        self.set_message_format(MessageFormat.PDU_MODE)

        try:
            # Encode message to PDU
            pdu = encode_sms_submit(
                number=number,
                text=message,
                encoding=encoding,
                request_status=request_status
            )

            # Calculate PDU length (excluding SMSC)
            # First byte is SMSC length (00 = use default)
            pdu_length = (len(pdu) // 2) - 1

            # Send AT+CMGS command
            cmd = f"AT+CMGS={pdu_length}"
            logger.debug(f"Sending: {cmd}")

            # Write command and wait for prompt
            self.modem.transport.write((cmd + "\r\n").encode())
            time.sleep(0.1)

            # Wait for "> " prompt
            prompt = self.modem.transport.read_until(b"> ", timeout=5.0)
            if b">" not in prompt:
                raise SMSError(
                    "Did not receive SMS prompt",
                    command=cmd,
                    response=[prompt.decode('utf-8', errors='ignore')]
                )

            # Send PDU followed by Ctrl+Z
            pdu_with_terminator = pdu + "\x1A"
            self.modem.transport.write(pdu_with_terminator.encode())

            # Wait for response (can take several seconds)
            # Read lines until we get a final response
            response_lines = []
            start_time = time.time()
            timeout = 30.0  # SMS can take a while

            while time.time() - start_time < timeout:
                try:
                    line_bytes = self.modem.transport.read_until(b"\r\n", timeout=1.0)
                    if not line_bytes:
                        continue

                    line = line_bytes.decode("utf-8", errors="ignore").strip()
                    if not line:
                        continue

                    response_lines.append(line)
                    logger.debug(f"SMS response: {line}")

                    # Check for final response
                    if line == "OK":
                        break
                    elif "ERROR" in line or "+CMS ERROR" in line:
                        raise SMSError(
                            f"SMS send failed: {line}",
                            command=cmd,
                            response=response_lines
                        )

                except Exception as e:
                    if isinstance(e, SMSError):
                        raise
                    # Continue waiting
                    continue

            # Parse message reference from response
            try:
                ref = self._sms_parser.parse_cmgs(response_lines)
                logger.info(f"SMS sent successfully, reference: {ref}")
                return ref
            except ValueError as e:
                # Even if we can't parse reference, if we got OK, it was sent
                if "OK" in response_lines:
                    logger.warning(f"SMS sent but could not parse reference: {e}")
                    return -1
                raise SMSError(
                    f"Failed to parse SMS response: {e}",
                    command=cmd,
                    response=response_lines
                ) from e

        except PDUError as e:
            raise SMSError(f"PDU encoding failed: {e}") from e
        except Exception as e:
            if isinstance(e, SMSError):
                raise
            raise SMSError(f"SMS send failed: {e}") from e

    def read_sms(self, index: int) -> SMSMessage:
        """
        Read SMS message by index.

        Uses current message format mode (PDU or text).

        Args:
            index: Message index in storage

        Returns:
            SMSMessage object

        Raises:
            SMSError: If reading fails or message doesn't exist

        Example:

        .. code-block:: python

            message = modem.sms.read_sms(5)
            print(f"From: {message.sender}")
            print(f"Text: {message.content}")
        """
        logger.info(f"Reading SMS at index {index}")

        try:
            # Send read command
            cmd = f"AT+CMGR={index}"
            response = self.modem.send_at(cmd, strip_ok=True)

            if not response:
                raise SMSError(
                    f"No message at index {index}",
                    command=cmd,
                    response=response
                )

            # Parse based on current format
            mode = self.get_message_format()

            if mode == MessageFormat.TEXT_MODE:
                message = self._sms_parser.parse_cmgr_text(response)
                message.index = index
            else:
                message = self._sms_parser.parse_cmgr_pdu(response, index)

            logger.info(f"Read SMS from {message.sender}")
            return message

        except ValueError as e:
            raise SMSError(
                f"Failed to parse SMS: {e}",
                command=f"AT+CMGR={index}",
                response=[]
            ) from e

    def list_messages(self, status: SMSStatus = SMSStatus.ALL) -> list[SMSMessage]:
        """
        List SMS messages by status.

        Uses current message format mode (PDU or text).

        Args:
            status: Message status filter (default: ALL)

        Returns:
            List of SMSMessage objects

        Example:

        .. code-block:: python

            # List all unread messages
            unread = modem.sms.list_messages(SMSStatus.REC_UNREAD)
            for msg in unread:
                print(f"{msg.sender}: {msg.content}")

            # List all messages
            all_messages = modem.sms.list_messages(SMSStatus.ALL)
        """
        logger.info(f"Listing messages with status: {status.value}")

        try:
            # Build command
            cmd = f'AT+CMGL="{status.value}"'
            response = self.modem.send_at(cmd, strip_ok=True)

            if not response or (len(response) == 1 and not response[0]):
                logger.info("No messages found")
                return []

            # Parse based on current format
            mode = self.get_message_format()

            if mode == MessageFormat.TEXT_MODE:
                messages = self._sms_parser.parse_cmgl_text(response)
            else:
                messages = self._sms_parser.parse_cmgl_pdu(response)

            logger.info(f"Found {len(messages)} message(s)")
            return messages

        except ValueError as e:
            raise SMSError(
                f"Failed to parse message list: {e}",
                command=cmd,
                response=[]
            ) from e

    def delete_message(self, index: int) -> None:
        """
        Delete SMS message by index.

        Args:
            index: Message index to delete

        Raises:
            SMSError: If deletion fails

        Example:

        .. code-block:: python

            modem.sms.delete_message(5)
        """
        logger.info(f"Deleting message at index {index}")

        try:
            cmd = f"AT+CMGD={index}"
            self.modem.send_at(cmd)
            logger.info(f"Deleted message {index}")

        except Exception as e:
            raise SMSError(
                f"Failed to delete message {index}: {e}",
                command=cmd
            ) from e

    def delete_all_messages(self, status: Optional[SMSStatus] = None) -> None:
        """
        Delete all messages, optionally filtered by status.

        Args:
            status: Optional status filter (None = delete all)

        Raises:
            SMSError: If deletion fails

        Example:

        .. code-block:: python

            # Delete all read messages
            modem.sms.delete_all_messages(SMSStatus.REC_READ)

            # Delete ALL messages (use with caution!)
            modem.sms.delete_all_messages()
        """
        if status:
            logger.info(f"Deleting all messages with status: {status.value}")
            # Delete by status - use flag 1,2,3,4
            status_map = {
                SMSStatus.REC_READ: 1,
                SMSStatus.REC_UNREAD: 2,
                SMSStatus.STO_SENT: 3,
                SMSStatus.STO_UNSENT: 4,
            }
            flag = status_map.get(status, 1)
            cmd = f"AT+CMGD=1,{flag}"
        else:
            logger.warning("Deleting ALL messages")
            # Delete all messages - use flag 4
            cmd = "AT+CMGD=1,4"

        try:
            self.modem.send_at(cmd)
            logger.info("Messages deleted successfully")

        except Exception as e:
            raise SMSError(
                f"Failed to delete messages: {e}",
                command=cmd
            ) from e

    def get_storage_info(self) -> tuple[SMSStorage, SMSStorage, SMSStorage]:
        """
        Get SMS storage information.

        Returns:
            Tuple of (read_storage, write_storage, receive_storage)
            Each SMSStorage contains: storage_type, used, total

        Example:

        .. code-block:: python

            read, write, receive = modem.sms.get_storage_info()
            print(f"Used: {read.used}/{read.total} on {read.storage_type}")
        """
        logger.info("Getting storage info")

        try:
            response = self.modem.send_at("AT+CPMS?", strip_ok=True)
            storages = self._sms_parser.parse_cpms(response)
            logger.info(f"Storage: {storages[0].used}/{storages[0].total}")
            return storages

        except ValueError as e:
            raise SMSError(
                f"Failed to parse storage info: {e}",
                command="AT+CPMS?",
                response=[]
            ) from e

    def set_preferred_storage(
        self,
        mem1: str = "ME",
        mem2: str = "ME",
        mem3: str = "ME"
    ) -> None:
        """
        Set preferred message storage.

        Args:
            mem1: Storage for reading/deleting (default: ME)
            mem2: Storage for writing/sending (default: ME)
            mem3: Storage for receiving (default: ME)

        Common storage types:
        - "ME": Mobile Equipment (internal memory)
        - "SM": SIM card
        - "MT": Mobile Equipment + SIM (reads from both)

        Example:

        .. code-block:: python

            # Store everything in SIM
            modem.sms.set_preferred_storage("SM", "SM", "SM")

            # Read from both, write to ME
            modem.sms.set_preferred_storage("MT", "ME", "ME")
        """
        logger.info(f"Setting storage: {mem1},{mem2},{mem3}")

        try:
            cmd = f'AT+CPMS="{mem1}","{mem2}","{mem3}"'
            self.modem.send_at(cmd)
            logger.info("Storage preference updated")

        except Exception as e:
            raise SMSError(
                f"Failed to set storage: {e}",
                command=cmd
            ) from e

    def get_storage_locations(self) -> list[str]:
        """
        Get list of available storage locations.

        Returns:
            List of storage location codes (e.g., ["ME", "SM", "MT"])

        Example:

        .. code-block:: python

            locations = modem.sms.get_storage_locations()
            print(f"Available storage: {', '.join(locations)}")
        """
        logger.info("Getting available storage locations")

        try:
            # AT+CPMS=? returns supported storage types
            response = self.modem.send_at("AT+CPMS=?", strip_ok=True)

            # Parse response: +CPMS: ("ME","SM","MT"),("ME","SM","MT"),("ME","SM","MT")
            if not response:
                return []

            line = response[0]
            # Extract first set of storage types
            import re
            match = re.search(r'\(([^)]+)\)', line)
            if not match:
                return []

            # Parse storage types
            types_str = match.group(1)
            storage_types = [s.strip('"') for s in types_str.split(',')]

            logger.info(f"Available storage locations: {storage_types}")
            return storage_types

        except Exception as e:
            logger.warning(f"Failed to get storage locations: {e}")
            # Return common defaults
            return ["ME", "SM", "MT"]
