#!/usr/bin/env python3
"""
SMS Operations Example

Demonstrates complete SMS functionality:
- Sending SMS (text and Unicode)
- Reading messages
- Listing messages by status
- Deleting messages
- Storage management
- Receiving new message notifications (URC)

Usage:
    python examples/sms_operations.py /dev/ttyUSB2
"""

import sys
import time
from quectelpy import QuectelModem, SerialTransport
from quectelpy.types import SMSStatus
from quectelpy.parsers.sms import SMSParser


def on_new_sms(urc_line: str):
    """
    Callback for new SMS notifications (+CMTI URC).

    Args:
        urc_line: URC line (e.g., '+CMTI: "ME",5')
    """
    try:
        # Parse the URC to get storage and index
        storage, index = SMSParser.parse_cmti(urc_line)
        print(f"\nNew SMS Received!")
        print(f"   Storage: {storage}, Index: {index}")
        print(f"   Use read_sms({index}) to read it\n")
    except ValueError as e:
        print(f"Failed to parse SMS notification: {e}")


def send_sms_example(modem: QuectelModem):
    """Demonstrate sending SMS."""
    print("\n" + "="*50)
    print("SENDING SMS")
    print("="*50)

    # Send simple SMS
    print("\n1. Sending simple SMS...")
    try:
        recipient = input("Enter recipient number (e.g., +1234567890): ").strip()
        message = input("Enter message text: ").strip()

        if recipient and message:
            ref = modem.sms.send_sms(recipient, message)
            print(f"✓ SMS sent successfully! Reference: {ref}")
        else:
            print("Skipped - no input provided")
    except Exception as e:
        print(f"✗ Failed to send SMS: {e}")

    # Send Unicode SMS
    print("\n2. Sending Unicode SMS...")
    try:
        send_unicode = input("Send Unicode test? (y/n): ").strip().lower()
        if send_unicode == 'y':
            recipient = input("Enter recipient number: ").strip()
            if recipient:
                ref = modem.sms.send_sms(
                    recipient,
                    "Hello 世界! 🌍",
                    encoding="ucs2"
                )
                print(f"✓ Unicode SMS sent! Reference: {ref}")
        else:
            print("Skipped")
    except Exception as e:
        print(f"✗ Failed to send Unicode SMS: {e}")

    # Send with delivery report
    print("\n3. Sending with delivery report...")
    try:
        send_with_report = input("Send with delivery report? (y/n): ").strip().lower()
        if send_with_report == 'y':
            recipient = input("Enter recipient number: ").strip()
            if recipient:
                ref = modem.sms.send_sms(
                    recipient,
                    "Test with delivery report",
                    request_status=True
                )
                print(f"✓ SMS sent with status request! Reference: {ref}")
        else:
            print("Skipped")
    except Exception as e:
        print(f"✗ Failed to send SMS: {e}")


def read_sms_example(modem: QuectelModem):
    """Demonstrate reading SMS."""
    print("\n" + "="*50)
    print("READING SMS")
    print("="*50)

    try:
        index = input("\nEnter message index to read: ").strip()
        if not index:
            print("Skipped")
            return

        index = int(index)
        message = modem.sms.read_sms(index)

        print(f"\nMessage #{message.index}")
        print(f"   From: {message.sender}")
        print(f"   Date: {message.timestamp}")
        print(f"   Status: {message.status}")
        print(f"   Encoding: {message.encoding}")
        print(f"   Content:")
        print(f"   {'-'*40}")
        print(f"   {message.content}")
        print(f"   {'-'*40}")

    except ValueError:
        print("Invalid index")
    except Exception as e:
        print(f"Failed to read message: {e}")


def list_messages_example(modem: QuectelModem):
    """Demonstrate listing messages."""
    print("\n" + "="*50)
    print("LISTING MESSAGES")
    print("="*50)

    status_options = {
        '1': SMSStatus.ALL,
        '2': SMSStatus.REC_UNREAD,
        '3': SMSStatus.REC_READ,
        '4': SMSStatus.STO_UNSENT,
        '5': SMSStatus.STO_SENT,
    }

    print("\nSelect status filter:")
    print("  1. All messages")
    print("  2. Unread messages")
    print("  3. Read messages")
    print("  4. Unsent messages")
    print("  5. Sent messages")

    choice = input("\nChoice (1-5): ").strip()
    status = status_options.get(choice, SMSStatus.ALL)

    try:
        messages = modem.sms.list_messages(status)

        if not messages:
            print(f"\n No messages with status: {status.value}")
            return

        print(f"\n Found {len(messages)} message(s):\n")

        for msg in messages:
            print(f"  [{msg.index}] From: {msg.sender}")
            print(f"      Date: {msg.timestamp}")
            print(f"      Status: {msg.status}")
            print(f"      Preview: {msg.content[:50]}...")
            print()

    except Exception as e:
        print(f"✗ Failed to list messages: {e}")


def delete_messages_example(modem: QuectelModem):
    """Demonstrate deleting messages."""
    print("\n" + "="*50)
    print("DELETING MESSAGES")
    print("="*50)

    print("\nDelete options:")
    print("  1. Delete specific message by index")
    print("  2. Delete all read messages")
    print("  3. Delete all unread messages")
    print("  4. Delete ALL messages (WARNING)")

    choice = input("\nChoice (1-4): ").strip()

    try:
        if choice == '1':
            index = input("Enter message index to delete: ").strip()
            if index:
                modem.sms.delete_message(int(index))
                print(f"Message {index} deleted")

        elif choice == '2':
            confirm = input("Delete all READ messages? (yes/no): ").strip().lower()
            if confirm == 'yes':
                modem.sms.delete_all_messages(SMSStatus.REC_READ)
                print("All read messages deleted")

        elif choice == '3':
            confirm = input("Delete all UNREAD messages? (yes/no): ").strip().lower()
            if confirm == 'yes':
                modem.sms.delete_all_messages(SMSStatus.REC_UNREAD)
                print("All unread messages deleted")

        elif choice == '4':
            confirm = input("Delete ALL messages? (type 'DELETE ALL'): ").strip()
            if confirm == 'DELETE ALL':
                modem.sms.delete_all_messages()
                print("All messages deleted")
            else:
                print("Cancelled")

    except Exception as e:
        print(f"✗ Delete failed: {e}")


def storage_management_example(modem: QuectelModem):
    """Demonstrate storage management."""
    print("\n" + "="*50)
    print("STORAGE MANAGEMENT")
    print("="*50)

    # Get storage info
    print("\n1. Current storage status:")
    try:
        read_storage, write_storage, receive_storage = modem.sms.get_storage_info()

        print(f"\n   Read Storage:    {read_storage.storage_type}")
        print(f"   Used/Total:      {read_storage.used}/{read_storage.total}")
        print(f"   Free:            {read_storage.total - read_storage.used}")

        print(f"\n   Write Storage:   {write_storage.storage_type}")
        print(f"   Used/Total:      {write_storage.used}/{write_storage.total}")

        print(f"\n   Receive Storage: {receive_storage.storage_type}")
        print(f"   Used/Total:      {receive_storage.used}/{receive_storage.total}")

        # Calculate usage percentage
        usage_pct = (read_storage.used / read_storage.total * 100) if read_storage.total > 0 else 0
        print(f"\n   Overall usage:   {usage_pct:.1f}%")

    except Exception as e:
        print(f"✗ Failed to get storage info: {e}")

    # Get available storage locations
    print("\n2. Available storage locations:")
    try:
        locations = modem.sms.get_storage_locations()
        print(f"   {', '.join(locations)}")

        print("\n   Storage types:")
        print("   - ME: Mobile Equipment (internal memory)")
        print("   - SM: SIM card")
        print("   - MT: Mobile Equipment + SIM (reads from both)")

    except Exception as e:
        print(f"✗ Failed to get storage locations: {e}")

    # Change storage preference
    print("\n3. Change storage preference:")
    change = input("   Change storage? (y/n): ").strip().lower()

    if change == 'y':
        print("\n   Enter storage for:")
        mem1 = input("   Reading/Deleting (ME/SM/MT): ").strip().upper()
        mem2 = input("   Writing/Sending (ME/SM): ").strip().upper()
        mem3 = input("   Receiving (ME/SM): ").strip().upper()

        if mem1 and mem2 and mem3:
            try:
                modem.sms.set_preferred_storage(mem1, mem2, mem3)
                print(f"   ✓ Storage updated: {mem1}, {mem2}, {mem3}")
            except Exception as e:
                print(f"   ✗ Failed to set storage: {e}")
        else:
            print("   Skipped")


def message_format_example(modem: QuectelModem):
    """Demonstrate message format management."""
    print("\n" + "="*50)
    print("MESSAGE FORMAT")
    print("="*50)

    try:
        current_format = modem.sms.get_message_format()
        print(f"\nCurrent format: {current_format.name}")
        print(f"  PDU mode (0): Binary format, supports Unicode and long messages")
        print(f"  Text mode (1): Simple text format, limited to GSM alphabet")

        print("\nNote: This library automatically uses PDU mode for sending")
        print("      to support Unicode and other advanced features.")

    except Exception as e:
        print(f"✗ Failed to get message format: {e}")


def main():
    """Main example program."""
    if len(sys.argv) < 2:
        print("Usage: python sms_operations.py <serial_port>")
        print("Example: python sms_operations.py /dev/ttyUSB2")
        sys.exit(1)

    port = sys.argv[1]

    print("="*50)
    print("SMS OPERATIONS EXAMPLE")
    print("="*50)
    print(f"Port: {port}")

    # Create modem
    transport = SerialTransport(port=port, baudrate=115200)
    modem = QuectelModem(transport=transport)

    try:
        # Start modem
        print("\nStarting modem...")
        modem.start()
        print("✓ Modem started")

        # Register URC callback for new SMS
        print("✓ Registered SMS notification callback")
        modem.register_urc_callback("+CMTI", on_new_sms)

        # Wait for initialization
        time.sleep(1)

        # Interactive menu
        while True:
            print("\n" + "="*50)
            print("MENU")
            print("="*50)
            print("1. Send SMS")
            print("2. Read SMS")
            print("3. List messages")
            print("4. Delete messages")
            print("5. Storage management")
            print("6. Message format info")
            print("7. Exit")

            choice = input("\nChoice (1-7): ").strip()

            if choice == '1':
                send_sms_example(modem)
            elif choice == '2':
                read_sms_example(modem)
            elif choice == '3':
                list_messages_example(modem)
            elif choice == '4':
                delete_messages_example(modem)
            elif choice == '5':
                storage_management_example(modem)
            elif choice == '6':
                message_format_example(modem)
            elif choice == '7':
                break
            else:
                print("Invalid choice")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")

    except Exception as e:
        print(f"\n✗ Error: {e}")

    finally:
        print("\nClosing modem...")
        modem.close()
        print("✓ Done")


if __name__ == "__main__":
    main()
