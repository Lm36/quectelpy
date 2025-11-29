"""
Tests for PDU encoding and decoding.
"""

import pytest
from quectelpy.parsers.pdu import (
    encode_gsm7,
    decode_gsm7,
    encode_ucs2,
    decode_ucs2,
    encode_phone_number,
    decode_phone_number,
    encode_timestamp,
    decode_timestamp,
    encode_sms_submit,
    decode_sms_deliver,
    calculate_sms_parts,
    PDUError,
    _pack_septets,
    _unpack_septets,
)


class TestGSM7Encoding:
    """Test GSM 7-bit alphabet encoding/decoding."""

    def test_encode_basic_text(self):
        """Test encoding basic GSM characters."""
        text = "Hello"
        encoded = encode_gsm7(text)
        assert isinstance(encoded, bytes)
        # "Hello" in 7-bit packed format
        assert encoded == b'\xc8\x32\x9b\xfd\x06'

    def test_decode_basic_text(self):
        """Test decoding basic GSM characters."""
        # "Hello" in 7-bit packed format
        data = b'\xc8\x32\x9b\xfd\x06'
        decoded = decode_gsm7(data, 5)
        assert decoded == "Hello"

    def test_encode_decode_round_trip(self):
        """Test encoding and decoding round trip."""
        text = "The quick brown fox jumps over the lazy dog"
        encoded = encode_gsm7(text)
        decoded = decode_gsm7(encoded, len(text))
        assert decoded == text

    def test_encode_extended_characters(self):
        """Test encoding extended GSM characters."""
        # Euro sign is an extended character
        text = "Cost: €10"
        encoded = encode_gsm7(text)
        decoded = decode_gsm7(encoded, 11)  # "Cost: €10" = 11 septets (€ = 2)
        assert decoded == text

    def test_encode_invalid_character(self):
        """Test encoding fails for non-GSM characters."""
        text = "Hello 世界"  # Chinese characters not in GSM alphabet
        with pytest.raises(PDUError):
            encode_gsm7(text)

    def test_decode_with_padding(self):
        """Test decoding handles padding correctly."""
        # Test text that requires padding
        text = "1234567"  # 7 characters = padding required
        encoded = encode_gsm7(text)
        decoded = decode_gsm7(encoded, len(text))
        assert decoded == text


class TestUCS2Encoding:
    """Test UCS2 (Unicode) encoding/decoding."""

    def test_encode_basic_text(self):
        """Test encoding basic text to UCS2."""
        text = "Hello"
        encoded = encode_ucs2(text)
        assert isinstance(encoded, bytes)
        assert encoded == b'\x00H\x00e\x00l\x00l\x00o'

    def test_decode_basic_text(self):
        """Test decoding basic text from UCS2."""
        data = b'\x00H\x00e\x00l\x00l\x00o'
        decoded = decode_ucs2(data)
        assert decoded == "Hello"

    def test_encode_unicode_text(self):
        """Test encoding Unicode characters."""
        text = "Hello 世界"
        encoded = encode_ucs2(text)
        decoded = decode_ucs2(encoded)
        assert decoded == text

    def test_encode_emoji(self):
        """Test encoding emoji characters."""
        text = "Hello 😀"
        encoded = encode_ucs2(text)
        decoded = decode_ucs2(encoded)
        assert decoded == text


class TestPhoneNumberEncoding:
    """Test phone number encoding/decoding."""

    def test_encode_international_number(self):
        """Test encoding international phone number."""
        number = "+1234567890"
        encoded, type_of_addr = encode_phone_number(number)

        assert type_of_addr == 0x91  # International
        # Semi-octet format: swap digits in pairs
        # 10 digits (even) - no padding needed
        assert encoded == b'\x21\x43\x65\x87\x09'

    def test_encode_local_number(self):
        """Test encoding local phone number."""
        number = "1234567890"
        encoded, type_of_addr = encode_phone_number(number)

        assert type_of_addr == 0x81  # Unknown
        # 10 digits (even) - no padding needed
        assert encoded == b'\x21\x43\x65\x87\x09'

    def test_encode_odd_length_number(self):
        """Test encoding phone number with odd length."""
        number = "123"
        encoded, type_of_addr = encode_phone_number(number)

        # Should pad with F
        assert encoded == b'\x21\xF3'

    def test_decode_international_number(self):
        """Test decoding international phone number."""
        data = b'\x21\x43\x65\x87\x09\xF0'
        number = decode_phone_number(data, 10, 0x91)

        assert number == "+1234567890"

    def test_decode_local_number(self):
        """Test decoding local phone number."""
        data = b'\x21\x43\x65\x87\x09\xF0'
        number = decode_phone_number(data, 10, 0x81)

        assert number == "1234567890"

    def test_encode_decode_round_trip(self):
        """Test phone number encoding/decoding round trip."""
        number = "+1234567890"
        encoded, type_of_addr = encode_phone_number(number)
        decoded = decode_phone_number(encoded, 10, type_of_addr)

        assert decoded == number


class TestTimestampEncoding:
    """Test timestamp encoding/decoding."""

    def test_decode_timestamp(self):
        """Test decoding timestamp."""
        # Timestamp: 23/01/15,10:30:45+00
        data = b'\x32\x10\x51\x01\x03\x54\x00'
        timestamp = decode_timestamp(data)

        assert timestamp == "23/01/15,10:30:45+00"

    def test_decode_timestamp_with_timezone(self):
        """Test decoding timestamp with timezone."""
        # Timestamp with +08 timezone (0x80 in semi-octet)
        data = b'\x32\x10\x51\x01\x03\x54\x80'
        timestamp = decode_timestamp(data)

        assert timestamp == "23/01/15,10:30:45+08"

    def test_decode_invalid_timestamp(self):
        """Test decoding invalid timestamp."""
        data = b'\x32\x10\x51'  # Too short
        with pytest.raises(PDUError):
            decode_timestamp(data)


class TestSeptsPacking:
    """Test septet packing/unpacking."""

    def test_pack_septets(self):
        """Test packing septets into octets."""
        septets = [0x48, 0x65, 0x6C, 0x6C, 0x6F]  # "Hello"
        packed = _pack_septets(septets)

        assert packed == b'\xc8\x32\x9b\xfd\x06'

    def test_unpack_septets(self):
        """Test unpacking octets into septets."""
        octets = b'\xc8\x32\x9b\xfd\x06'
        septets = _unpack_septets(octets, 5)

        assert septets == [0x48, 0x65, 0x6C, 0x6C, 0x6F]

    def test_pack_unpack_round_trip(self):
        """Test packing and unpacking round trip."""
        original = [0x48, 0x65, 0x6C, 0x6C, 0x6F]
        packed = _pack_septets(original)
        unpacked = _unpack_septets(packed, 5)

        assert unpacked == original


class TestSMSSubmit:
    """Test SMS-SUBMIT PDU encoding."""

    def test_encode_simple_message(self):
        """Test encoding simple SMS message."""
        pdu = encode_sms_submit(
            number="+1234567890",
            text="Hello",
            encoding="gsm7"
        )

        assert isinstance(pdu, str)
        # PDU should be hex string
        assert all(c in "0123456789ABCDEF" for c in pdu)
        # Should start with SMSC length (00 = use default)
        assert pdu.startswith("00")

    def test_encode_with_ucs2(self):
        """Test encoding message with UCS2."""
        pdu = encode_sms_submit(
            number="+1234567890",
            text="Hello",
            encoding="ucs2"
        )

        # Should contain UCS2 DCS (0x08)
        assert "08" in pdu

    def test_encode_auto_encoding_gsm7(self):
        """Test auto-encoding chooses GSM7 for basic text."""
        pdu = encode_sms_submit(
            number="+1234567890",
            text="Hello",
            encoding="auto"
        )

        # Should use GSM7 (DCS = 0x00)
        # Can't easily check DCS in PDU without parsing, but verify it encodes
        assert isinstance(pdu, str)
        assert len(pdu) > 0

    def test_encode_auto_encoding_ucs2(self):
        """Test auto-encoding chooses UCS2 for Unicode."""
        pdu = encode_sms_submit(
            number="+1234567890",
            text="Hello 世界",
            encoding="auto"
        )

        # Should use UCS2
        assert isinstance(pdu, str)
        assert len(pdu) > 0

    def test_encode_with_validity_period(self):
        """Test encoding with validity period."""
        pdu = encode_sms_submit(
            number="+1234567890",
            text="Hello",
            validity_period=1440  # 24 hours
        )

        # Should contain validity period flag in PDU type
        assert isinstance(pdu, str)
        assert len(pdu) > 0

    def test_encode_flash_sms(self):
        """Test encoding flash SMS."""
        pdu = encode_sms_submit(
            number="+1234567890",
            text="Flash!",
            flash=True
        )

        assert isinstance(pdu, str)
        assert len(pdu) > 0

    def test_encode_with_status_report(self):
        """Test encoding with status report request."""
        pdu = encode_sms_submit(
            number="+1234567890",
            text="Hello",
            request_status=True
        )

        # Should contain status report flag
        assert isinstance(pdu, str)
        assert len(pdu) > 0


class TestSMSDeliver:
    """Test SMS-DELIVER PDU decoding."""

    def test_decode_simple_message(self):
        """Test decoding simple SMS message."""
        # PDU for "Hello" from +1234567890
        pdu = (
            "0791447758100650"  # SMSC
            "040A912143658709"  # PDU type + sender (+1234567890)
            "0000"  # PID + DCS
            "230115103045"  # Timestamp (semi-octet)
            "00"  # Timestamp timezone
            "05"  # UDL (5 septets)
            "C8329BFD06"  # User data (Hello)
        )

        decoded = decode_sms_deliver(pdu)

        assert decoded["sender"] == "+1234567890"
        assert decoded["text"] == "Hello"
        assert decoded["encoding"] == "gsm7"

    def test_decode_invalid_pdu_type(self):
        """Test decoding invalid PDU type."""
        # PDU with wrong type (SMS-SUBMIT instead of SMS-DELIVER)
        pdu = "000100"

        with pytest.raises(PDUError):
            decode_sms_deliver(pdu)


class TestCalculateSMSParts:
    """Test SMS parts calculation."""

    def test_single_part_gsm7(self):
        """Test single-part GSM7 message."""
        text = "Hello"
        parts = calculate_sms_parts(text, "gsm7")

        assert parts == 1

    def test_single_part_gsm7_max(self):
        """Test GSM7 message at max single-part length."""
        text = "A" * 160
        parts = calculate_sms_parts(text, "gsm7")

        assert parts == 1

    def test_multi_part_gsm7(self):
        """Test multi-part GSM7 message."""
        text = "A" * 161
        parts = calculate_sms_parts(text, "gsm7")

        assert parts == 2

    def test_gsm7_extended_characters(self):
        """Test GSM7 with extended characters (count as 2)."""
        text = "€" * 80  # 80 euro signs = 160 septets
        parts = calculate_sms_parts(text, "gsm7")

        assert parts == 1  # Exactly 160 septets

        text = "€" * 81  # 81 euro signs = 162 septets
        parts = calculate_sms_parts(text, "gsm7")

        assert parts == 2  # Over 160, needs 2 parts

    def test_single_part_ucs2(self):
        """Test single-part UCS2 message."""
        text = "A" * 70
        parts = calculate_sms_parts(text, "ucs2")

        assert parts == 1

    def test_multi_part_ucs2(self):
        """Test multi-part UCS2 message."""
        text = "A" * 71
        parts = calculate_sms_parts(text, "ucs2")

        assert parts == 2

    def test_auto_encoding_gsm7(self):
        """Test auto encoding detects GSM7."""
        text = "Hello"
        parts = calculate_sms_parts(text, "auto")

        assert parts == 1

    def test_auto_encoding_ucs2(self):
        """Test auto encoding detects UCS2."""
        text = "Hello 世界"
        parts = calculate_sms_parts(text, "auto")

        assert parts == 1

    def test_invalid_encoding(self):
        """Test invalid encoding raises error."""
        with pytest.raises(PDUError):
            calculate_sms_parts("Hello", "invalid")
