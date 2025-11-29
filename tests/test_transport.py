"""
Tests for transport layer.
"""

import pytest
from quectelpy.core import MockTransport
from quectelpy.exceptions import EC25Error


def test_mock_transport_write():
    """Test MockTransport write operation."""
    transport = MockTransport()

    written = transport.write(b"AT\r\n")
    assert written == 4  # AT\r\n is 4 bytes

    transport.close()


def test_mock_transport_read():
    """Test MockTransport read operation."""
    transport = MockTransport()

    # Add response
    transport.add_response(["OK"])

    # Read line
    line = transport.read_until()
    assert line == b"OK\r\n"

    transport.close()


def test_mock_transport_multiple_lines():
    """Test MockTransport with multiple response lines."""
    transport = MockTransport()

    # Add multi-line response
    transport.add_response(["+CSQ: 24,99", "OK"])

    # Read lines
    line1 = transport.read_until()
    assert line1 == b"+CSQ: 24,99\r\n"

    line2 = transport.read_until()
    assert line2 == b"OK\r\n"

    transport.close()


def test_mock_transport_empty_read():
    """Test MockTransport returns empty when no data."""
    transport = MockTransport()

    line = transport.read_until()
    assert line == b""

    transport.close()


def test_mock_transport_is_open():
    """Test MockTransport is_open status."""
    transport = MockTransport()

    assert transport.is_open() is True

    transport.close()
    assert transport.is_open() is False


def test_mock_transport_write_when_closed():
    """Test MockTransport raises error when writing to closed transport."""
    transport = MockTransport()
    transport.close()

    with pytest.raises(EC25Error):
        transport.write(b"AT\r\n")


def test_mock_transport_reset_buffer():
    """Test MockTransport reset_input_buffer."""
    transport = MockTransport()

    # Should not raise
    transport.reset_input_buffer()

    transport.close()


def test_mock_transport_clear_responses():
    """Test MockTransport clear_responses."""
    transport = MockTransport()

    # Add responses
    transport.add_response(["Line 1"])
    transport.add_response(["Line 2"])

    # Clear
    transport.clear_responses()

    # Should return empty now
    line = transport.read_until()
    assert line == b""

    transport.close()
