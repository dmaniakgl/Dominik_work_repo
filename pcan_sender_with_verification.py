#!/usr/bin/env python3
"""
PCAN CAN Test Suite with Automated Response Verification
Usage: python pcan_sender.py TC=1
Install: pip install python-can
"""

import can
import time
import sys
import threading


# ==================== TEST CASE DEFINITIONS ====================

TEST_CASES = {
    # Case 1: Ideal case - should pass
    1: {
        'description': 'Ideal case - should pass',
        'expected_result': 'PASS',
        'messages': [
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
        'verify_success': [(0x114F0900, [0xFF, 0x00, 0x81])],  # Expected success message
    },
    
    # Case 2: Messages in different order - should pass
    2: {
        'description': 'Messages in different order - should pass',
        'expected_result': 'PASS',
        'messages': [
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
        'verify_success': [(0x114F0900, [0xFF, 0x00, 0x81])],
    },
    
    # Case 3: LINE_CHECKSUM_FAIL received once - line should be resent
    3: {
        'description': 'LINE_CHECKSUM_FAIL once - should pass with retry',
        'expected_result': 'PASS',
        'messages': [
            (0x11500700, [0x04], "Display expect as reaction to start"),
            (0x11500700, [0x01], "Display expect as reaction to start"),
            (0x11500700, [0x06], "Display expect as reaction to S3 message"),
            (0x11500700, [0x06], "Display expect as reaction to S3 message"),
            (0x11500700, [0x06], "Display expect as reaction to S3 message"),
            (0x11500700, [0x11], "LINE_CHECKSUM_FAIL - trigger line resend"),
            (0x11500700, [0x06], "Display expect as reaction to S3 message (resent line)"),
            (0x11500700, [0x06], "Display expect as reaction to S3 message"),
            (0x11500700, [0x06], "Display expect as reaction to S3 message"),
            (0x11500700, [0x06], "Display expect as reaction to S3 message"),
            (0x11500700, [0x03], "Display expect as reaction to S7 message"),
            (0x11500700, [0x07], "Display expect as reaction to S7 message"),
            (0x11500700, [0x02], "Display expect as reaction to S7 message"),
        ],
        'verify_success': [(0x114F0900, [0xFF, 0x00, 0x81])],
    },
    
    # Case 4: LINE_TIMEOUT received once - line should be resent
    4: {
        'description': 'LINE_TIMEOUT once - should pass with retry',
        'expected_result': 'PASS',
        'messages': [
            (0x11500700, [0x04], "Display expect as reaction to start"),
            (0x11500700, [0x01], "Display expect as reaction to start"),
            (0x11500700, [0x06], "Display expect as reaction to S3 message"),
            (0x11500700, [0x06], "Display expect as reaction to S3 message"),
            (0x11500700, [0x06], "Display expect as reaction to S3 message"),
            (0x11500700, [0x12], "LINE_TIMEOUT - trigger line resend"),
            (0x11500700, [0x06], "Display expect as reaction to S3 message (resent line)"),
            (0x11500700, [0x06], "Display expect as reaction to S3 message"),
            (0x11500700, [0x06], "Display expect as reaction to S3 message"),
            (0x11500700, [0x06], "Display expect as reaction to S3 message"),
            (0x11500700, [0x03], "Display expect as reaction to S7 message"),
            (0x11500700, [0x07], "Display expect as reaction to S7 message"),
            (0x11500700, [0x02], "Display expect as reaction to S7 message"),
        ],
        'verify_success': [(0x114F0900, [0xFF, 0x00, 0x81])],
    },
    
    # Case 5: LINE_CHECKSUM_FAIL received twice - update should fail
    5: {
        'description': 'LINE_CHECKSUM_FAIL twice - should FAIL',
        'expected_result': 'FAIL',
        'messages': [
            (0x11500700, [0x04], "Display expect as reaction to start"),
            (0x11500700, [0x01], "Display expect as reaction to start"),
            (0x11500700, [0x06], "Display expect as reaction to S3 message"),
            (0x11500700, [0x06], "Display expect as reaction to S3 message"),
            (0x11500700, [0x06], "Display expect as reaction to S3 message"),
            (0x11500700, [0x11], "LINE_CHECKSUM_FAIL - first failure (line resend)"),
            (0x11500700, [0x06], "Display expect as reaction to S3 message (resent line)"),
            (0x11500700, [0x11], "LINE_CHECKSUM_FAIL - second failure (update fails)"),
        ],
        'verify_failure': [(0x114F0900, [0xFF, 0x00, 0x81])],  # Expected error message
    },
    
    # Case 6: LINE_TIMEOUT received twice - update should fail
    6: {
        'description': 'LINE_TIMEOUT twice - should FAIL',
        'expected_result': 'FAIL',
        'messages': [
            (0x11500700, [0x04], "Display expect as reaction to start"),
            (0x11500700, [0x01], "Display expect as reaction to start"),
            (0x11500700, [0x06], "Display expect as reaction to S3 message"),
            (0x11500700, [0x06], "Display expect as reaction to S3 message"),
            (0x11500700, [0x06], "Display expect as reaction to S3 message"),
            (0x11500700, [0x12], "LINE_TIMEOUT - first timeout (line resend)"),
            (0x11500700, [0x06], "Display expect as reaction to S3 message (resent line)"),
            (0x11500700, [0x12], "LINE_TIMEOUT - second timeout (update fails)"),
        ],
        'verify_failure': [(0x114F0900, [0xFF, 0x00, 0x81])],
    },
    
    # Case 7: Sporadic/unexpected messages during update - should fail
    7: {
        'description': 'Unexpected message during update - should FAIL',
        'expected_result': 'FAIL',
        'messages': [
            (0x11500700, [0x01], "Display expect as reaction to start"),
            (0x11500700, [0x04], "Display expect as reaction to start"),
            (0x11500700, [0x06], "Display expect as reaction to S3 message"),
            (0x11500700, [0xFF], "SPORADIC/UNEXPECTED message - should cause failure"),
        ],
        'verify_failure': [(0x114F0900, [0xFF, 0x00, 0x81])],
    },
    
    # Case 8: Random messages before update start - should be ignored, then run case 1
    8: {
        'description': 'Pre-update noise ignored - should PASS',
        'expected_result': 'PASS',
        'messages': [
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
        'verify_success': [(0x114F0900, [0xFF, 0x00, 0x81])],
    },
}

# ==================== CONFIGURATION ====================

CONFIG = {
    'interface': 'pcan',
    'channel': 'PCAN_USBBUS1',
    'bitrate': 250000,
    'delay_between_messages': 0.0,  # NO DELAY - send immediately
    'verification_timeout': 5.0,     # seconds to wait for verification message
}

# ===========================================================


class CANListener:
    """CAN message listener for verification"""
    
    def __init__(self, bus):
        self.bus = bus
        self.received_messages = []
        self.listening = False
        self.thread = None
    
    def start(self):
        """Start listening for CAN messages"""
        self.listening = True
        self.received_messages = []
        self.thread = threading.Thread(target=self._listen, daemon=True)
        self.thread.start()
    
    def stop(self):
        """Stop listening for CAN messages"""
        self.listening = False
        if self.thread:
            self.thread.join(timeout=1.0)
    
    def _listen(self):
        """Background thread to listen for messages"""
        while self.listening:
            msg = self.bus.recv(timeout=0.1)
            if msg:
                self.received_messages.append(msg)
    
    def check_message_received(self, expected_id, expected_data, timeout=5.0):
        """
        Check if a specific message was received
        
        Args:
            expected_id: CAN ID to check
            expected_data: Expected data bytes (can use None for wildcard byte)
            timeout: Timeout in seconds
        
        Returns:
            (found, actual_message) tuple
        """
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            for msg in self.received_messages:
                if msg.arbitration_id == expected_id:
                    # Check data match (None = wildcard)
                    data_match = True
                    for i, expected_byte in enumerate(expected_data):
                        if expected_byte is not None:
                            if i >= len(msg.data) or msg.data[i] != expected_byte:
                                data_match = False
                                break
                    
                    if data_match:
                        return True, msg
            
            time.sleep(0.01)
        
        return False, None


class CANSender:
    """CAN message sender with verification"""
    
    def __init__(self, interface, channel, bitrate):
        self.bus = None
        self.listener = None
        try:
            self.bus = can.Bus(interface=interface, channel=channel, bitrate=bitrate)
            self.listener = CANListener(self.bus)
            print(f"✓ Connected: {self.bus.channel_info}")
        except can.CanError as e:
            print(f"✗ Connection failed: {e}")
            sys.exit(1)
    
    def send(self, can_id, data, description=""):
        """Send CAN message"""
        try:
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
    
    def verify_message(self, expected_id, expected_data, timeout=5.0):
        """
        Verify that Display sent expected message
        
        Args:
            expected_id: Expected CAN ID
            expected_data: Expected data bytes (None = wildcard)
            timeout: Timeout in seconds
        
        Returns:
            True if message received, False otherwise
        """
        print(f"\n[VERIFY] Waiting for ID=0x{expected_id:X}, Data={expected_data}, Timeout={timeout}s")
        
        found, msg = self.listener.check_message_received(expected_id, expected_data, timeout)
        
        if found:
            data_hex = ' '.join(f'{b:02X}' for b in msg.data)
            print(f"[VERIFY] ✓ Received: ID=0x{msg.arbitration_id:X}, Data=[{data_hex}]")
            return True
        else:
            print(f"[VERIFY] ✗ Message not received within {timeout}s")
            return False
    
    def close(self):
        if self.listener:
            self.listener.stop()
        if self.bus:
            self.bus.shutdown()
            print("✓ Disconnected")


def run_test_case(sender, tc_number, delay):
    """Execute a specific test case with verification"""
    
    if tc_number not in TEST_CASES:
        print(f"✗ Test Case {tc_number} not found!")
        print(f"Available test cases: {list(TEST_CASES.keys())}")
        return False
    
    tc = TEST_CASES[tc_number]
    messages = tc['messages']
    
    if not messages:
        print(f"⚠ Test Case {tc_number} has no messages defined")
        return False
    
    print(f"\n{'='*70}")
    print(f"Test Case {tc_number}: {tc['description']}")
    print(f"Expected Result: {tc['expected_result']}")
    print(f"Total messages: {len(messages)}")
    print(f"{'='*70}\n")
    
    # Start listening for CAN messages BEFORE sending
    sender.listener.start()
    
    # Send all messages IMMEDIATELY - no delay
    success_count = 0
    start_time = time.time()
    
    for i, (can_id, data, description) in enumerate(messages, 1):
        print(f"[{i}/{len(messages)}] ", end="")
        if sender.send(can_id, data, description):
            success_count += 1
        # NO DELAY - send next message immediately
    
    elapsed = time.time() - start_time
    print(f"\n⚡ All {len(messages)} messages sent in {elapsed*1000:.2f}ms")
    
    # Verify expected response from Display
    print(f"\n{'='*70}")
    print("VERIFICATION PHASE")
    print(f"{'='*70}")
    
    verification_passed = False
    
    if 'verify_success' in tc:
        # Expect success message
        for expected_id, expected_data in tc['verify_success']:
            if sender.verify_message(expected_id, expected_data, CONFIG['verification_timeout']):
                verification_passed = True
                print("\n✓ SUCCESS: Display sent expected success message (0x114F0900#FF0081)")
                break
    
    elif 'verify_failure' in tc:
        # Expect failure message
        for expected_id, expected_data in tc['verify_failure']:
            if sender.verify_message(expected_id, expected_data, CONFIG['verification_timeout']):
                verification_passed = True
                print("\n✓ EXPECTED FAILURE: Display sent expected error message (0x114F0900#FF0081)")
                break
    
    # Stop listening
    sender.listener.stop()
    
    # Final result
    print(f"\n{'='*70}")
    print("TEST RESULTS")
    print(f"{'='*70}")
    print(f"Messages Sent: {success_count}/{len(messages)}")
    print(f"Send Speed: {elapsed*1000:.2f}ms total")
    print(f"Verification: {'PASSED' if verification_passed else 'FAILED'}")
    print(f"Test Case {tc_number}: {'PASSED ✓' if verification_passed else 'FAILED ✗'}")
    print(f"{'='*70}\n")
    
    return verification_passed


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
    print(f"\nAvailable Test Cases:")
    for tc_num, tc_data in TEST_CASES.items():
        print(f"  TC={tc_num}: {tc_data['description']} (Expected: {tc_data['expected_result']})")
    print("\nExamples:")
    print("  python pcan_sender.py TC=1")
    print("  python pcan_sender.py TC=5")


def main():
    tc_number = parse_arguments()
    
    if tc_number is None:
        print("✗ No test case specified!\n")
        print_usage()
        sys.exit(1)
    
    sender = CANSender(
        CONFIG['interface'],
        CONFIG['channel'],
        CONFIG['bitrate']
    )
    
    try:
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