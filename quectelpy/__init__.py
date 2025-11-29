"""
QuectelPy - Python library for controlling Quectel cellular modems.
"""

from .version import __version__
from .modem import QuectelModem

from .types import (
    NetworkInfo,
    SignalQuality,
    ModelInfo,
    CurrentOperator,
    RegistrationStatus,
    RegistrationState,
    SIMState,
    EquipmentStatus,
    MessageFormat,
    NetworkMode,
    PDPContext,
)

from .exceptions import (
    EC25Error,
    ATTimeoutError,
    ATParseError,
    TransportError,
    DeviceDisconnectedError,
    ModemNotStartedError,
    SIMError,
    NetworkError,
)

__all__ = [
    "__version__",
    "QuectelModem",
    "NetworkInfo",
    "SignalQuality",
    "ModelInfo",
    "CurrentOperator",
    "RegistrationStatus",
    "RegistrationState",
    "SIMState",
    "EquipmentStatus",
    "MessageFormat",
    "NetworkMode",
    "PDPContext",
    "EC25Error",
    "ATTimeoutError",
    "ATParseError",
    "TransportError",
    "DeviceDisconnectedError",
    "ModemNotStartedError",
    "SIMError",
    "NetworkError",
]

