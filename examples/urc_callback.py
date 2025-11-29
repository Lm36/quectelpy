"""
URC callback example.

Demonstrates registering callbacks for unsolicited result codes.
"""

import time
from quectelpy import QuectelModem

# Replace with your serial port
PORT = "/dev/ttyUSB2"


def on_sms_notification(line: str):
    """Handle SMS notification URC."""
    print(f"\n[SMS NOTIFICATION] {line}")


def on_registration_change(line: str):
    """Handle network registration change URC."""
    print(f"\n[REGISTRATION CHANGE] {line}")


def on_signal_change(line: str):
    """Handle signal quality change URC."""
    print(f"\n[SIGNAL CHANGE] {line}")


def main():
    """Main function."""
    print("QuectelPy - URC Callback Example\n")

    with QuectelModem(port=PORT, log_urcs=True) as modem:
        print("Registering URC callbacks...\n")

        # Register callbacks for different URCs
        modem.register_urc_callback("+CMTI", on_sms_notification)
        modem.register_urc_callback("+CREG", on_registration_change)
        modem.register_urc_callback("+CGREG", on_registration_change)
        modem.register_urc_callback("+CSQ", on_signal_change)

        print("Callbacks registered!")
        print("Waiting for URCs (Ctrl+C to stop)...\n")
        print("Tip: URCs are unsolicited messages from the modem,")
        print("like network registration changes or SMS notifications.\n")

        try:
            # Keep running to receive URCs
            while True:
                time.sleep(1)

        except KeyboardInterrupt:
            print("\nStopping...")


if __name__ == "__main__":
    main()
