"""
Tests for DeviceManager.
"""

import pytest
from quectelpy.types import ModelInfo, SIMState, EquipmentStatus
from quectelpy.exceptions import SIMError


def test_get_model_info(modem, mock_transport):
    """Test getting model information."""
    # Setup mock response
    mock_transport.add_response(["Quectel", "EC25", "Revision: EC25EFAR06A03M4G", "OK"])

    # Call method
    model = modem.device.get_model_info()

    # Verify
    assert isinstance(model, ModelInfo)
    assert model.manufacturer == "Quectel"
    assert model.model == "EC25"
    assert model.revision == "EC25EFAR06A03M4G"


def test_get_imei(modem, mock_transport):
    """Test getting IMEI."""
    # Setup mock response
    mock_transport.add_response(["861536030196001", "OK"])

    # Call method
    imei = modem.device.get_imei()

    # Verify
    assert imei == "861536030196001"
    assert len(imei) == 15


def test_get_firmware_version(modem, mock_transport):
    """Test getting firmware version."""
    # Setup mock response
    mock_transport.add_response(["EC25EFAR06A03M4G", "OK"])

    # Call method
    firmware = modem.device.get_firmware_version()

    # Verify
    assert firmware == "EC25EFAR06A03M4G"


def test_get_sim_state_ready(modem, mock_transport):
    """Test getting SIM state when ready."""
    # Setup mock response
    mock_transport.add_response(["+CPIN: READY", "OK"])

    # Call method
    sim_state = modem.device.get_sim_state()

    # Verify
    assert sim_state == SIMState.READY


def test_get_sim_state_pin_required(modem, mock_transport):
    """Test getting SIM state when PIN required."""
    # Setup mock response
    mock_transport.add_response(["+CPIN: SIM PIN", "OK"])

    # Call method - should raise error
    with pytest.raises(SIMError) as exc_info:
        modem.device.get_sim_state()

    assert "SIM PIN" in str(exc_info.value)


def test_get_equipment_status(modem, mock_transport):
    """Test getting equipment status."""
    # Setup mock response
    mock_transport.add_response(["+CPAS: 0", "OK"])

    # Call method
    status = modem.device.get_equipment_status()

    # Verify
    assert status == EquipmentStatus.READY
    assert status == 0
