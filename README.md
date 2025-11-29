# QuectelPy

A Python library for controlling Quectel cellular modems via AT commands with SMS and device management capabilities.

**📖 [Full Documentation](https://lm36.github.io/quectelpy/)** - Complete API reference

## Features

- **Thread-safe AT command execution** with automatic URC (Unsolicited Result Code) handling
- **Device management**: Device information (IMEI, model, firmware), SIM card management
- **Network operations**: Registration, signal quality monitoring, operator selection
- **SMS messaging**: Send and receive SMS messages with PDU and text mode support
- **CLI tool** - interactive AT command terminal (`quectel-cli`)

## Installation

**Install from source:**

```bash
git clone https://github.com/lm36/quectelpy.git
cd quectelpy
pip install .
```

### Development Installation

For development with testing dependencies:

```bash
git clone https://github.com/lm36/quectelpy.git
cd quectelpy
pip install -e ".[dev]"
```

## Quick Start

```python
from quectelpy import QuectelModem

# Connect to modem
with QuectelModem(port="/dev/ttyUSB2") as modem:
    # Get device info
    model = modem.device.get_model_info()
    print(f"Modem: {model.manufacturer} {model.model}")
    print(f"IMEI: {modem.device.get_imei()}")

    # Check network status
    signal = modem.network.get_signal_quality()
    print(f"Signal: RSSI={signal.rssi}, BER={signal.ber}")

    operator = modem.network.get_current_operator()
    if operator:
        print(f"Connected to: {operator.oper}")

    # Register URC callback
    modem.register_urc_callback("+CMTI", lambda line: print(f"New SMS: {line}"))
```

## CLI Tool

QuectelPy includes an interactive AT command REPL:

```bash
$ quectel-cli /dev/ttyUSB2

QuectelPy CLI v0.1.0
Type 'help' for commands, 'quit' to exit

> ATI
Quectel
EC25
Revision: EC25EFAR06A03M4G

> AT+CSQ
+CSQ: 24,99
OK

> help
Available commands:
  <AT command>  - Send AT command to modem
  help         - Show this help
  quit         - Exit CLI
  urcs         - Show URC monitoring status
```

## Testing

QuectelPy includes comprehensive tests using pytest and a mock transport:

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=quectelpy --cov-report=html

# Run specific test file
pytest tests/test_network_manager.py
```

## Examples

See the `examples/` directory for complete examples:

- `basic_connection.py` - Connect and get device info
- `check_signal.py` - Monitor signal quality
- `network_info.py` - Get detailed network information

## Documentation

### Device Information

```python
# Get model information
model_info = modem.device.get_model_info()
print(f"{model_info.manufacturer} {model_info.model} {model_info.revision}")

# Get IMEI
imei = modem.device.get_imei()

# Get firmware version
firmware = modem.device.get_firmware()

# Check SIM state
sim_state = modem.device.get_sim_state()  # Returns "READY" if SIM is ready
```

### URC Handling

```python
# Register callback for specific URC
def on_new_sms(line):
    print(f"New SMS notification: {line}")

modem.register_urc_callback("+CMTI", on_new_sms)

# URCs are automatically handled in background thread
# Callbacks are invoked when matching URC is received
```

[Full Documentation](https://lm36.github.io/quectelpy/)


## Supported Modems

QuectelPy has been primarily tested with:
- **EC25 (4G LTE)** - Primary development and testing platform


> **Note**: This library has only been tested with the EC25 modem. Compatibility with other Quectel modems or manufacturers is not guaranteed but may work with compatible AT command sets.


## License

[MIT License](LICENSE)


