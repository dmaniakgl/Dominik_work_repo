#!/usr/bin/env python3
"""
PCAN CAN Transceiver - Complete 2-in-1 Sender & Receiver
Combines ALL functionality from pcan_sender.py and pcan_receiver.py

Features:
  - Send any CAN message (predefined or custom)
  - Monitor CAN bus for specific messages
  - Decode special fields (16bit, 32bit, signed, nibbles, enums, bit fields)
  - Interactive message builder
  - PCAN diagnostics
  - FC 08 date/time support
  - Multiple argument styles supported

Usage:
  # RECEIVER MODE
  python pcan_transceiver.py --listen MSG=BI_RESULTS
  python pcan_transceiver.py --listen MSG=BI_RESULTS,BI_USAGE --quiet
  python pcan_transceiver.py MSG=BI_RESULTS --quiet  (alternative syntax)
  
  # SENDER MODE  
  python pcan_transceiver.py --send --msg BI_RESULTS --data "01 00 01"
  python pcan_transceiver.py --send --msg CURRENT_DATETIME_CONNECTIVITY --now
  python pcan_transceiver.py --send --msg CURRENT_DATETIME_CONNECTIVITY --datetime "2026-02-03 07:00:00"
  python pcan_transceiver.py --send --id 0x123 --data "01 02 03"
  
  # INTERACTIVE MODE
  python pcan_transceiver.py --interactive --msg BI_RESULTS
  python pcan_transceiver.py --interactive --id 0x100
  
  # MONITOR MODE
  python pcan_transceiver.py --monitor
  
  # UTILITIES
  python pcan_transceiver.py --list
  python pcan_transceiver.py --diagnose

Install: pip install python-can
"""

import sys
import time
import argparse
from datetime import datetime, timezone

try:
    import can
except ImportError:
    print("ERROR: python-can module not found!")
    print("Please install it using: pip install python-can")
    sys.exit(1)

try:
    from can_messages_config import PREDEFINED_MESSAGES
except ImportError:
    print("WARNING: can_messages_config.py not found!")
    print("Predefined message features will not be available.")
    PREDEFINED_MESSAGES = {}

# ...existing code... (CAN_CONFIG, EPOCH_BASE, NODE_IDS unchanged)

class CANTransceiver:
    """Complete CAN sender and receiver with all features"""
    
    def __init__(self, interface='pcan', channel='PCAN_USBBUS1', bitrate=250000):
        """Initialize CAN bus connection"""
        self.bus = None
        self.listening = False
        
        try:
            self.bus = can.Bus(interface=interface, channel=channel, bitrate=bitrate)
            print(f"✓ Connected to {self.bus.channel_info}\n")
        except can.CanError as e:
            print(f"✗ Connection failed: {e}\n")
            print("Troubleshooting:")
            print("1. Check PCAN device is connected")
            print("2. Verify PCAN driver is installed")
            print("3. Ensure no other application is using the device")
            print("4. Try different channel: --channel PCAN_USBBUS2")
            print("5. Run diagnostics: python pcan_transceiver.py --diagnose")
            sys.exit(1)
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            sys.exit(1)
    
    # ...existing code... (__del__, stop_listening, close unchanged)
    
    # ...existing code... (wait_for_message, wait_for_messages, monitor_all unchanged)
    
    # ==================== SENDING FUNCTIONS ====================
    
    def parse_data_string(self, data_str):
        """Parse data string into byte array"""
        if not data_str:
            return []
        
        data_str = data_str.replace(',', ' ').replace('-', ' ').strip()
        parts = data_str.split()
        data = []
        
        for part in parts:
            try:
                byte_val = int(part, 16)
                
                if 0 <= byte_val <= 255:
                    data.append(byte_val)
                else:
                    print(f"✗ Error: Byte value {byte_val} out of range (0-255)")
                    return None
            except ValueError:
                print(f"✗ Error: Invalid byte value '{part}'")
                return None
        
        return data
    
    def build_fc08_data(self, timestamp=None):
        """Build FC 08 date/time data bytes"""
        if timestamp is None:
            # Get current UTC time using timezone-aware method
            dt = datetime.now(timezone.utc)
            unix_timestamp = int(dt.timestamp())
            timestamp = unix_timestamp - EPOCH_BASE
        
        data = []
        data.append((timestamp >> 0) & 0xFF)
        data.append((timestamp >> 8) & 0xFF)
        data.append((timestamp >> 16) & 0xFF)
        data.append((timestamp >> 24) & 0xFF)
        data.append(0x00)
        
        return data
    
    # ...existing code... (send_message, send_predefined_message, interactive_send unchanged)
    
    # ...existing code... (_decode_special_fields, _print_match_details unchanged)
    
    # ...existing code... (_check_match, _print_message, _print_message_multi, _print_message_simple, _format_data_pattern unchanged)


# ...existing code... (parse_can_id, list_predefined_messages, diagnose_pcan unchanged)


def parse_receiver_style_arguments():
    """Parse pcan_receiver.py style arguments (MSG=, ID=, DATA=, TIMEOUT=)"""
    target_id = None
    target_data = None
    monitor_mode = False
    timeout = 0
    predefined_list = []
    collect_all = True
    quiet_mode = False
    
    for arg in sys.argv[1:]:
        if arg in ['--monitor', '-m']:
            monitor_mode = True
        elif arg in ['--list', '-l']:
            list_predefined_messages()
            sys.exit(0)
        elif arg in ['--first', '-f']:
            collect_all = False
        elif arg in ['--all', '-a']:
            collect_all = True
        elif arg in ['--quiet', '-q']:
            quiet_mode = True
        elif arg in ['--verbose', '-v']:
            quiet_mode = False
        elif arg.upper().startswith('MSG='):
            msg_names = arg.split('=', 1)[1].upper()
            for msg_name in msg_names.split(','):
                msg_name = msg_name.strip()
                if msg_name in PREDEFINED_MESSAGES:
                    predefined_list.append(msg_name)
                else:
                    print(f"✗ Unknown: {msg_name}")
                    sys.exit(1)
        elif arg.upper().startswith('ID='):
            id_str = arg.split('=', 1)[1]
            try:
                target_id = int(id_str, 16) if id_str.startswith('0x') else int(id_str, 0)
            except ValueError:
                print(f"✗ Invalid ID: {id_str}")
                sys.exit(1)
        elif arg.upper().startswith('DATA='):
            data_str = arg.split('=', 1)[1]
            try:
                target_data = []
                for byte_str in data_str.split(','):
                    byte_str = byte_str.strip()
                    if byte_str.upper() in ['X', 'XX', '*', '?']:
                        target_data.append(None)
                    else:
                        byte_val = int(byte_str, 16)
                        if byte_val < 0 or byte_val > 255:
                            raise ValueError(f"Byte {byte_val} out of range")
                        target_data.append(byte_val)
            except ValueError as e:
                print(f"✗ Invalid DATA: {e}")
                sys.exit(1)
        elif arg.upper().startswith('TIMEOUT='):
            try:
                timeout = float(arg.split('=', 1)[1])
                if timeout < 0:
                    raise ValueError()
            except ValueError:
                print(f"✗ Invalid TIMEOUT")
                sys.exit(1)
    
    return monitor_mode, target_id, target_data, timeout, predefined_list, collect_all, quiet_mode


def main():
    # ...existing code... (receiver_style check and block unchanged)
    
    # ...existing code... (argparse setup unchanged)
    
    args = parser.parse_args()
    
    # ...existing code... (--list and --diagnose handlers unchanged)
    
    # Create transceiver
    transceiver = CANTransceiver(
        interface=CAN_CONFIG['interface'],
        channel=args.channel,
        bitrate=args.bitrate
    )
    
    try:
        # Listen mode
        if args.listen:
            # Support both "MSG=NAME" and plain "NAME" formats
            listen_value = args.listen
            if '=' in listen_value:
                listen_value = listen_value.split('=', 1)[1]
            
            msg_names = [name.strip().upper() for name in listen_value.split(',')]
            targets = []
            for msg_name in msg_names:
                if msg_name not in PREDEFINED_MESSAGES:
                    print(f"✗ Unknown message: {msg_name}")
                    sys.exit(1)
                msg_def = PREDEFINED_MESSAGES[msg_name]
                targets.append({
                    'id': msg_def['id'],
                    'data': msg_def.get('data_pattern'),
                    'decode_info': msg_def,
                    'name': msg_name
                })
            
            # ...existing code... (rest of listen mode unchanged)
        
        # ...existing code... (send, interactive, monitor modes unchanged)
    
    except KeyboardInterrupt:
        print("\n\n✓ Stopped by user (Ctrl+C)")
        sys.exit(0)
    finally:
        transceiver.close()


if __name__ == '__main__':
    main()