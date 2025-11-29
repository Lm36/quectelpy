"""
Signal quality monitoring example.

Demonstrates checking signal strength and network registration.
"""

import time
from quectelpy import QuectelModem

# Replace with your serial port
PORT = "/dev/ttyUSB2"


def main():
    """Main function."""
    print("QuectelPy - Signal Quality Monitor\n")

    with QuectelModem(port=PORT) as modem:
        print("Monitoring signal quality (Ctrl+C to stop)...\n")

        try:
            while True:
                # Get signal quality
                signal = modem.network.get_signal_quality()

                if signal.is_valid:
                    rssi_dbm = signal.rssi_dbm
                    print(f"Signal: RSSI={signal.rssi} ({rssi_dbm} dBm), BER={signal.ber}")

                else:
                    print("No signal detected")

                # Check registration
                reg = modem.network.get_registration_status()
                if reg.is_registered:
                    print(f"Registered: {reg.state.name}")
                else:
                    print(f"Not registered: {reg.state.name}")

                print("-" * 40)
                time.sleep(5)

        except KeyboardInterrupt:
            print("\nStopping monitor...")


if __name__ == "__main__":
    main()
