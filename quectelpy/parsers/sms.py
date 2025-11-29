"""
SMS response parsers for AT commands.

Parses responses from SMS-related AT commands like:
- AT+CMGL (List messages)
- AT+CMGR (Read message)
- AT+CPMS (Preferred message storage)
- +CMTI URC (New message indication)
"""

import re
from ..types import SMSMessage, SMSStorage
from .pdu import decode_sms_deliver


class SMSParser:
    """Parser for SMS-related AT command responses."""

    @staticmethod
    def parse_cmgr_text(response: list[str]) -> SMSMessage:
        """
        Parse AT+CMGR response in text mode.

        Expected format:
            +CMGR: "REC READ","+1234567890",,"23/01/15,10:30:45+00"
            Message content here

        Args:
            response: Response lines from AT+CMGR

        Returns:
            SMSMessage object

        Raises:
            ValueError: If response format is invalid
        """
        if len(response) < 2:
            raise ValueError(f"Invalid CMGR response: expected 2+ lines, got {len(response)}")

        # Parse header line
        header = response[0]
        if not header.startswith("+CMGR:"):
            raise ValueError(f"Invalid CMGR header: {header}")

        # Extract fields using regex
        # +CMGR: "status","sender","alpha","timestamp" OR
        # +CMGR: "status","sender",,"timestamp" (empty alpha)
        match = re.match(
            r'\+CMGR:\s*"([^"]+)","([^"]+)",(?:"[^"]*",|,)"([^"]+)"',
            header
        )

        if not match:
            raise ValueError(f"Could not parse CMGR header: {header}")

        status = match.group(1)
        sender = match.group(2)
        timestamp = match.group(3)

        # Message content is everything after header
        content = "\n".join(response[1:])

        return SMSMessage(
            index=-1,  # Index not provided in CMGR response
            status=status,
            sender=sender,
            timestamp=timestamp,
            content=content,
            encoding="text",
            storage=None,
            pdu=None
        )

    @staticmethod
    def parse_cmgr_pdu(response: list[str], index: int) -> SMSMessage:
        """
        Parse AT+CMGR response in PDU mode.

        Expected format:
            +CMGR: 0,,24
            07911234567890F0040B911234567890F00000230115103045800548656C6C6F

        Args:
            response: Response lines from AT+CMGR
            index: Message index

        Returns:
            SMSMessage object

        Raises:
            ValueError: If response format is invalid
        """
        if len(response) < 2:
            raise ValueError(f"Invalid CMGR PDU response: expected 2 lines, got {len(response)}")

        # Parse header line
        header = response[0]
        if not header.startswith("+CMGR:"):
            raise ValueError(f"Invalid CMGR header: {header}")

        # Extract status and length
        # +CMGR: <stat>,,<length>
        match = re.match(r'\+CMGR:\s*(\d+),,(\d+)', header)
        if not match:
            raise ValueError(f"Could not parse CMGR PDU header: {header}")

        stat = int(match.group(1))
        length = int(match.group(2))

        # PDU data
        pdu = response[1].strip()

        # Decode PDU
        try:
            decoded = decode_sms_deliver(pdu)
        except Exception as e:
            raise ValueError(f"Failed to decode PDU: {e}") from e

        # Map status code to text
        status_map = {
            0: "REC UNREAD",
            1: "REC READ",
            2: "STO UNSENT",
            3: "STO SENT"
        }
        status = status_map.get(stat, f"UNKNOWN ({stat})")

        return SMSMessage(
            index=index,
            status=status,
            sender=decoded["sender"],
            timestamp=decoded["timestamp"],
            content=decoded["text"],
            encoding=decoded["encoding"],
            storage=None,
            pdu=pdu
        )

    @staticmethod
    def parse_cmgl_text(response: list[str]) -> list[SMSMessage]:
        """
        Parse AT+CMGL response in text mode.

        Expected format (multiple messages):
            +CMGL: 1,"REC READ","+1234567890",,"23/01/15,10:30:45+00"
            Message 1 content
            +CMGL: 2,"REC UNREAD","+0987654321",,"23/01/15,11:45:30+00"
            Message 2 content

        Args:
            response: Response lines from AT+CMGL

        Returns:
            List of SMSMessage objects
        """
        messages = []
        i = 0

        while i < len(response):
            line = response[i]

            # Check if this is a message header
            if line.startswith("+CMGL:"):
                # Parse header
                # +CMGL: <index>,"status","sender","alpha","timestamp" OR
                # +CMGL: <index>,"status","sender",,"timestamp" (empty alpha)
                match = re.match(
                    r'\+CMGL:\s*(\d+),"([^"]+)","([^"]+)",(?:"[^"]*",|,)"([^"]+)"',
                    line
                )

                if not match:
                    i += 1
                    continue

                index = int(match.group(1))
                status = match.group(2)
                sender = match.group(3)
                timestamp = match.group(4)

                # Content is on next line(s) until next header or end
                i += 1
                content_lines = []

                while i < len(response):
                    if response[i].startswith("+CMGL:"):
                        break
                    content_lines.append(response[i])
                    i += 1

                content = "\n".join(content_lines).strip()

                messages.append(SMSMessage(
                    index=index,
                    status=status,
                    sender=sender,
                    timestamp=timestamp,
                    content=content,
                    encoding="text",
                    storage=None,
                    pdu=None
                ))
            else:
                i += 1

        return messages

    @staticmethod
    def parse_cmgl_pdu(response: list[str]) -> list[SMSMessage]:
        """
        Parse AT+CMGL response in PDU mode.

        Expected format (multiple messages):
            +CMGL: 1,0,,24
            07911234567890F0040B911234567890F00000230115103045800548656C6C6F
            +CMGL: 2,1,,26
            07911234567890F0040B910987654321F00000230115114530800648692074686572

        Args:
            response: Response lines from AT+CMGL

        Returns:
            List of SMSMessage objects
        """
        messages = []
        i = 0

        while i < len(response):
            line = response[i]

            # Check if this is a message header
            if line.startswith("+CMGL:"):
                # Parse header
                # +CMGL: <index>,<stat>,,<length>
                match = re.match(r'\+CMGL:\s*(\d+),(\d+),,(\d+)', line)

                if not match:
                    i += 1
                    continue

                index = int(match.group(1))
                stat = int(match.group(2))
                length = int(match.group(3))

                # PDU data is on next line
                i += 1
                if i >= len(response):
                    break

                pdu = response[i].strip()

                # Decode PDU
                try:
                    decoded = decode_sms_deliver(pdu)

                    # Map status code to text
                    status_map = {
                        0: "REC UNREAD",
                        1: "REC READ",
                        2: "STO UNSENT",
                        3: "STO SENT"
                    }
                    status = status_map.get(stat, f"UNKNOWN ({stat})")

                    messages.append(SMSMessage(
                        index=index,
                        status=status,
                        sender=decoded["sender"],
                        timestamp=decoded["timestamp"],
                        content=decoded["text"],
                        encoding=decoded["encoding"],
                        storage=None,
                        pdu=pdu
                    ))
                except Exception:
                    # Skip malformed PDU
                    pass

                i += 1
            else:
                i += 1

        return messages

    @staticmethod
    def parse_cpms(response: list[str]) -> tuple[SMSStorage, SMSStorage, SMSStorage]:
        """
        Parse AT+CPMS? response (preferred message storage).

        Expected format:
            +CPMS: "ME",10,100,"ME",10,100,"ME",10,100

        Args:
            response: Response lines from AT+CPMS?

        Returns:
            Tuple of (read_storage, write_storage, receive_storage)

        Raises:
            ValueError: If response format is invalid
        """
        if not response:
            raise ValueError("Empty CPMS response")

        line = response[0]
        if not line.startswith("+CPMS:"):
            raise ValueError(f"Invalid CPMS response: {line}")

        # Parse response
        # +CPMS: "mem1",used1,total1,"mem2",used2,total2,"mem3",used3,total3
        match = re.match(
            r'\+CPMS:\s*"([^"]+)",(\d+),(\d+),"([^"]+)",(\d+),(\d+),"([^"]+)",(\d+),(\d+)',
            line
        )

        if not match:
            raise ValueError(f"Could not parse CPMS response: {line}")

        # Extract storage info
        read_storage = SMSStorage(
            storage_type=match.group(1),
            used=int(match.group(2)),
            total=int(match.group(3))
        )

        write_storage = SMSStorage(
            storage_type=match.group(4),
            used=int(match.group(5)),
            total=int(match.group(6))
        )

        receive_storage = SMSStorage(
            storage_type=match.group(7),
            used=int(match.group(8)),
            total=int(match.group(9))
        )

        return read_storage, write_storage, receive_storage

    @staticmethod
    def parse_cmti(urc: str) -> tuple[str, int]:
        """
        Parse +CMTI URC (new message indication).

        Expected format:
            +CMTI: "ME",5

        Args:
            urc: URC line

        Returns:
            Tuple of (storage, index)

        Raises:
            ValueError: If URC format is invalid
        """
        if not urc.startswith("+CMTI:"):
            raise ValueError(f"Not a +CMTI URC: {urc}")

        # Parse URC
        # +CMTI: "storage",index
        match = re.match(r'\+CMTI:\s*"([^"]+)",(\d+)', urc)

        if not match:
            raise ValueError(f"Could not parse +CMTI URC: {urc}")

        storage = match.group(1)
        index = int(match.group(2))

        return storage, index

    @staticmethod
    def parse_cmgs(response: list[str]) -> int:
        """
        Parse AT+CMGS response (send message).

        Expected format:
            +CMGS: 123

        Where 123 is the message reference number.

        Args:
            response: Response lines from AT+CMGS

        Returns:
            Message reference number

        Raises:
            ValueError: If response format is invalid
        """
        if not response:
            raise ValueError("Empty CMGS response")

        line = response[0]
        if not line.startswith("+CMGS:"):
            raise ValueError(f"Invalid CMGS response: {line}")

        # Parse response
        match = re.match(r'\+CMGS:\s*(\d+)', line)

        if not match:
            raise ValueError(f"Could not parse CMGS response: {line}")

        return int(match.group(1))
