"""
Basic connection example.

Demonstrates connecting to a modem and getting basic device information.
"""

from quectelpy import QuectelModem

# Replace with your serial port
PORT = "/dev/ttyUSB2"


def main():
    """Main function."""
    print("QuectelPy - Basic Connection Example\n")

    # Connect to modem using context manager
    # This automatically starts and closes the modem
    with QuectelModem(port=PORT) as modem:
        print("Connected to modem!\n")

        # Get model information
        print("=== Device Information ===")
        model = modem.device.get_model_info()
        print(f"Manufacturer: {model.manufacturer}")
        print(f"Model: {model.model}")
        print(f"Revision: {model.revision}")

        # Get IMEI
        imei = modem.device.get_imei()
        print(f"IMEI: {imei}")

        # Get firmware version
        firmware = modem.device.get_firmware_version()
        print(f"Firmware: {firmware}")

        # Check SIM state
        print("\n=== SIM Information ===")
        try:
            sim_state = modem.device.get_sim_state()
            print(f"SIM State: {sim_state.value}")
        except Exception as e:
            print(f"SIM Error: {e}")

    print("\nConnection closed.")


if __name__ == "__main__":
    main()
