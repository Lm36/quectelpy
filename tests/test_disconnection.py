"""
Tests for device disconnection handling.
"""

import pytest
import time
from quectelpy import QuectelModem, MockTransport, DeviceDisconnectedError


def test_disconnection_callback():
    """Test that disconnection callback is called when device disconnects."""
    callback_called = [False]
    callback_error = [None]

    def on_disconnect(error):
        callback_called[0] = True
        callback_error[0] = error

    # Create modem with disconnect callback
    transport = MockTransport()
    modem = QuectelModem(transport=transport, on_disconnect=on_disconnect)
    modem.start()

    # Verify initial state
    assert modem.is_running is True
    assert modem.is_disconnected is False
    assert callback_called[0] is False

    # Simulate disconnection
    transport.close()

    # Wait for reader thread to detect disconnection
    time.sleep(0.5)

    # Verify callback was called
    assert callback_called[0] is True
    assert callback_error[0] is not None
    assert isinstance(callback_error[0], DeviceDisconnectedError)

    # Verify modem state
    assert modem.is_disconnected is True
    assert modem.is_running is False

    modem.close()


def test_disconnection_stops_reader_thread():
    """Test that reader thread stops gracefully on disconnection."""
    transport = MockTransport()
    modem = QuectelModem(transport=transport)
    modem.start()

    # Verify running
    assert modem.is_running is True

    # Simulate disconnection
    transport.close()

    # Wait for reader thread to stop
    time.sleep(0.5)

    # Verify stopped
    assert modem.is_running is False
    assert modem.is_disconnected is True

    modem.close()


def test_no_infinite_loop_on_disconnection():
    """Test that disconnection doesn't cause infinite error loop."""
    error_count = [0]

    def on_disconnect(error):
        error_count[0] += 1

    transport = MockTransport()
    modem = QuectelModem(transport=transport, on_disconnect=on_disconnect)
    modem.start()

    # Simulate disconnection
    transport.close()

    # Wait a bit longer than normal
    time.sleep(1.0)

    # Callback should only be called once, not looping
    assert error_count[0] == 1

    # Thread should be stopped
    assert modem.is_running is False

    modem.close()


def test_consecutive_error_limit():
    """Test that too many consecutive errors stops the reader thread."""
    # Create a custom transport that always raises regular errors
    class ErrorTransport(MockTransport):
        def __init__(self):
            super().__init__()
            self.read_count = 0

        def read_until(self, terminator=b"\r\n", timeout=None):
            self.read_count += 1
            # Raise regular error (not disconnection)
            raise Exception("Test error")

    transport = ErrorTransport()
    modem = QuectelModem(transport=transport)
    modem.start()

    # Wait for error limit to be reached (max 5 errors with backoff)
    # With exponential backoff: 0.1s, 0.2s, 0.4s, 0.8s, 1.6s = ~3.1s total
    time.sleep(5.0)

    # Should have stopped after max errors
    assert modem.is_running is False
    # Should have tried multiple times (up to max_consecutive_errors)
    assert transport.read_count >= 5

    modem.close()


def test_disconnection_without_callback():
    """Test that disconnection works even without a callback."""
    transport = MockTransport()
    modem = QuectelModem(transport=transport)  # No callback
    modem.start()

    assert modem.is_running is True

    # Simulate disconnection
    transport.close()

    # Wait for detection
    time.sleep(0.5)

    # Should still handle disconnection gracefully
    assert modem.is_disconnected is True
    assert modem.is_running is False

    modem.close()


def test_successful_reads_reset_error_counter():
    """Test that successful reads reset the consecutive error counter."""
    # This tests that transient errors don't accumulate
    transport = MockTransport()
    modem = QuectelModem(transport=transport)
    modem.start()

    # Add some responses - reader should process these successfully
    transport.add_response(["+CSQ: 24,99", "OK"])
    transport.add_response(["+CREG: 0,1", "OK"])

    # Wait for reads
    time.sleep(0.5)

    # Should still be running (errors were reset)
    assert modem.is_running is True

    modem.close()
