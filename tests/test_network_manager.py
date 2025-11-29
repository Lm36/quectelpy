"""
Tests for NetworkManager.
"""

import pytest
from quectelpy.types import SignalQuality, NetworkInfo, RegistrationStatus, CurrentOperator


def test_get_signal_quality(modem, mock_transport):
    """Test getting signal quality."""
    # Setup mock response
    mock_transport.add_response(["+CSQ: 24,99", "OK"])

    # Call method
    signal = modem.network.get_signal_quality()

    # Verify
    assert isinstance(signal, SignalQuality)
    assert signal.rssi == 24
    assert signal.ber == 99
    assert signal.is_valid is True
    assert signal.rssi_dbm == -65  # -113 + (24 * 2)


def test_get_signal_quality_no_signal(modem, mock_transport):
    """Test getting signal quality when no signal."""
    # Setup mock response (99 = no signal)
    mock_transport.add_response(["+CSQ: 99,99", "OK"])

    # Call method
    signal = modem.network.get_signal_quality()

    # Verify
    assert signal.rssi == 99
    assert signal.is_valid is False
    assert signal.rssi_dbm is None


def test_get_network_info(modem, mock_transport):
    """Test getting network information."""
    # Setup mock response
    mock_transport.add_response(['+QNWINFO: "LTE","310410","LTE BAND 4",5110', "OK"])

    # Call method
    net_info = modem.network.get_network_info()

    # Verify
    assert isinstance(net_info, NetworkInfo)
    assert net_info.rat == "LTE"
    assert net_info.operator == "310410"
    assert net_info.band == "LTE BAND 4"
    assert net_info.cell_id == 5110


def test_get_current_operator(modem, mock_transport):
    """Test getting current operator."""
    # Setup mock response
    mock_transport.add_response(['+COPS: 0,0,"AT&T",7', "OK"])

    # Call method
    operator = modem.network.get_current_operator()

    # Verify
    assert isinstance(operator, CurrentOperator)
    assert operator.mode == 0
    assert operator.format == 0
    assert operator.oper == "AT&T"
    assert operator.act == 7


def test_get_current_operator_not_registered(modem, mock_transport):
    """Test getting current operator when not registered."""
    # Setup mock response (0 = not registered)
    mock_transport.add_response(["+COPS: 0", "OK"])

    # Call method
    operator = modem.network.get_current_operator()

    # Verify
    assert operator is None


def test_get_registration_status(modem, mock_transport):
    """Test getting registration status."""
    # Setup mock response
    mock_transport.add_response(['+CREG: 2,1,"1A2B","00012345",7', "OK"])

    # Call method
    reg_status = modem.network.get_registration_status()

    # Verify
    assert isinstance(reg_status, RegistrationStatus)
    assert reg_status.n == 2
    assert reg_status.stat == 1
    assert reg_status.lac == "1A2B"
    assert reg_status.ci == "00012345"
    assert reg_status.act == 7
    assert reg_status.is_registered is True


def test_get_registration_status_not_registered(modem, mock_transport):
    """Test getting registration status when not registered."""
    # Setup mock response
    mock_transport.add_response(["+CREG: 0,0", "OK"])

    # Call method
    reg_status = modem.network.get_registration_status()

    # Verify
    assert reg_status.stat == 0
    assert reg_status.is_registered is False


def test_get_gprs_attachment_status_attached(modem, mock_transport):
    """Test GPRS attachment status when attached."""
    # Setup mock response
    mock_transport.add_response(["+CGATT: 1", "OK"])

    # Call method
    attached = modem.network.get_gprs_attachment_status()

    # Verify
    assert attached is True


def test_get_gprs_attachment_status_not_attached(modem, mock_transport):
    """Test GPRS attachment status when not attached."""
    # Setup mock response
    mock_transport.add_response(["+CGATT: 0", "OK"])

    # Call method
    attached = modem.network.get_gprs_attachment_status()

    # Verify
    assert attached is False
