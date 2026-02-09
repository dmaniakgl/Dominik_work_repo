#!/usr/bin/env python3
"""
PCAN CAN Test Suite Runner
Usage: python pcan_sender.py TC=1
Install: pip install python-can
"""

import can
import time
import sys


# ==================== TEST CASE DEFINITIONS ====================

TEST_CASES = {
    1: [
        # Add Test Case 1 messages here
        (0x11500700, [0x01], "Display expect as reaction to start"),
        (0x11500700, [0x04], "Display expect as reaction to start"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S5 message"),
        (0x11500700, [0x02], "Display expect as reaction to S7 message"),
        (0x11500700, [0x07], "Display expect as reaction to S7 message"),
        (0x11500700, [0x03], "Display expect as reaction to S7 message"),
    ],
    
    2: [
        # Add Test Case 2 messages here
        (0x11500700, [0x04], "Display expect as reaction to start"),
        (0x11500700, [0x01], "Display expect as reaction to start"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S5 message"),
        (0x11500700, [0x03], "Display expect as reaction to S7 message"),
        (0x11500700, [0x07], "Display expect as reaction to S7 message"),
        (0x11500700, [0x02], "Display expect as reaction to S7 message"),
    ],
    
    3: [
        # Add Test Case 3 messages here
        (0x11500700, [0x04], "Display expect as reaction to start"),
        (0x11500700, [0x01], "Display expect as reaction to start"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x11], "LINE_CHECKSUM_FAIL has been sanded to Display"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S5 message"),
        (0x11500700, [0x03], "Display expect as reaction to S7 message"),
        (0x11500700, [0x07], "Display expect as reaction to S7 message"),
        (0x11500700, [0x02], "Display expect as reaction to S7 message"),
    ],
    
    4: [
        (0x11500700, [0x04], "Display expect as reaction to start"),
        (0x11500700, [0x01], "Display expect as reaction to start"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x11], "LINE_CHECKSUM_FAIL has been sanded to Display"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S5 message"),
        (0x11500700, [0x03], "Display expect as reaction to S7 message"),
        (0x11500700, [0x07], "Display expect as reaction to S7 message"),
        (0x11500700, [0x02], "Display expect as reaction to S7 message"),
    ],
    
    5: [
        (0x11500700, [0x04], "Display expect as reaction to start"),
        (0x11500700, [0x01], "Display expect as reaction to start"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x11], "LINE_CHECKSUM_FAIL - first failure (line resend)"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message (resent line)"),
        (0x11500700, [0x11], "LINE_CHECKSUM_FAIL - second failure (update fails)"),
    ],
    
    6: [
        (0x11500700, [0x04], "Display expect as reaction to start"),
        (0x11500700, [0x01], "Display expect as reaction to start"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x12], "LINE_TIMEOUT - first timeout (line resend)"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message (resent line)"),
        (0x11500700, [0x12], "LINE_TIMEOUT - second timeout (update fails)"),
    ],
    
    7: [
        (0x11500700, [0x01], "Display expect as reaction to start"),
        (0x11500700, [0x04], "Display expect as reaction to start"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0xFF], "SPORADIC/UNEXPECTED message - should cause failure"),
    ],
    
    8: [
        (0x11500700, [0xAA], "Random message 1 - should be ignored"),
        (0x11500700, [0xBB], "Random message 2 - should be ignored"),
        (0x11500700, [0xCC], "Random message 3 - should be ignored"),
        (0x11500700, [0x01], "Display expect as reaction to start"),
        (0x11500700, [0x04], "Display expect as reaction to start"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S3 message"),
        (0x11500700, [0x06], "Display expect as reaction to S5 message"),
        (0x11500700, [0x02], "Display expect as reaction to S7 message"),
        (0x11500700, [0x07], "Display expect as reaction to S7 message"),
        (0x11500700, [0x03], "Display expect as reaction to S7 message"),
    ],
}

# ==================== CONFIGURATION ====================

CONFIG = {
    'interface': 'pcan',
    'channel': 'PCAN_USBBUS1',
    'bitrate': 250000,
    'delay_between_messages': 0.1,  # seconds
}

# ===========================================================


class CANSender:
    """Simple CAN message sender"""
    
    def __init__(self, interface, channel, bitrate):
        self.bus = None
        try:
            self.bus = can.Bus(interface=interface, channel=channel, bitrate=bitrate)
            print(f"✓ Connected: {self.bus.channel_info}")
        except can.CanError as e:
            print(f"✗ Connection failed: {e}")
            sys.exit(1)
    
    def send(self, can_id, data, description=""):
        """Send CAN message"""
        try:
            # Determine if extended ID (>11 bits)
            is_extended = can_id > 0x7FF
            
            msg = can.Message(
                arbitration_id=can_id,
                data=data,
                is_extended_id=is_extended
            )
            self.bus.send(msg)
            
            data_hex = ' '.join(f'{b:02X}' for b in data)
            id_type = "Ext" if is_extended else "Std"
            desc_str = f" # {description}" if description else ""
            print(f"[SENT] ID=0x{can_id:X} ({id_type}), Data=[{data_hex}]{desc_str}")
            return True
            
        except can.CanError as e:
            print(f"✗ Send failed: {e}")
            return False
    
    def close(self):
        if self.bus:
            self.bus.shutdown()
            print("✓ Disconnected")


def run_test_case(sender, tc_number, delay):
    """Execute a specific test case"""
    
    if tc_number not in TEST_CASES:
        print(f"✗ Test Case {tc_number} not found!")
        print(f"Available test cases: {list(TEST_CASES.keys())}")
        return False
    
    messages = TEST_CASES[tc_number]
    
    if not messages:
        print(f"⚠ Test Case {tc_number} has no messages defined")
        return False
    
    print(f"\n{'='*70}")
    print(f"Running Test Case {tc_number}")
    print(f"Total messages: {len(messages)}")
    print(f"{'='*70}\n")
    
    success_count = 0
    for i, (can_id, data, description) in enumerate(messages, 1):
        print(f"[{i}/{len(messages)}] ", end="")
        if sender.send(can_id, data, description):
            success_count += 1
        
        if i < len(messages):  # Don't delay after last message
            time.sleep(delay)
    
    print(f"\n{'='*70}")
    print(f"Test Case {tc_number} completed: {success_count}/{len(messages)} messages sent")
    print(f"{'='*70}\n")
    
    return success_count == len(messages)


def parse_arguments():
    """Parse command line arguments"""
    tc_number = None
    
    for arg in sys.argv[1:]:
        if arg.upper().startswith('TC='):
            try:
                tc_number = int(arg.split('=')[1])
            except ValueError:
                print(f"✗ Invalid TC value: {arg}")
                sys.exit(1)
    
    return tc_number


def print_usage():
    """Print usage information"""
    print("Usage: python pcan_sender.py TC=<number>")
    print(f"\nAvailable Test Cases: {list(TEST_CASES.keys())}")
    print("\nExamples:")
    print("  python pcan_sender.py TC=1")
    print("  python pcan_sender.py TC=2")


def main():
    # Parse command line arguments
    tc_number = parse_arguments()
    
    if tc_number is None:
        print("✗ No test case specified!\n")
        print_usage()
        sys.exit(1)
    
    # Initialize CAN sender
    sender = CANSender(
        CONFIG['interface'],
        CONFIG['channel'],
        CONFIG['bitrate']
    )
    
    try:
        # Run the specified test case
        success = run_test_case(
            sender,
            tc_number,
            CONFIG['delay_between_messages']
        )
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n✗ Stopped by user")
        sys.exit(1)
        
    finally:
        sender.close()


if __name__ == "__main__":
    main()