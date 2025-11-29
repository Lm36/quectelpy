"""
Core modem infrastructure.

Provides low-level building blocks for modem communication:
- Transport: Serial communication abstraction
- Protocol: AT command execution
- URC: Unsolicited result code handling
- ModemCore: Coordination of all core components
"""

from .transport import Transport, SerialTransport, MockTransport
from .protocol import ATProtocol
from .urc import URCHandler, URCCallback
from .modem import ModemCore

__all__ = [
    "Transport",
    "SerialTransport",
    "MockTransport",
    "ATProtocol",
    "URCHandler",
    "URCCallback",
    "ModemCore",
]
