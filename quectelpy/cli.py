"""
CLI REPL (Read-Eval-Print Loop) for QuectelPy.

Provides an interactive AT command terminal similar to minicom.
"""

import sys
import logging
from typing import Optional

from .modem import QuectelModem
from .version import __version__
from .exceptions import EC25Error


class QuectelCLI:
    """Interactive AT command REPL."""

    def __init__(self, port: str, baudrate: int = 115200, log_urcs: bool = True):
        """
        Initialize CLI.

        Args:
            port: Serial port path
            baudrate: Baud rate
            log_urcs: Display URCs in real-time
        """
        self.port = port
        self.baudrate = baudrate
        self.log_urcs = log_urcs
        self.modem: Optional[QuectelModem] = None
        self.urc_count = 0

    def _setup_urc_display(self):
        """Set up URC display callback."""
        def display_urc(line: str):
            self.urc_count += 1
            print(f"\n[URC {self.urc_count}] {line}")
            print("> ", end="", flush=True)

        # Register wildcard-ish callback for common URCs
        if self.log_urcs:
            urc_prefixes = ["+CMTI", "+CREG", "+CGREG", "+QIURC", "+QIND"]
            for prefix in urc_prefixes:
                self.modem.register_urc_callback(prefix, display_urc)

    def run(self):
        """Run the REPL."""
        print(f"QuectelPy CLI v{__version__}")
        print(f"Connecting to {self.port} at {self.baudrate} baud...")
        print("Type 'help' for commands, 'quit' to exit\n")

        try:
            # Create and start modem
            self.modem = QuectelModem(
                port=self.port,
                baudrate=self.baudrate,
                log_urcs=False  # We handle URC display ourselves
            )
            self.modem.start()
            self._setup_urc_display()

            print("Connected! Ready for AT commands.\n")

            # REPL loop
            while True:
                try:
                    # Get user input
                    cmd = input("> ").strip()

                    if not cmd:
                        continue

                    # Handle special commands
                    if cmd.lower() in ("quit", "exit", "q"):
                        break
                    elif cmd.lower() == "help":
                        self._print_help()
                        continue
                    elif cmd.lower() == "urcs":
                        self._show_urc_status()
                        continue
                    elif cmd.lower() == "clear":
                        print("\033[2J\033[H", end="")  # Clear screen
                        continue
                    elif cmd.lower() == "info":
                        self._show_modem_info()
                        continue

                    # Send AT command
                    self._send_command(cmd)

                except KeyboardInterrupt:
                    print("\nUse 'quit' to exit")
                    continue
                except EOFError:
                    break

        except EC25Error as e:
            print(f"\nError: {e}")
            return 1
        except Exception as e:
            print(f"\nUnexpected error: {e}")
            logging.exception("CLI error")
            return 1
        finally:
            if self.modem:
                print("\nClosing connection...")
                self.modem.close()
                print("Goodbye!")

        return 0

    def _send_command(self, cmd: str):
        """Send AT command and display response."""
        try:
            response = self.modem.send_raw_at(cmd)

            # Display response
            for line in response:
                print(line)

        except EC25Error as e:
            print(f"Error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

    def _print_help(self):
        """Print help message."""
        print("""
Available commands:
  <AT command>  - Send AT command to modem (e.g., AT+CSQ)
  help          - Show this help message
  info          - Show modem information
  urcs          - Show URC monitoring status
  clear         - Clear screen
  quit/exit/q   - Exit CLI

Common AT commands:
  ATI           - Get model information
  AT+CSQ        - Check signal quality
  AT+CREG?      - Check network registration
  AT+COPS?      - Get current operator
  AT+QNWINFO    - Get network info (Quectel specific)
  AT+CPIN?      - Check SIM status
  AT+GSN        - Get IMEI

For full AT command reference, consult your modem's documentation.
        """)

    def _show_urc_status(self):
        """Show URC monitoring status."""
        print(f"\nURCs received this session: {self.urc_count}")
        print(f"URC display: {'Enabled' if self.log_urcs else 'Disabled'}")

        # Show queue status
        queue_size = self.modem._core.urc_handler.queue_size()
        print(f"URCs in queue: {queue_size}")

        # Show registered callbacks
        callbacks = self.modem._core.urc_handler.get_callbacks()
        print(f"\nRegistered callbacks: {len(callbacks)}")
        for prefix in callbacks.keys():
            print(f"  - {prefix}")

    def _show_modem_info(self):
        """Show modem information."""
        try:
            print("\nFetching modem information...")

            # Model info
            model = self.modem.device.get_model_info()
            print(f"\nModel: {model.manufacturer} {model.model}")
            print(f"Revision: {model.revision}")

            # IMEI
            imei = self.modem.device.get_imei()
            print(f"IMEI: {imei}")

            # Firmware
            firmware = self.modem.device.get_firmware_version()
            print(f"Firmware: {firmware}")

            # Signal
            signal = self.modem.network.get_signal_quality()
            if signal.is_valid:
                print(f"\nSignal: RSSI={signal.rssi} ({signal.rssi_dbm} dBm), BER={signal.ber}")
            else:
                print("\nSignal: No signal detected")

            # Registration
            reg = self.modem.network.get_registration_status()
            print(f"Registration: {reg.state.name}")
            if reg.is_registered:
                if reg.lac and reg.ci:
                    print(f"Location: LAC={reg.lac}, CI={reg.ci}")

            # Operator
            operator = self.modem.network.get_current_operator()
            if operator:
                print(f"Operator: {operator.oper}")

        except Exception as e:
            print(f"Error fetching modem info: {e}")


def main():
    """Main entry point for CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="QuectelPy CLI - Interactive AT command terminal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  quectel-cli /dev/ttyUSB2
  quectel-cli /dev/ttyUSB2 --baudrate 9600
  quectel-cli /dev/ttyUSB2 --no-urcs
        """
    )

    parser.add_argument(
        "port",
        help="Serial port (e.g., /dev/ttyUSB2, COM3)"
    )
    parser.add_argument(
        "-b", "--baudrate",
        type=int,
        default=115200,
        help="Baud rate (default: 115200)"
    )
    parser.add_argument(
        "--no-urcs",
        action="store_true",
        help="Disable URC display"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    if args.verbose:
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    else:
        logging.basicConfig(
            level=logging.WARNING,
            format='%(levelname)s: %(message)s'
        )

    # Run CLI
    cli = QuectelCLI(
        port=args.port,
        baudrate=args.baudrate,
        log_urcs=not args.no_urcs
    )

    return cli.run()


if __name__ == "__main__":
    sys.exit(main())
