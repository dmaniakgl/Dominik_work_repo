#!/usr/bin/env python3
"""
PCAN Generic CAN Message Sender
Purpose: Send any CAN message - predefined or custom

Usage Examples:
    # Send predefined message
    python pcan_sender.py --msg BI_RESULTS --data "01 00 01 A0 82 55 02 00"
    
    # Send custom message by ID
    python pcan_sender.py --id 0x102E0900 --extended --data "01 00 01 A0 82 55 02 00"
    
    # Send message with interactive data input
    python pcan_sender.py --msg BI_RESULTS --interactive
    
    # Send FC 08 date/time (current time)
    python pcan_sender.py --msg CURRENT_DATETIME_CONNECTIVITY --now
    
    # Send FC 08 with specific timestamp
    python pcan_sender.py --msg CURRENT_DATETIME_SENSOR_CONTROL --timestamp 39289500
    
    # List all predefined messages
    python pcan_sender.py --list
    
    # Send standard ID message
    python pcan_sender.py --id 0x123 --data "01 02 03 04"

Install: pip install python-can
"""

import sys
import argparse
from datetime import datetime

# Try to import python-can
CAN_AVAILABLE = True
try:
    import can
except ImportError:
    CAN_AVAILABLE = False
    can = None  # Placeholder

# Try to import config
try:
    from can_messages_config import PREDEFINED_MESSAGES
except ImportError:
    print("WARNING: can_messages_config.py not found!")
    print("Predefined message features will not be available.")
    PREDEFINED_MESSAGES = {}

# ==================== CONFIGURATION ====================

CAN_CONFIG = {
    'interface': 'pcan',
    'channel': 'PCAN_USBBUS1',
    'bitrate': 250000,
}

# FC 08 Date/Time Configuration
EPOCH_BASE = 1451606400  # Unix timestamp for 2016-01-01 00:00:00 UTC

# Known Node IDs for reference
NODE_IDS = {
    'CONNECTIVITY': 0x11,      # Node 17 decimal
    'DISPLAY': 0x09,           # Node 9 decimal
    'CONTROL': 0x07,           # Node 7 decimal
    'SENSOR_CONTROL': 0x1E,    # Node 30 decimal
}


class CANSender:
    """Generic CAN message sender"""
    
    def __init__(self, interface='pcan', channel='PCAN_USBBUS1', bitrate=250000):
        """Initialize CAN bus connection"""
        if not CAN_AVAILABLE:
            print("ERROR: python-can module not found!")
            print("Please install it using: pip install python-can")
            sys.exit(1)
        
        self.bus = None
        try:
            self.bus = can.Bus(interface=interface, channel=channel, bitrate=bitrate)
            print(f"✓ Connected: {self.bus.channel_info}\n")
        except can.CanError as e:
            print(f"✗ Connection failed: {e}\n")
            print("Troubleshooting:")
            print("1. Check PCAN device is connected")
            print("2. Verify PCAN driver is installed")
            print("3. Ensure no other application is using the device")
            print("4. Try different channel: --channel PCAN_USBBUS2")
            print("5. Run diagnostics: python pcan_sender.py --diagnose")
            sys.exit(1)
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            sys.exit(1)
    
    def __del__(self):
        """Clean up CAN bus connection"""
        if self.bus:
            self.bus.shutdown()
    
    def parse_data_string(self, data_str):
        """
        Parse data string into byte array
        Supports formats: "01 02 03", "01,02,03", "010203", "1 2 3"
        """
        if not data_str:
            return []
        
        # Remove common separators and whitespace
        data_str = data_str.replace(',', ' ').replace('-', ' ').strip()
        
        # Split and parse
        parts = data_str.split()
        data = []
        
        for part in parts:
            try:
                # Handle hex with or without 0x prefix
                if part.startswith('0x') or part.startswith('0X'):
                    byte_val = int(part, 16)
                else:
                    byte_val = int(part, 16)  # Assume hex by default
                
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
            # Use current time
            dt = datetime.now()
            timestamp = int(dt.timestamp()) - EPOCH_BASE
        
        # Convert timestamp to 4 bytes (little-endian)
        data = []
        data.append((timestamp >> 0) & 0xFF)   # Byte 0: Bits 0-7
        data.append((timestamp >> 8) & 0xFF)   # Byte 1: Bits 8-15
        data.append((timestamp >> 16) & 0xFF)  # Byte 2: Bits 16-23
        data.append((timestamp >> 24) & 0xFF)  # Byte 3: Bits 24-31
        data.append(0x00)  # Byte 4: Reserved/Unused
        
        return data
    
    def send_message(self, can_id, data, is_extended=True, msg_name=None):
        """
        Send a CAN message
        
        Args:
            can_id: CAN ID (int)
            data: List of data bytes
            is_extended: True for 29-bit ID, False for 11-bit ID
            msg_name: Optional message name for display
        
        Returns:
            bool: True if successful, False otherwise
        """
        if not data:
            data = []
        
        if len(data) > 8:
            print(f"✗ Error: Data length {len(data)} exceeds maximum of 8 bytes")
            return False
        
        try:
            msg = can.Message(
                arbitration_id=can_id,
                is_extended_id=is_extended,
                data=data,
                dlc=len(data)
            )
            
            self.bus.send(msg)
            
            # Display success message
            print("=" * 70)
            if msg_name:
                print(f"✓ CAN Message SENT: {msg_name}")
            else:
                print(f"✓ CAN Message SENT")
            print("=" * 70)
            
            # Display message details
            id_type = "Extended" if is_extended else "Standard"
            id_format = "0x{:08X}" if is_extended else "0x{:03X}"
            print(f"CAN ID:          {id_format.format(can_id)} ({id_type})")
            print(f"Data:            {' '.join(f'{b:02X}' for b in data) if data else '(empty)'}")
            print(f"DLC:             {len(data)}")
            
            # Show additional info for predefined messages
            if msg_name and msg_name in PREDEFINED_MESSAGES:
                msg_config = PREDEFINED_MESSAGES[msg_name]
                print(f"\nMessage Info:")
                print(f"  Description:   {msg_config.get('description', 'N/A')}")
                if 'notes' in msg_config and msg_config['notes']:
                    print(f"  Notes:")
                    for note in msg_config['notes']:
                        print(f"    • {note}")
            
            print("=" * 70)
            
            return True
            
        except Exception as e:
            print(f"✗ Failed to send message: {e}")
            return False
    
    def send_predefined_message(self, msg_name, data=None, timestamp=None, use_now=False):
        """
        Send a predefined message from config
        
        Args:
            msg_name: Message name from PREDEFINED_MESSAGES
            data: Optional data bytes (if None, user must provide or use special decode)
            timestamp: Optional timestamp for FC 08 messages
            use_now: Use current time for FC 08 messages
        """
        if msg_name not in PREDEFINED_MESSAGES:
            print(f"✗ Error: Message '{msg_name}' not found in configuration")
            print(f"  Use --list to see available messages")
            return False
        
        msg_config = PREDEFINED_MESSAGES[msg_name]
        can_id = msg_config['id']
        is_extended = msg_config.get('extended', True)
        
        # Special handling for FC 08 date/time messages
        is_fc08 = 'CURRENT_DATETIME' in msg_name or 'FC 08' in msg_config.get('description', '')
        
        if is_fc08 and (use_now or timestamp is not None):
            data = self.build_fc08_data(timestamp)
            print(f"Generated FC 08 data for {'current time' if use_now else f'timestamp {timestamp}'}")
        
        if data is None:
            print(f"✗ Error: No data provided for message '{msg_name}'")
            print(f"  Use --data to specify data bytes")
            if is_fc08:
                print(f"  Or use --now to send current time")
                print(f"  Or use --timestamp to send specific time")
            return False
        
        return self.send_message(can_id, data, is_extended, msg_name)
    
    def interactive_send(self, msg_name=None, can_id=None, is_extended=True):
        """Interactive mode to build and send a message"""
        print("\n" + "=" * 70)
        print("INTERACTIVE MESSAGE BUILDER")
        print("=" * 70)
        
        # Get message info
        if msg_name:
            if msg_name not in PREDEFINED_MESSAGES:
                print(f"✗ Error: Message '{msg_name}' not found")
                return False
            
            msg_config = PREDEFINED_MESSAGES[msg_name]
            can_id = msg_config['id']
            is_extended = msg_config.get('extended', True)
            
            print(f"\nMessage:         {msg_name}")
            print(f"Description:     {msg_config.get('description', 'N/A')}")
            print(f"CAN ID:          0x{can_id:08X if is_extended else can_id:03X}")
            print(f"ID Type:         {'Extended (29-bit)' if is_extended else 'Standard (11-bit)'}")
            
            # Show data byte descriptions
            if 'data_description' in msg_config:
                print(f"\nData Byte Descriptions:")
                for byte_idx, desc in msg_config['data_description'].items():
                    print(f"  Byte {byte_idx}: {desc}")
        else:
            print(f"\nCAN ID:          0x{can_id:08X if is_extended else can_id:03X}")
            print(f"ID Type:         {'Extended (29-bit)' if is_extended else 'Standard (11-bit)'}")
        
        # Get data from user
        print(f"\nEnter data bytes (0-8 bytes):")
        print(f"  Format: XX XX XX  (hex values, space-separated)")
        print(f"  Example: 01 02 03 A0 B5")
        print(f"  Press Enter for empty data")
        
        data_input = input("Data: ").strip()
        
        if not data_input:
            data = []
        else:
            data = self.parse_data_string(data_input)
            if data is None:
                return False
        
        # Confirm
        print(f"\n" + "-" * 70)
        print(f"Ready to send:")
        print(f"  CAN ID: 0x{can_id:08X if is_extended else can_id:03X}")
        print(f"  Data:   {' '.join(f'{b:02X}' for b in data) if data else '(empty)'}")
        print(f"  DLC:    {len(data)}")
        
        confirm = input("\nSend this message? [Y/n]: ").strip().lower()
        if confirm and confirm not in ['y', 'yes']:
            print("✗ Cancelled")
            return False
        
        return self.send_message(can_id, data, is_extended, msg_name)


def list_predefined_messages():
    """List all predefined messages from config"""
    if not PREDEFINED_MESSAGES:
        print("No predefined messages available (can_messages_config.py not found)")
        return
    
    print("\n" + "=" * 70)
    print("PREDEFINED MESSAGES")
    print("=" * 70 + "\n")
    
    for msg_name, msg_config in sorted(PREDEFINED_MESSAGES.items()):
        can_id = msg_config['id']
        is_extended = msg_config.get('extended', True)
        description = msg_config.get('description', 'N/A')
        
        id_format = f"0x{can_id:08X}" if is_extended else f"0x{can_id:03X}"
        id_type = "Ext" if is_extended else "Std"
        
        print(f"{msg_name:35} {id_format} ({id_type})  {description}")
    
    print("\n" + "=" * 70)
    print(f"Total: {len(PREDEFINED_MESSAGES)} predefined messages")
    print("=" * 70)


def parse_can_id(id_str):
    """Parse CAN ID from string (supports hex and decimal)"""
    try:
        if id_str.startswith('0x') or id_str.startswith('0X'):
            return int(id_str, 16)
        else:
            return int(id_str, 0)  # Auto-detect base
    except ValueError:
        return None


def diagnose_pcan():
    """Diagnose PCAN connection and list available channels"""
    print("\n" + "=" * 70)
    print("PCAN DIAGNOSTICS")
    print("=" * 70)
    
    if not CAN_AVAILABLE:
        print("\n✗ python-can module is NOT installed")
        print("  Install with: pip install python-can")
        return
    
    print("\n✓ python-can module is installed")
    print(f"  Version: {can.__version__ if hasattr(can, '__version__') else 'unknown'}")
    
    # Try to detect available PCAN channels
    print("\n" + "-" * 70)
    print("Testing PCAN channels:")
    print("-" * 70)
    
    channels_to_test = [
        'PCAN_USBBUS1',
        'PCAN_USBBUS2', 
        'PCAN_USBBUS3',
        'PCAN_USBBUS4',
        'PCAN_USBBUS5',
        'PCAN_USBBUS6',
        'PCAN_USBBUS7',
        'PCAN_USBBUS8',
    ]
    
    found_channels = []
    
    for channel in channels_to_test:
        try:
            bus = can.Bus(interface='pcan', channel=channel, bitrate=250000)
            print(f"✓ {channel:20} - AVAILABLE")
            bus.shutdown()
            found_channels.append(channel)
        except Exception as e:
            error_msg = str(e)
            if "initialized" in error_msg.lower() or "not found" in error_msg.lower():
                print(f"✗ {channel:20} - NOT FOUND")
            else:
                print(f"⚠ {channel:20} - ERROR: {error_msg}")
    
    print("-" * 70)
    
    if found_channels:
        print(f"\n✓ Found {len(found_channels)} available channel(s): {', '.join(found_channels)}")
        print(f"\nTo use a specific channel:")
        print(f"  python pcan_sender.py --channel {found_channels[0]} --list")
    else:
        print("\n✗ No PCAN channels found!")
        print("\nPossible reasons:")
        print("  1. PCAN device not connected")
        print("  2. PCAN driver not installed (Windows)")
        print("  3. Wrong permissions (Linux)")
        print("  4. Channel already in use by another application")
        print("\nWindows users: Install PCAN driver from:")
        print("  https://www.peak-system.com/PCAN-USB.199.0.html")
        print("\nLinux users: Check device and permissions:")
        print("  ls -l /dev/pcan*")
        print("  sudo usermod -a -G dialout $USER")
    
    print("\n" + "=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description='Generic CAN Message Sender - Send any CAN message',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Send predefined message with data
  python pcan_sender.py --msg BI_RESULTS --data "01 00 01 A0 82 55 02 00"
  
  # Send FC 08 with current time
  python pcan_sender.py --msg CURRENT_DATETIME_CONNECTIVITY --now
  
  # Send FC 08 with specific timestamp
  python pcan_sender.py --msg CURRENT_DATETIME_SENSOR_CONTROL --timestamp 39289500
  
  # Send custom message by ID (extended)
  python pcan_sender.py --id 0x102E0900 --extended --data "01 00 01"
  
  # Send custom message by ID (standard)
  python pcan_sender.py --id 0x123 --data "AA BB CC DD"
  
  # Interactive mode
  python pcan_sender.py --msg BI_RESULTS --interactive
  python pcan_sender.py --id 0x100 --interactive
  
  # List all predefined messages
  python pcan_sender.py --list
  
  # Different CAN channel/bitrate
  python pcan_sender.py --msg BI_RESULTS --data "01 02" --channel PCAN_USBBUS2 --bitrate 500000

Data Format Options:
  "01 02 03"          - Space-separated hex bytes
  "01,02,03"          - Comma-separated hex bytes
  "0x01 0x02 0x03"    - Hex with 0x prefix
  "1 2 3"             - Space-separated (interpreted as hex)
        '''
    )
    
    # Message selection
    msg_group = parser.add_mutually_exclusive_group()
    msg_group.add_argument('--msg', type=str,
                          help='Predefined message name from config')
    msg_group.add_argument('--id', type=str,
                          help='CAN ID (hex or decimal, e.g., 0x123 or 291)')
    msg_group.add_argument('--list', action='store_true',
                          help='List all predefined messages')
    msg_group.add_argument('--diagnose', action='store_true',
                          help='Run PCAN diagnostics and detect available channels')
    
    # Message data
    parser.add_argument('--data', type=str,
                       help='Data bytes (e.g., "01 02 03 AA BB")')
    
    parser.add_argument('--extended', action='store_true',
                       help='Use extended 29-bit ID (only with --id)')
    
    parser.add_argument('--standard', action='store_true',
                       help='Use standard 11-bit ID (only with --id)')
    
    # FC 08 specific options
    parser.add_argument('--now', action='store_true',
                       help='Use current time (for FC 08 messages)')
    
    parser.add_argument('--timestamp', type=int,
                       help='Timestamp in custom epoch (seconds since 2016-01-01)')
    
    parser.add_argument('--datetime', type=str,
                       help='Date/time string "YYYY-MM-DD HH:MM:SS" (for FC 08)')
    
    # Interactive mode
    parser.add_argument('--interactive', '-i', action='store_true',
                       help='Interactive mode to build message')
    
    # CAN configuration
    parser.add_argument('--channel', default='PCAN_USBBUS1',
                       help='CAN channel (default: PCAN_USBBUS1)')
    
    parser.add_argument('--bitrate', type=int, default=250000,
                       help='CAN bitrate (default: 250000)')
    
    args = parser.parse_args()
    
    # Handle --list
    if args.list:
        list_predefined_messages()
        sys.exit(0)
    
    # Handle --diagnose
    if args.diagnose:
        diagnose_pcan()
        sys.exit(0)
    
    # Validate arguments
    if not args.msg and not args.id:
        parser.print_help()
        print("\n✗ Error: Must specify either --msg or --id (or use --list or --diagnose)")
        sys.exit(1)
    
    # Create sender
    sender = CANSender(
        interface=CAN_CONFIG['interface'],
        channel=args.channel,
        bitrate=args.bitrate
    )
    
    # Handle timestamp/datetime conversion for FC 08
    timestamp = None
    if args.datetime:
        try:
            dt = datetime.strptime(args.datetime, "%Y-%m-%d %H:%M:%S")
            timestamp = int(dt.timestamp()) - EPOCH_BASE
            print(f"Converted datetime to timestamp: {timestamp}")
        except ValueError as e:
            print(f"✗ Error: Invalid datetime format: {e}")
            print("  Use format: YYYY-MM-DD HH:MM:SS")
            sys.exit(1)
    elif args.timestamp:
        timestamp = args.timestamp
    
    # Interactive mode
    if args.interactive:
        if args.msg:
            success = sender.interactive_send(msg_name=args.msg)
        elif args.id:
            can_id = parse_can_id(args.id)
            if can_id is None:
                print(f"✗ Error: Invalid CAN ID: {args.id}")
                sys.exit(1)
            
            is_extended = True
            if args.standard:
                is_extended = False
            elif not args.extended:
                # Auto-detect: if ID > 0x7FF, assume extended
                is_extended = (can_id > 0x7FF)
            
            success = sender.interactive_send(can_id=can_id, is_extended=is_extended)
        
        sys.exit(0 if success else 1)
    
    # Parse data if provided
    data = None
    if args.data:
        data = sender.parse_data_string(args.data)
        if data is None:
            sys.exit(1)
    
    # Send predefined message
    if args.msg:
        success = sender.send_predefined_message(
            msg_name=args.msg,
            data=data,
            timestamp=timestamp,
            use_now=args.now
        )
    
    # Send custom message by ID
    elif args.id:
        can_id = parse_can_id(args.id)
        if can_id is None:
            print(f"✗ Error: Invalid CAN ID: {args.id}")
            sys.exit(1)
        
        if data is None:
            print(f"✗ Error: Must specify --data for custom messages")
            sys.exit(1)
        
        # Determine if extended or standard
        is_extended = True
        if args.standard:
            is_extended = False
        elif not args.extended:
            # Auto-detect: if ID > 0x7FF, assume extended
            is_extended = (can_id > 0x7FF)
        
        success = sender.send_message(can_id, data, is_extended)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()