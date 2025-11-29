"""
Network information example.

Demonstrates getting detailed network and operator information.
"""

from quectelpy import QuectelModem

# Replace with your serial port
PORT = "/dev/ttyUSB2"


def main():
    """Main function."""
    print("QuectelPy - Network Information Example\n")

    with QuectelModem(port=PORT) as modem:
        print("=== Network Information ===\n")

        # Get network registration status
        print("Registration Status:")
        reg_status = modem.network.get_registration_status()
        print(f"  State: {reg_status.state.name}")
        print(f"  Registered: {reg_status.is_registered}")

        if reg_status.lac and reg_status.ci:
            print(f"  Location Area Code: {reg_status.lac}")
            print(f"  Cell ID: {reg_status.ci}")

        if reg_status.act is not None:
            print(f"  Access Technology: {reg_status.act}")

        # Get current operator
        print("\nCurrent Operator:")
        operator = modem.network.get_current_operator()
        if operator:
            print(f"  Name: {operator.oper}")
            print(f"  Mode: {operator.mode}")
            print(f"  Access Technology: {operator.act}")
        else:
            print("  Not registered to any operator")

        # Get network info (Quectel-specific)
        print("\nNetwork Details:")
        try:
            net_info = modem.network.get_network_info()
            print(f"  RAT: {net_info.rat}")
            print(f"  Operator Code: {net_info.operator}")
            print(f"  Band: {net_info.band}")
            print(f"  Cell ID: {net_info.cell_id}")
        except Exception as e:
            print(f"  Error getting network info: {e}")

        # Get GPRS attachment status
        print("\nGPRS Status:")
        try:
            gprs_attached = modem.network.get_gprs_attachment_status()
            print(f"  GPRS Attached: {gprs_attached}")

            gprs_reg = modem.network.get_gprs_registration_status()
            print(f"  GPRS Registered: {gprs_reg.is_registered}")
        except Exception as e:
            print(f"  Error getting GPRS status: {e}")

        # Get signal quality
        print("\nSignal Quality:")
        signal = modem.network.get_signal_quality()
        if signal.is_valid:
            print(f"  RSSI: {signal.rssi} ({signal.rssi_dbm} dBm)")
            print(f"  BER: {signal.ber}")
        else:
            print("  No signal")


if __name__ == "__main__":
    main()
