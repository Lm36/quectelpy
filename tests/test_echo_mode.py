"""
Tests for AT command echo mode handling with new minimal API.
"""

import pytest
from quectelpy import QuectelModem, MockTransport


def test_echo_mode_functionality():
    """Test setting echo mode via device manager."""
    transport = MockTransport()

    modem = QuectelModem(transport=transport)
    modem.start()

    # Test disabling echo
    transport.add_response(["OK"])
    modem.device.set_echo_mode(False)

    # Test enabling echo
    transport.add_response(["OK"])
    modem.device.set_echo_mode(True)

    modem.close()


def test_echo_stripping_when_enabled():
    """Test that echo is stripped from responses when enabled."""
    transport = MockTransport()

    modem = QuectelModem(transport=transport)
    modem.start()

    # Enable echo
    transport.add_response(["OK"])
    modem.device.set_echo_mode(True)

    # Send command with echo enabled
    # Modem will echo the command, then send response
    transport.add_response(["AT+GSN", "867200061927693", "OK"])

    # Get IMEI - should work despite echo
    imei = modem.device.get_imei()

    # Should get just the IMEI (echo line stripped)
    assert imei == "867200061927693"

    modem.close()


def test_echo_stripping_when_disabled():
    """Test that responses work correctly when echo is disabled."""
    transport = MockTransport()

    modem = QuectelModem(transport=transport)
    modem.start()

    # Disable echo
    transport.add_response(["OK"])
    modem.device.set_echo_mode(False)

    # Send command - no echo in response
    transport.add_response(["867200061927693", "OK"])

    # Get IMEI
    imei = modem.device.get_imei()

    # Should work normally
    assert imei == "867200061927693"

    modem.close()


def test_model_info_with_echo():
    """Test getting model info with echo enabled."""
    transport = MockTransport()

    modem = QuectelModem(transport=transport)
    modem.start()

    # Enable echo
    transport.add_response(["OK"])
    modem.device.set_echo_mode(True)

    # ATI command with echo
    transport.add_response([
        "ATI",  # Echo
        "Quectel",
        "EC25",
        "Revision: EC25AFFAR07A14M4G",
        "OK"
    ])

    model = modem.device.get_model_info()

    assert model.manufacturer == "Quectel"
    assert model.model == "EC25"
    assert model.revision == "EC25AFFAR07A14M4G"

    modem.close()


def test_signal_quality_with_echo():
    """Test getting signal quality with echo enabled."""
    transport = MockTransport()

    modem = QuectelModem(transport=transport)
    modem.start()

    # Enable echo
    transport.add_response(["OK"])
    modem.device.set_echo_mode(True)

    # AT+CSQ with echo
    transport.add_response([
        "AT+CSQ",  # Echo
        "+CSQ: 24,99",
        "OK"
    ])

    signal = modem.network.get_signal_quality()

    assert signal.rssi == 24
    assert signal.ber == 99

    modem.close()


def test_raw_at_with_echo():
    """Test send_raw_at with echo enabled."""
    transport = MockTransport()

    modem = QuectelModem(transport=transport)
    modem.start()

    # Enable echo
    transport.add_response(["OK"])
    modem.device.set_echo_mode(True)

    # Send raw AT command
    transport.add_response([
        "ATI",  # Echo
        "Quectel",
        "EC25",
        "Revision: EC25AFFAR07A14M4G",
        "OK"
    ])

    response = modem.send_raw_at("ATI")

    # Echo should be stripped, response should be clean
    assert "ATI" not in response  # Echo stripped
    assert "Quectel" in response
    assert "EC25" in response
    assert "OK" in response

    modem.close()


def test_echo_with_strip_ok():
    """Test that echo stripping works with strip_ok."""
    transport = MockTransport()

    modem = QuectelModem(transport=transport)
    modem.start()

    # Enable echo
    transport.add_response(["OK"])
    modem.device.set_echo_mode(True)

    # Send command
    transport.add_response([
        "AT+QGMR",  # Echo
        "EC25AFFAR07A14M4G",
        "OK"
    ])

    response = modem.send_raw_at("AT+QGMR", strip_ok=True)

    # Should have echo stripped and OK stripped
    assert len(response) == 1
    assert response[0] == "EC25AFFAR07A14M4G"

    modem.close()


def test_echo_mode_device_api():
    """Test that echo mode is only available via device manager."""
    transport = MockTransport()

    modem = QuectelModem(transport=transport)
    modem.start()

    # Test that main modem class doesn't have echo methods
    assert not hasattr(modem, 'set_echo_mode')
    assert not hasattr(modem, 'get_echo_mode')

    # Test that device manager has set_echo_mode
    assert hasattr(modem.device, 'set_echo_mode')
    assert not hasattr(modem.device, 'get_echo_mode')  # No getter

    # Use the device method
    transport.add_response(["OK"])
    modem.device.set_echo_mode(True)

    transport.add_response(["OK"])
    modem.device.set_echo_mode(False)

    modem.close()


def test_echo_mode_at_commands():
    """Test that echo mode commands execute successfully."""
    transport = MockTransport()

    modem = QuectelModem(transport=transport)
    modem.start()

    # Test ATE0 (disable echo) - should not raise exception
    transport.add_response(["OK"])
    modem.device.set_echo_mode(False)

    # Test ATE1 (enable echo) - should not raise exception
    transport.add_response(["OK"])
    modem.device.set_echo_mode(True)

    modem.close()