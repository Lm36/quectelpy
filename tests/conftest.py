"""
Pytest configuration and fixtures.

Provides shared test fixtures for QuectelPy tests.
"""

import pytest
import logging

from quectelpy.core import MockTransport, ModemCore
from quectelpy import QuectelModem


# Enable logging for tests
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@pytest.fixture
def mock_transport():
    """
    Create a MockTransport instance for testing.

    Example:
        def test_something(mock_transport):
            mock_transport.add_response(["OK"])
            # ... test code ...
    """
    transport = MockTransport()
    yield transport
    transport.close()


@pytest.fixture
def modem_core(mock_transport):
    """
    Create a ModemCore instance with MockTransport.

    Example:
        def test_at_command(modem_core, mock_transport):
            mock_transport.add_response(["+CSQ: 24,99", "OK"])
            response = modem_core.send_at("AT+CSQ")
            assert "+CSQ: 24,99" in response
    """
    core = ModemCore(transport=mock_transport, log_urcs=False)
    core.start()
    yield core
    core.close()


@pytest.fixture
def modem(mock_transport):
    """
    Create a QuectelModem instance with MockTransport.

    Example:
        def test_device_info(modem, mock_transport):
            mock_transport.add_response(["Quectel", "EC25", "Revision: EC25EFAR06A03M4G", "OK"])
            model = modem.device.get_model_info()
            assert model.manufacturer == "Quectel"
    """
    modem_instance = QuectelModem(transport=mock_transport)
    modem_instance.start()
    yield modem_instance
    modem_instance.close()


@pytest.fixture
def mock_model_info_response():
    """Mock response for ATI command."""
    return ["Quectel", "EC25", "Revision: EC25EFAR06A03M4G", "OK"]


@pytest.fixture
def mock_signal_response():
    """Mock response for AT+CSQ command."""
    return ["+CSQ: 24,99", "OK"]


@pytest.fixture
def mock_network_info_response():
    """Mock response for AT+QNWINFO command."""
    return ['+QNWINFO: "LTE","310410","LTE BAND 4",5110', "OK"]


@pytest.fixture
def mock_registration_response():
    """Mock response for AT+CREG? command."""
    return ['+CREG: 2,1,"1A2B","00012345",7', "OK"]


@pytest.fixture
def mock_operator_response():
    """Mock response for AT+COPS? command."""
    return ['+COPS: 0,0,"AT&T",7', "OK"]
