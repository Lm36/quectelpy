"""
PDU encoding and decoding for SMS messages.

Implements GSM 03.40 specification for SMS PDU format.
Supports:
- 7-bit GSM alphabet (160 chars)
- UCS2 Unicode (70 chars)
- Concatenated SMS (long messages)
- Flash SMS
- Validity period
- Status reports
"""

import re
from typing import Optional, Tuple
from datetime import datetime


# GSM 7-bit default alphabet
GSM7_BASIC = (
    "@£$¥èéùìòÇ\nØø\rÅåΔ_ΦΓΛΩΠΨΣΘΞ\x1bÆæßÉ !\"#¤%&'()*+,-./0123456789:;<=>?"
    "¡ABCDEFGHIJKLMNOPQRSTUVWXYZÄÖÑÜ§¿abcdefghijklmnopqrstuvwxyzäöñüà"
)

# GSM 7-bit extended characters (escaped with 0x1B)
GSM7_EXTENDED = {
    "\f": 0x0A,  # Form feed
    "^": 0x14,   # Caret
    "{": 0x28,   # Left brace
    "}": 0x29,   # Right brace
    "\\": 0x2F,  # Backslash
    "[": 0x3C,   # Left bracket
    "~": 0x3D,   # Tilde
    "]": 0x3E,   # Right bracket
    "|": 0x40,   # Pipe
    "€": 0x65,   # Euro sign
}

# Reverse mapping for decoding
GSM7_EXTENDED_REV = {v: k for k, v in GSM7_EXTENDED.items()}


class PDUError(Exception):
    """PDU encoding/decoding error."""
    pass


def encode_gsm7(text: str) -> bytes:
    """
    Encode text to 7-bit GSM alphabet.

    Args:
        text: Text to encode

    Returns:
        Encoded bytes (7-bit packed)

    Raises:
        PDUError: If text contains unsupported characters
    """
    septets = []

    for char in text:
        if char in GSM7_BASIC:
            septets.append(GSM7_BASIC.index(char))
        elif char in GSM7_EXTENDED:
            # Extended character needs escape
            septets.append(0x1B)
            septets.append(GSM7_EXTENDED[char])
        else:
            raise PDUError(f"Character '{char}' not in GSM 7-bit alphabet")

    # Pack 7-bit septets into 8-bit octets
    return _pack_septets(septets)


def decode_gsm7(data: bytes, length: int) -> str:
    """
    Decode 7-bit GSM alphabet to text.

    Args:
        data: Packed 7-bit data
        length: Number of septets (not bytes!)

    Returns:
        Decoded text
    """
    septets = _unpack_septets(data, length)

    text = []
    i = 0
    while i < len(septets):
        if septets[i] == 0x1B:
            # Extended character escape
            if i + 1 < len(septets):
                i += 1
                if septets[i] in GSM7_EXTENDED_REV:
                    text.append(GSM7_EXTENDED_REV[septets[i]])
                else:
                    text.append("?")  # Unknown extended char
            i += 1
        else:
            if septets[i] < len(GSM7_BASIC):
                text.append(GSM7_BASIC[septets[i]])
            else:
                text.append("?")  # Unknown char
            i += 1

    return "".join(text)


def _pack_septets(septets: list[int]) -> bytes:
    """Pack 7-bit septets into 8-bit octets."""
    if not septets:
        return b''

    octets = []
    bits = 0  # Accumulated bits
    bits_count = 0  # Number of bits accumulated

    for septet in septets:
        # Add septet to accumulator
        bits |= (septet << bits_count)
        bits_count += 7

        # Extract complete octets
        while bits_count >= 8:
            octets.append(bits & 0xFF)
            bits >>= 8
            bits_count -= 8

    # Add remaining bits if any
    if bits_count > 0:
        octets.append(bits & 0xFF)

    return bytes(octets)


def _unpack_septets(octets: bytes, length: int) -> list[int]:
    """Unpack 8-bit octets into 7-bit septets."""
    if not octets or length == 0:
        return []

    septets = []
    bits = 0  # Accumulated bits
    bits_count = 0  # Number of bits accumulated

    for octet in octets:
        # Add octet to accumulator
        bits |= (octet << bits_count)
        bits_count += 8

        # Extract complete septets
        while bits_count >= 7 and len(septets) < length:
            septets.append(bits & 0x7F)
            bits >>= 7
            bits_count -= 7

        if len(septets) >= length:
            break

    return septets[:length]


def encode_ucs2(text: str) -> bytes:
    """
    Encode text to UCS2 (UTF-16 BE).

    Args:
        text: Text to encode

    Returns:
        UCS2 encoded bytes
    """
    return text.encode("utf-16-be")


def decode_ucs2(data: bytes) -> str:
    """
    Decode UCS2 (UTF-16 BE) to text.

    Args:
        data: UCS2 encoded data

    Returns:
        Decoded text
    """
    return data.decode("utf-16-be")


def encode_phone_number(number: str) -> Tuple[bytes, int]:
    """
    Encode phone number to PDU format.

    Args:
        number: Phone number (may start with +)

    Returns:
        Tuple of (encoded bytes, type-of-address byte)
    """
    # Determine number type
    if number.startswith("+"):
        # International format
        number = number[1:]
        type_of_addr = 0x91  # International, ISDN/telephone
    else:
        type_of_addr = 0x81  # Unknown, ISDN/telephone

    # Remove non-digit characters
    number = re.sub(r"[^0-9]", "", number)

    # Swap digits in pairs (semi-octet format)
    if len(number) % 2:
        number += "F"  # Pad with F if odd length

    octets = []
    for i in range(0, len(number), 2):
        # Swap nibbles
        octet = int(number[i+1], 16) << 4 | int(number[i], 16)
        octets.append(octet)

    return bytes(octets), type_of_addr


def decode_phone_number(data: bytes, length: int, type_of_addr: int) -> str:
    """
    Decode phone number from PDU format.

    Args:
        data: Encoded phone number
        length: Number of digits
        type_of_addr: Type-of-address byte

    Returns:
        Decoded phone number
    """
    digits = []

    for octet in data:
        # Extract swapped nibbles
        low = octet & 0x0F
        high = (octet >> 4) & 0x0F

        if low != 0xF:
            digits.append(str(low))
        if high != 0xF:
            digits.append(str(high))

    number = "".join(digits[:length])

    # Add + for international numbers
    if (type_of_addr & 0x70) == 0x10:  # International
        number = "+" + number

    return number


def encode_timestamp(dt: Optional[datetime] = None) -> bytes:
    """
    Encode timestamp to PDU format (semi-octet).

    Args:
        dt: Datetime to encode (uses current time if None)

    Returns:
        7-byte timestamp
    """
    if dt is None:
        dt = datetime.now()

    # Format: YY MM DD HH MM SS TZ
    # Each field is semi-octet encoded (digits swapped)
    year = dt.year % 100

    fields = [
        year,
        dt.month,
        dt.day,
        dt.hour,
        dt.minute,
        dt.second,
    ]

    octets = []
    for field in fields:
        # Swap digits
        low = field % 10
        high = field // 10
        octets.append((low << 4) | high)

    # Timezone (in quarters of an hour)
    # For now, use 0 (GMT)
    octets.append(0x00)

    return bytes(octets)


def decode_timestamp(data: bytes) -> str:
    """
    Decode timestamp from PDU format.

    Args:
        data: 7-byte timestamp

    Returns:
        Timestamp string in format: YY/MM/DD,HH:MM:SS±TZ
    """
    if len(data) < 7:
        raise PDUError(f"Invalid timestamp length: {len(data)}")

    def decode_semi_octet(octet: int) -> int:
        """Decode semi-octet (swapped digits)."""
        low = (octet >> 4) & 0x0F
        high = octet & 0x0F
        return high * 10 + low

    year = decode_semi_octet(data[0])
    month = decode_semi_octet(data[1])
    day = decode_semi_octet(data[2])
    hour = decode_semi_octet(data[3])
    minute = decode_semi_octet(data[4])
    second = decode_semi_octet(data[5])

    # Timezone (in quarters of an hour, with sign bit)
    tz_octet = data[6]
    tz_sign = "-" if (tz_octet & 0x08) else "+"
    tz_value = decode_semi_octet(tz_octet & 0xF7)  # Clear sign bit

    return f"{year:02d}/{month:02d}/{day:02d},{hour:02d}:{minute:02d}:{second:02d}{tz_sign}{tz_value:02d}"


def encode_sms_submit(
    number: str,
    text: str,
    encoding: str = "auto",
    validity_period: Optional[int] = None,
    flash: bool = False,
    request_status: bool = False
) -> str:
    """
    Encode SMS-SUBMIT PDU.

    Args:
        number: Destination phone number
        text: Message text
        encoding: "gsm7", "ucs2", or "auto"
        validity_period: Validity period in minutes (None = max)
        flash: Flash SMS (class 0)
        request_status: Request status report

    Returns:
        Hex-encoded PDU string
    """
    pdu = []

    # SMSC length (let modem use default)
    pdu.append(0x00)

    # PDU type (SMS-SUBMIT)
    pdu_type = 0x01  # SMS-SUBMIT
    if validity_period is not None:
        pdu_type |= 0x10  # Validity Period Format: relative
    if request_status:
        pdu_type |= 0x20  # Status Report Request
    pdu.append(pdu_type)

    # Message Reference (let modem assign)
    pdu.append(0x00)

    # Destination address
    phone_data, phone_type = encode_phone_number(number)
    pdu.append(len(number.lstrip("+")))  # Number of digits
    pdu.append(phone_type)
    pdu.extend(phone_data)

    # Protocol Identifier (normal SMS)
    pdu.append(0x00)

    # Auto-detect encoding if needed
    if encoding == "auto":
        try:
            encode_gsm7(text)
            encoding = "gsm7"
        except PDUError:
            encoding = "ucs2"

    # Data Coding Scheme
    if encoding == "gsm7":
        dcs = 0x00  # 7-bit default alphabet
        if flash:
            dcs |= 0x10  # Class 0 (flash)
        user_data = encode_gsm7(text)
        user_data_length = len(text)  # Septets for GSM7
    elif encoding == "ucs2":
        dcs = 0x08  # UCS2
        if flash:
            dcs |= 0x10  # Class 0 (flash)
        user_data = encode_ucs2(text)
        user_data_length = len(user_data)  # Octets for UCS2
    else:
        raise PDUError(f"Unsupported encoding: {encoding}")

    pdu.append(dcs)

    # Validity Period (if specified)
    if validity_period is not None:
        # Convert minutes to TP-VP format
        if validity_period <= 720:  # 12 hours
            vp = (validity_period // 5) - 1
        elif validity_period <= 1440:  # 24 hours
            vp = ((validity_period - 720) // 30) + 143
        elif validity_period <= 43200:  # 30 days
            vp = (validity_period // 1440) + 166
        else:  # > 30 days
            vp = (validity_period // 10080) + 192
        pdu.append(max(0, min(255, vp)))

    # User Data Length
    pdu.append(user_data_length)

    # User Data
    pdu.extend(user_data)

    # Convert to hex string
    return "".join(f"{b:02X}" for b in pdu)


def decode_sms_deliver(pdu_hex: str) -> dict:
    """
    Decode SMS-DELIVER PDU.

    Args:
        pdu_hex: Hex-encoded PDU string

    Returns:
        Dictionary with decoded fields:
        - sender: Phone number
        - timestamp: Timestamp string
        - text: Message text
        - encoding: "gsm7" or "ucs2"
    """
    # Convert hex string to bytes
    pdu = bytes.fromhex(pdu_hex)

    idx = 0

    # SMSC length
    smsc_len = pdu[idx]
    idx += 1 + smsc_len

    # PDU type
    pdu_type = pdu[idx]
    idx += 1

    if (pdu_type & 0x03) != 0x00:
        raise PDUError(f"Not an SMS-DELIVER PDU: {pdu_type:02X}")

    # Sender address
    sender_len = pdu[idx]
    idx += 1
    sender_type = pdu[idx]
    idx += 1

    # Number of octets for sender (round up)
    sender_octets = (sender_len + 1) // 2
    sender_data = pdu[idx:idx + sender_octets]
    idx += sender_octets

    sender = decode_phone_number(sender_data, sender_len, sender_type)

    # Protocol Identifier
    pid = pdu[idx]
    idx += 1

    # Data Coding Scheme
    dcs = pdu[idx]
    idx += 1

    # Timestamp
    timestamp_data = pdu[idx:idx + 7]
    idx += 7
    timestamp = decode_timestamp(timestamp_data)

    # User Data Length
    udl = pdu[idx]
    idx += 1

    # User Data
    user_data = pdu[idx:]

    # Decode based on DCS
    if (dcs & 0x0C) == 0x08:
        # UCS2
        text = decode_ucs2(user_data[:udl])
        encoding = "ucs2"
    else:
        # GSM 7-bit (default)
        text = decode_gsm7(user_data, udl)
        encoding = "gsm7"

    return {
        "sender": sender,
        "timestamp": timestamp,
        "text": text,
        "encoding": encoding,
    }


def calculate_sms_parts(text: str, encoding: str = "auto") -> int:
    """
    Calculate number of SMS parts needed for text.

    Args:
        text: Message text
        encoding: "gsm7", "ucs2", or "auto"

    Returns:
        Number of SMS parts required
    """
    # Auto-detect encoding
    if encoding == "auto":
        try:
            encode_gsm7(text)
            encoding = "gsm7"
        except PDUError:
            encoding = "ucs2"

    if encoding == "gsm7":
        # Count septets (extended chars count as 2)
        septets = 0
        for char in text:
            if char in GSM7_EXTENDED:
                septets += 2
            else:
                septets += 1

        # Single SMS: 160 chars, Concatenated: 153 chars per part
        if septets <= 160:
            return 1
        else:
            return (septets + 152) // 153

    elif encoding == "ucs2":
        # UCS2 uses 2 bytes per character
        # Single SMS: 70 chars, Concatenated: 67 chars per part
        length = len(text)
        if length <= 70:
            return 1
        else:
            return (length + 66) // 67

    else:
        raise PDUError(f"Unsupported encoding: {encoding}")
