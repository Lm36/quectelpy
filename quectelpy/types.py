"""
Data types and structures for QuectelPy.

Provides type-safe representations of modem data.
"""

from dataclasses import dataclass
from enum import IntEnum, Enum
from typing import Optional


class RegistrationState(IntEnum):
    """Network registration status values."""
    NOT_REGISTERED = 0
    REGISTERED_HOME = 1
    SEARCHING = 2
    DENIED = 3
    UNKNOWN = 4
    REGISTERED_ROAMING = 5


class SIMState(Enum):
    """SIM card states."""
    READY = "READY"
    SIM_PIN = "SIM PIN"
    SIM_PUK = "SIM PUK"
    SIM_PIN2 = "SIM PIN2"
    SIM_PUK2 = "SIM PUK2"
    PH_NET_PIN = "PH-NET PIN"
    NOT_INSERTED = "NOT INSERTED"


class EquipmentStatus(IntEnum):
    """Mobile equipment activity status (AT+CPAS)."""
    READY = 0
    UNAVAILABLE = 1
    UNKNOWN = 2
    RINGING = 3
    CALL_IN_PROGRESS = 4
    ASLEEP = 5


class MessageFormat(IntEnum):
    """SMS message format modes."""
    PDU_MODE = 0
    TEXT_MODE = 1


class NetworkMode(IntEnum):
    """Network selection mode (AT+COPS)."""
    AUTOMATIC = 0
    MANUAL = 1
    DEREGISTER = 2
    SET_FORMAT_ONLY = 3
    MANUAL_AUTOMATIC = 4


@dataclass
class NetworkInfo:
    """Network information from AT+QNWINFO."""
    rat: str       # Radio Access Technology (e.g., "LTE", "WCDMA")
    operator: str  # MCC+MNC (e.g., "310410")
    band: str      # Band information (e.g., "LTE BAND 4")
    cell_id: int   # Cell ID


@dataclass
class ModelInfo:
    """Modem model information from ATI."""
    manufacturer: str  # e.g., "Quectel"
    model: str         # e.g., "EC25"
    revision: str      # Firmware revision


@dataclass
class SignalQuality:
    """
    Signal quality from AT+CSQ.

    RSSI (Received Signal Strength Indicator):
        0: -113 dBm or less
        1: -111 dBm
        2...30: -109 to -53 dBm
        31: -51 dBm or greater
        99: Not known or not detectable

    BER (Bit Error Rate):
        0...7: As specified in 3GPP TS 45.008
        99: Not known or not detectable
    """
    rssi: int
    ber: int

    @property
    def rssi_dbm(self) -> Optional[int]:
        """Convert RSSI to dBm value."""
        if self.rssi == 99:
            return None
        if self.rssi == 0:
            return -113
        if self.rssi == 31:
            return -51
        return -113 + (self.rssi * 2)

    @property
    def is_valid(self) -> bool:
        """Check if signal quality reading is valid."""
        return self.rssi != 99


@dataclass
class CurrentOperator:
    """Current operator from AT+COPS?"""
    mode: int      # Network selection mode
    format: int    # Operator name format
    oper: str      # Operator name/code
    act: int       # Access technology


@dataclass
class RegistrationStatus:
    """
    Network registration status from AT+CREG? or AT+CGREG?

    Attributes:
        n: Reporting mode (0=disable, 1=enable, 2=enable with location)
        stat: Registration status (see RegistrationState enum)
        lac: Location Area Code (hex string, if available)
        ci: Cell ID (hex string, if available)
        act: Access technology (if available)
    """
    n: int                      # Reporting mode
    stat: int                   # Registration status
    lac: Optional[str] = None   # Location Area Code (if present)
    ci: Optional[str] = None    # Cell ID (if present)
    act: Optional[int] = None   # Access technology

    @property
    def is_registered(self) -> bool:
        """Check if registered to network (home or roaming)."""
        return self.stat in (
            RegistrationState.REGISTERED_HOME,
            RegistrationState.REGISTERED_ROAMING
        )

    @property
    def state(self) -> RegistrationState:
        """Get registration state as enum."""
        return RegistrationState(self.stat)


@dataclass
class PDPContext:
    """PDP context configuration."""
    cid: int                    # Context ID (1-16)
    pdp_type: str               # Protocol type (e.g., "IP", "IPV6", "IPV4V6")
    apn: str                    # Access Point Name
    pdp_addr: Optional[str] = None      # PDP address
    data_comp: Optional[int] = None     # Data compression
    header_comp: Optional[int] = None   # Header compression


class SMSStatus(Enum):
    """SMS message status values."""
    REC_UNREAD = "REC UNREAD"      # Received unread
    REC_READ = "REC READ"          # Received read
    STO_UNSENT = "STO UNSENT"      # Stored unsent
    STO_SENT = "STO SENT"          # Stored sent
    ALL = "ALL"                    # All messages


class SMSEncoding(Enum):
    """SMS encoding types."""
    GSM7 = "gsm7"       # 7-bit GSM alphabet (160 chars)
    UCS2 = "ucs2"       # Unicode UCS2 (70 chars)
    EIGHTBIT = "8bit"   # 8-bit data
    AUTO = "auto"       # Auto-detect best encoding


@dataclass
class SMSMessage:
    """
    SMS message data.

    Represents a complete SMS message with metadata.
    """
    index: int                      # Message index in storage
    status: str                     # Message status (e.g., "REC READ")
    sender: str                     # Sender phone number
    timestamp: str                  # Timestamp (format: YY/MM/DD,HH:MM:SS±TZ)
    content: str                    # Message text content
    encoding: Optional[str] = None  # Encoding used (gsm7, ucs2, etc.)
    storage: Optional[str] = None   # Storage location (ME, SM, etc.)
    pdu: Optional[str] = None       # Raw PDU data (if available)


@dataclass
class SMSStorage:
    """SMS storage information."""
    storage_type: str               # Storage type (ME, SM, MT, etc.)
    used: int                       # Number of messages stored
    total: int                      # Total storage capacity


