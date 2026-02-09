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
import struct

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

# ==================== CONFIGURATION ====================

CAN_CONFIG = {
    'interface': 'pcan',
    'channel': 'PCAN_USBBUS1',
    'bitrate': 250000,
}

EPOCH_BASE = 1451606400  # Unix timestamp for 2016-01-01 00:00:00 UTC

NODE_IDS = {
    'CONNECTIVITY': 0x11,
    'DISPLAY': 0x09,
    'CONTROL': 0x07,
    'SENSOR_CONTROL': 0x1E,
}


class CANTransceiver:
    """Complete CAN sender and receiver with all features"""
    
    def __init__(self, interface='pcan', channel='PCAN_USBBUS1', bitrate=250000):
        """Initialize CAN bus connection"""
        self.bus = None
        self.listening = False
        
        try:
            self.bus = can.Bus(interface=interface, channel=channel, bitrate=bitrate)
            print(f"\u2713 Connected to {self.bus.channel_info}\n")
        except can.CanError as e:
            print(f"\u2717 Connection failed: {e}\n")
            print("Troubleshooting:")
            print("1. Check PCAN device is connected")
            print("2. Verify PCAN driver is installed")
            print("3. Ensure no other application is using the device")
            print("4. Try different channel: --channel PCAN_USBBUS2")
            print("5. Run diagnostics: python pcan_transceiver.py --diagnose")
            sys.exit(1)
        except Exception as e:
            print(f"\u2717 Unexpected error: {e}")
            sys.exit(1)
    
    def __del__(self):
        """Clean up CAN bus connection"""
        try:
            self.stop_listening()
        except:
            pass
        if self.bus:
            try:
                self.bus.shutdown()
            except:
                pass
    
    def stop_listening(self):
        """Stop listening"""
        self.listening = False
    
    def close(self):
        """Explicitly close the bus"""
        try:
            self.stop_listening()
        except:
            pass
        if self.bus:
            try:
                self.bus.shutdown()
                print("\u2713 Disconnected from CAN bus")
            except Exception:
                pass
    
    # ==================== RECEIVING FUNCTIONS ====================
    
    def wait_for_message(self, target_id, target_data=None, timeout=0, decode_info=None, collect_all=True, quiet_mode=False):
        """Wait for single CAN message"""
        
        data_str = "ANY" if target_data is None else self._format_data_pattern(target_data)
        
        print(f"\n{'='*80}")
        print(f"MONITORING SINGLE MESSAGE")
        print(f"{'='*80}")
        print(f"ID: 0x{target_id:X} | Data: {data_str}")
        print(f"Mode: {'COLLECT ALL' if collect_all else 'STOP AT FIRST'} | Display: {'QUIET' if quiet_mode else 'VERBOSE'}")
        print(f"Timeout: {'\u221e' if timeout == 0 else f'{timeout}s'}")
        
        if decode_info and 'description' in decode_info:
            print(f"Desc: {decode_info['description']}")
        
        print(f"{'='*80}\n")
        print("\U0001f4a1 Press Ctrl+C to stop monitoring\n")
        
        if not quiet_mode:
            print(f"{'Timestamp':<26} {'ID':<12} {'Type':<6} {'DLC':<4} {'Data':<30} {'Match':<10}")
            print(f"{'-'*80}")
        
        start_time = time.time()
        msg_count = 0
        match_count = 0
        matched_messages = []
        header_printed = False
        
        try:
            while True:
                if timeout > 0 and (time.time() - start_time) > timeout:
                    break
                
                try:
                    msg = self.bus.recv(timeout=0.1)
                except KeyboardInterrupt:
                    raise
                
                if msg is None:
                    continue
                
                msg_count += 1
                is_match = self._check_match(msg, target_id, target_data)
                
                if quiet_mode:
                    if is_match:
                        if not header_printed:
                            print(f"{'Timestamp':<26} {'ID':<12} {'Type':<6} {'DLC':<4} {'Data':<30} {'Match':<10}")
                            print(f"{'-'*80}")
                            header_printed = True
                        self._print_message(msg, match=True)
                else:
                    self._print_message(msg, match=is_match)
                
                if is_match:
                    match_count += 1
                    current_ts = datetime.now()
                    matched_messages.append({
                        'timestamp': current_ts,
                        'timestamp_str': current_ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                        'message': msg,
                        'time_from_start': time.time() - start_time
                    })
                    
                    self._print_match_details(msg, match_count, decode_info)
                    
                    if not collect_all:
                        break
                
        except KeyboardInterrupt:
            print(f"\n\n\u2713 Stopped by user (Ctrl+C)")
        
        elapsed = time.time() - start_time
        print(f"\n{'='*80}")
        print(f"SUMMARY: {elapsed:.2f}s | Messages: {msg_count} | Matches: {match_count}")
        print(f"{'='*80}")
        
        if matched_messages:
            if len(matched_messages) <= 5:
                for i, m in enumerate(matched_messages, 1):
                    print(f"  #{i}: {m['timestamp_str']} (+{m['time_from_start']:.2f}s)")
            else:
                print(f"  First: {matched_messages[0]['timestamp_str']}")
                print(f"  Last:  {matched_messages[-1]['timestamp_str']}")
        
        print(f"{'='*80}\n")
        
        return match_count > 0
    
    def wait_for_messages(self, targets, timeout=0, quiet_mode=False, collect_all=True):
        """Wait for multiple CAN messages"""
        
        print(f"\n{'='*80}")
        if len(targets) == 1:
            print(f"MONITORING CAN MESSAGE")
        else:
            print(f"MONITORING MULTIPLE CAN MESSAGES")
        print(f"{'='*80}")
        print(f"Targets: {len(targets)} | Mode: {'COLLECT ALL' if collect_all else 'STOP AT FIRST'}")
        print(f"Display: {'QUIET' if quiet_mode else 'VERBOSE'} | Timeout: {'\u221e' if timeout == 0 else f'{timeout}s'}")
        print(f"{'='*80}\n")
        
        for i, target in enumerate(targets, 1):
            data_str = "ANY" if target['data'] is None else self._format_data_pattern(target['data'])
            print(f"Target {i}: {target.get('name', 'Unknown')}")
            print(f"  ID: 0x{target['id']:X} | Data: {data_str}")
        
        print(f"\n{'='*80}")
        print("\n\U0001f4a1 Press Ctrl+C to stop monitoring\n")
        
        if not quiet_mode:
            print(f"{'Timestamp':<26} {'ID':<12} {'Type':<6} {'DLC':<4} {'Data':<30} {'Match':<15}")
            print(f"{'-'*95}")
        
        start_time = time.time()
        msg_count = 0
        header_printed = False
        
        match_results = {}
        for target in targets:
            key = f"0x{target['id']:X}"
            match_results[key] = {'name': target.get('name', key), 'count': 0, 'matches': []}
        
        try:
            while True:
                if timeout > 0 and (time.time() - start_time) > timeout:
                    break
                
                try:
                    msg = self.bus.recv(timeout=0.1)
                except KeyboardInterrupt:
                    raise
                
                if msg is None:
                    continue
                
                msg_count += 1
                
                matched_target = None
                for target in targets:
                    if self._check_match(msg, target['id'], target['data']):
                        matched_target = target
                        break
                
                if quiet_mode:
                    if matched_target:
                        if not header_printed:
                            print(f"{'Timestamp':<26} {'ID':<12} {'Type':<6} {'DLC':<4} {'Data':<30} {'Match':<15}")
                            print(f"{'-'*95}")
                            header_printed = True
                        self._print_message_multi(msg, match=True, match_name=matched_target.get('name', ''))
                else:
                    match_name = matched_target.get('name', '') if matched_target else None
                    self._print_message_multi(msg, match=(matched_target is not None), match_name=match_name)
                
                if matched_target:
                    key = f"0x{matched_target['id']:X}"
                    match_results[key]['count'] += 1
                    
                    current_ts = datetime.now()
                    match_results[key]['matches'].append({
                        'timestamp': current_ts,
                        'timestamp_str': current_ts.strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                        'message': msg,
                        'time_from_start': time.time() - start_time
                    })
                    
                    total_matches = sum(r['count'] for r in match_results.values())
                    self._print_match_details(msg, total_matches, matched_target.get('decode_info'))
                    
                    if not collect_all:
                        break
                
        except KeyboardInterrupt:
            print(f"\n\n\u2713 Stopped by user (Ctrl+C)")
        
        elapsed = time.time() - start_time
        total_matches = sum(r['count'] for r in match_results.values())
        
        print(f"\n{'='*80}")
        print(f"SUMMARY: {elapsed:.2f}s | Messages: {msg_count} | Matches: {total_matches}")
        print(f"{'='*80}")
        
        for key, result in match_results.items():
            if result['count'] > 0:
                print(f"\n{result['name']}: {result['count']} match(es)")
                if result['count'] <= 5:
                    for i, m in enumerate(result['matches'], 1):
                        print(f"  #{i}: {m['timestamp_str']} (+{m['time_from_start']:.2f}s)")
                else:
                    print(f"  First: {result['matches'][0]['timestamp_str']}")
                    print(f"  Last:  {result['matches'][-1]['timestamp_str']}")
        
        no_matches = [r['name'] for r in match_results.values() if r['count'] == 0]
        if no_matches:
            print(f"\nNo matches: {', '.join(no_matches)}")
        
        print(f"\n{'='*80}\n")
        return total_matches > 0
    
    def monitor_all(self, duration=0):
        """Monitor all CAN traffic"""
        print(f"\n{'='*80}")
        print("CAN BUS MONITOR - ALL TRAFFIC")
        print(f"Duration: {'Infinite (Ctrl+C to stop)' if duration == 0 else f'{duration}s'}")
        print(f"{'='*80}\n")
        print(f"{'Timestamp':<26} {'ID':<12} {'Type':<6} {'DLC':<4} {'Data':<30}")
        print(f"{'-'*80}")
        
        start_time = time.time()
        msg_count = 0
        
        try:
            while True:
                if duration > 0 and (time.time() - start_time) > duration:
                    break
                
                try:
                    msg = self.bus.recv(timeout=0.1)
                except KeyboardInterrupt:
                    raise
                
                if msg is None:
                    continue
                
                msg_count += 1
                self._print_message_simple(msg)
                
        except KeyboardInterrupt:
            print(f"\n\n\u2713 Stopped by user (Ctrl+C)")
        
        elapsed = time.time() - start_time
        print(f"\n{'='*80}")
        print(f"Messages: {msg_count}, Duration: {elapsed:.2f}s")
        print(f"{'='*80}\n")
    
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
                if part.startswith('0x') or part.startswith('0X'):
                    byte_val = int(part, 16)
                else:
                    byte_val = int(part, 16)
                
                if 0 <= byte_val <= 255:
                    data.append(byte_val)
                else:
                    print(f"\u2717 Error: Byte value {byte_val} out of range (0-255)")
                    return None
            except ValueError:
                print(f"\u2717 Error: Invalid byte value '{part}'")
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
    
    def send_message(self, can_id, data, is_extended=True, msg_name=None):
        """Send a CAN message"""
        if not data:
            data = []
        
        if len(data) > 8:
            print(f"\u2717 Error: Data length {len(data)} exceeds maximum of 8 bytes")
            return False
        
        try:
            msg = can.Message(
                arbitration_id=can_id,
                is_extended_id=is_extended,
                data=data,
                dlc=len(data)
            )
            
            self.bus.send(msg)
            
            print("\n" + "=" * 70)
            if msg_name:
                print(f"\u2713 CAN Message SENT: {msg_name}")
            else:
                print(f"\u2713 CAN Message SENT")
            print("=" * 70)
            
            id_type = "Extended" if is_extended else "Standard"
            id_format = "0x{:08X}" if is_extended else "0x{:03X}"
            print(f"CAN ID:          {id_format.format(can_id)} ({id_type})")
            print(f"Data:            {' '.join(f'{b:02X}' for b in data) if data else '(empty)'}")
            print(f"DLC:             {len(data)}")
            
            if msg_name and msg_name in PREDEFINED_MESSAGES:
                msg_config = PREDEFINED_MESSAGES[msg_name]
                print(f"\nMessage Info:")
                print(f"  Description:   {msg_config.get('description', 'N/A')}")
                if 'notes' in msg_config and msg_config['notes']:
                    print(f"  Notes:")
                    for note in msg_config['notes']:
                        print(f"    \u2022 {note}")
            
            print("=" * 70 + "\n")
            
            return True
            
        except Exception as e:
            print(f"\u2717 Failed to send message: {e}")
            return False
    
    def send_predefined_message(self, msg_name, data=None, timestamp=None, use_now=False):
        """Send a predefined message from config"""
        if msg_name not in PREDEFINED_MESSAGES:
            print(f"\u2717 Error: Message '{msg_name}' not found in configuration")
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
            print(f"\u2717 Error: No data provided for message '{msg_name}'")
            print(f"  Use --data to specify data bytes")
            if is_fc08:
                print(f"  Or use --now to send current time")
                print(f"  Or use --timestamp to send specific time")
                print(f"  Or use --datetime to send specific date/time")
            return False
        
        return self.send_message(can_id, data, is_extended, msg_name)
    
    def interactive_send(self, msg_name=None, can_id=None, is_extended=True):
        """Interactive mode to build and send a message"""
        print("\n" + "=" * 70)
        print("INTERACTIVE MESSAGE BUILDER")
        print("=" * 70)
        
        # Get message info
        msg_config = None
        if msg_name:
            if msg_name not in PREDEFINED_MESSAGES:
                print(f"\u2717 Error: Message '{msg_name}' not found")
                return False
            msg_config = PREDEFINED_MESSAGES[msg_name]
            can_id = msg_config['id']
            is_extended = msg_config.get('extended', True)
            
            print(f"Message: {msg_name}")
            print(f"Description: {msg_config.get('description', 'N/A')}")
            
            id_format = "0x{:08X}" if is_extended else "0x{:03X}"
            print(f"CAN ID: {id_format.format(can_id)} ({'Extended' if is_extended else 'Standard'})")
            
            if 'data_description' in msg_config:
                print(f"\nData Format:")
                for idx, desc in sorted(msg_config['data_description'].items()):
                    print(f"  Byte {idx+1} (index {idx}): {desc}")
            
            if 'notes' in msg_config:
                print(f"\nNotes:")
                for note in msg_config['notes']:
                    print(f"  \u2022 {note}")
        else:
            id_format = "0x{:08X}" if is_extended else "0x{:03X}"
            print(f"Custom Message - CAN ID: {id_format.format(can_id)} ({'Extended' if is_extended else 'Standard'})")
        
        print("\n" + "-" * 70)
        
        # Check for FC 08 special handling
        is_fc08 = False
        if msg_name:
            is_fc08 = 'CURRENT_DATETIME' in msg_name or 'FC 08' in (msg_config or {}).get('description', '')
        
        if is_fc08:
            print("\nFC 08 Date/Time Message Options:")
            print("  1. Send current date/time")
            print("  2. Enter custom date/time")
            print("  3. Enter raw data bytes")
            
            choice = input("\nChoice [1]: ").strip() or '1'
            
            if choice == '1':
                data = self.build_fc08_data()
                print(f"Using current UTC time")
            elif choice == '2':
                dt_str = input("Enter date/time (YYYY-MM-DD HH:MM:SS): ").strip()
                try:
                    dt = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
                    epoch_1970 = datetime(1970, 1, 1)
                    unix_ts = int((dt - epoch_1970).total_seconds())
                    custom_ts = unix_ts - EPOCH_BASE
                    data = self.build_fc08_data(custom_ts)
                    print(f"Custom timestamp: {custom_ts} (seconds since 2016-01-01)")
                except ValueError as e:
                    print(f"\u2717 Invalid format: {e}")
                    return False
            else:
                data_str = input("Enter data bytes (hex, space-separated): ").strip()
                data = self.parse_data_string(data_str)
                if data is None:
                    return False
        else:
            data_str = input("\nEnter data bytes (hex, space-separated): ").strip()
            if not data_str:
                print("\u2717 No data entered")
                return False
            data = self.parse_data_string(data_str)
            if data is None:
                return False
        
        # Confirm before sending
        print(f"\n--- Ready to Send ---")
        id_format = "0x{:08X}" if is_extended else "0x{:03X}"
        print(f"ID:   {id_format.format(can_id)}")
        print(f"Data: {' '.join(f'{b:02X}' for b in data)}")
        print(f"DLC:  {len(data)}")
        
        confirm = input("\nSend? [Y/n]: ").strip().lower()
        if confirm in ['n', 'no']:
            print("Cancelled.")
            return False
        
        return self.send_message(can_id, data, is_extended, msg_name)
    
    # ==================== DECODE FUNCTIONS ====================
    
    def _decode_special_fields(self, msg, special_decode):
        """Decode special fields from CAN message data"""
        decoded = {}
        
        for field_name, field_info in special_decode.items():
            try:
                field_type = field_info['type']
                
                if field_type == '16bit':
                    byte_indices = field_info['bytes']
                    if all(idx < len(msg.data) for idx in byte_indices):
                        if field_info.get('endian', 'little') == 'little':
                            value = msg.data[byte_indices[0]] | (msg.data[byte_indices[1]] << 8)
                        else:
                            value = (msg.data[byte_indices[0]] << 8) | msg.data[byte_indices[1]]
                        decoded[field_name] = {
                            'value': value,
                            'hex': f'0x{value:04X}',
                            'description': field_info['description']
                        }
                
                elif field_type == '32bit':
                    byte_indices = field_info['bytes']
                    if all(idx < len(msg.data) for idx in byte_indices):
                        if field_info.get('endian', 'little') == 'little':
                            value = (msg.data[byte_indices[0]] |
                                     (msg.data[byte_indices[1]] << 8) |
                                     (msg.data[byte_indices[2]] << 16) |
                                     (msg.data[byte_indices[3]] << 24))
                        else:
                            value = ((msg.data[byte_indices[0]] << 24) |
                                     (msg.data[byte_indices[1]] << 16) |
                                     (msg.data[byte_indices[2]] << 8) |
                                     msg.data[byte_indices[3]])
                        
                        result = {
                            'value': value,
                            'hex': f'0x{value:08X}',
                            'description': field_info['description']
                        }
                        
                        # Handle epoch-based timestamp conversion
                        if 'epoch_base' in field_info:
                            unix_ts = value + field_info['epoch_base']
                            try:
                                dt = datetime.fromtimestamp(unix_ts, tz=timezone.utc)
                                result['datetime'] = dt.strftime("%Y-%m-%d %H:%M:%S UTC")
                                result['unix_timestamp'] = unix_ts
                            except (OSError, OverflowError, ValueError):
                                result['datetime'] = 'Invalid timestamp'
                                result['unix_timestamp'] = unix_ts
                        
                        decoded[field_name] = result
                
                elif field_type == '16bit_signed':
                    byte_indices = field_info['bytes']
                    if all(idx < len(msg.data) for idx in byte_indices):
                        if field_info.get('endian', 'little') == 'little':
                            raw = msg.data[byte_indices[0]] | (msg.data[byte_indices[1]] << 8)
                        else:
                            raw = (msg.data[byte_indices[0]] << 8) | msg.data[byte_indices[1]]
                        # Convert to signed
                        value = struct.unpack('<h', struct.pack('<H', raw))[0]
                        result = {
                            'value': value,
                            'hex': f'0x{raw:04X}',
                            'description': field_info['description']
                        }
                        if 'status_func' in field_info:
                            try:
                                result['status'] = field_info['status_func'](value)
                            except Exception:
                                pass
                        decoded[field_name] = result
                
                elif field_type == 'nibble_lower':
                    byte_idx = field_info['byte']
                    if len(msg.data) > byte_idx:
                        value = msg.data[byte_idx] & 0x0F
                        decoded[field_name] = {
                            'value': value,
                            'hex': f'0x{value:X}',
                            'description': field_info['description']
                        }
                        if 'values' in field_info:
                            decoded[field_name]['text'] = field_info['values'].get(value, 'Unknown')
                
                elif field_type == 'nibble_upper':
                    byte_idx = field_info['byte']
                    if len(msg.data) > byte_idx:
                        value = (msg.data[byte_idx] >> 4) & 0x0F
                        decoded[field_name] = {
                            'value': value,
                            'hex': f'0x{value:X}',
                            'description': field_info['description']
                        }
                        if 'values' in field_info:
                            decoded[field_name]['text'] = field_info['values'].get(value, 'Unknown')
                
                elif field_type == 'byte_enum':
                    byte_idx = field_info['byte']
                    if len(msg.data) > byte_idx:
                        value = msg.data[byte_idx]
                        decoded[field_name] = {
                            'value': value,
                            'hex': f'0x{value:02X}',
                            'description': field_info['description']
                        }
                        if 'values' in field_info:
                            decoded[field_name]['text'] = field_info['values'].get(value, 'Unknown')
                
                elif field_type == 'bit_field':
                    byte_idx = field_info['byte']
                    bit_pos = field_info.get('bit', 0)
                    if len(msg.data) > byte_idx:
                        byte_val = msg.data[byte_idx]
                        bit_value = (byte_val >> bit_pos) & 0x01
                        decoded[field_name] = {
                            'value': bit_value,
                            'byte_value': byte_val,
                            'bit_position': bit_pos,
                            'description': field_info['description']
                        }
                        if 'values' in field_info:
                            decoded[field_name]['text'] = field_info['values'].get(bit_value, 'Unknown')
                
            except Exception as e:
                print(f"    Warning: Failed to decode {field_name}: {e}")
                continue
        
        return decoded
    
    def _print_match_details(self, msg, match_number, decode_info):
        """Print detailed match information"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        print(f"\n{'-'*80}")
        print(f"MATCH #{match_number}")
        print(f"{'-'*80}")
        print(f"  Time: {ts}")
        print(f"  ID:   0x{msg.arbitration_id:X} ({'Ext' if msg.is_extended_id else 'Std'})")
        print(f"  DLC:  {msg.dlc}")
        print(f"  Data: {' '.join(f'{b:02X}' for b in msg.data)}")
        
        if decode_info and 'data_description' in decode_info and len(msg.data) > 0:
            print(f"\n  Data Breakdown:")
            for i, byte_val in enumerate(msg.data):
                if i in decode_info['data_description']:
                    print(f"    [{i+1}] 0x{byte_val:02X}: {decode_info['data_description'][i]}")
            
            if 'special_decode' in decode_info:
                decoded = self._decode_special_fields(msg, decode_info['special_decode'])
                
                if decoded:
                    print(f"\n  Decoded Values:")
                    for field_name, data in decoded.items():
                        desc = data['description']
                        
                        if 'datetime' in data:
                            # Special formatting for timestamps
                            print(f"    {desc}: {data['value']} (0x{data['value']:08X})")
                            print(f"      Date/Time: {data['datetime']}")
                            print(f"      Unix Time: {data['unix_timestamp']}")
                        elif 'hex' in data and 'text' in data:
                            print(f"    {desc}: {data['value']} ({data['hex']}) = {data['text']}")
                        elif 'hex' in data:
                            print(f"    {desc}: {data['value']} ({data['hex']})")
                        elif 'text' in data:
                            print(f"    {desc}: {data['value']} = {data['text']}")
                        elif 'status' in data:
                            print(f"    {desc}: {data['value']} ({data['hex']}) -> {data['status']}")
                        elif 'bit_position' in data:
                            text = data.get('text', str(data['value']))
                            print(f"    {desc}: Bit {data['bit_position']} = {data['value']} ({text})")
                            print(f"      Full byte: 0x{data['byte_value']:02X} ({data['byte_value']:08b}b)")
                        else:
                            print(f"    {desc}: {data['value']}")
        
        if decode_info and 'notes' in decode_info:
            print(f"\n  Notes:")
            for note in decode_info['notes']:
                print(f"    \u2022 {note}")
        
        print(f"{'-'*80}")
    
    # ==================== HELPER FUNCTIONS ====================
    
    def _check_match(self, msg, target_id, target_data=None):
        """Check if a received message matches the target"""
        if msg.arbitration_id != target_id:
            return False
        
        if target_data is None:
            return True
        
        if len(msg.data) < len(target_data):
            return False
        
        for i, expected in enumerate(target_data):
            if expected is None:
                continue  # Wildcard
            if msg.data[i] != expected:
                return False
        
        return True
    
    def _print_message(self, msg, match=False):
        """Print a single CAN message (single-target mode)"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        if msg.is_extended_id:
            id_str = f"0x{msg.arbitration_id:08X}"
        else:
            id_str = f"0x{msg.arbitration_id:03X}"
        
        type_str = "Ext" if msg.is_extended_id else "Std"
        data_str = ' '.join(f'{b:02X}' for b in msg.data)
        match_str = "<<< MATCH" if match else ""
        
        print(f"{ts:<26} {id_str:<12} {type_str:<6} {msg.dlc:<4} {data_str:<30} {match_str:<10}")
    
    def _print_message_multi(self, msg, match=False, match_name=None):
        """Print a single CAN message (multi-target mode)"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        if msg.is_extended_id:
            id_str = f"0x{msg.arbitration_id:08X}"
        else:
            id_str = f"0x{msg.arbitration_id:03X}"
        
        type_str = "Ext" if msg.is_extended_id else "Std"
        data_str = ' '.join(f'{b:02X}' for b in msg.data)
        
        if match and match_name:
            match_str = f"<<< {match_name}"
        elif match:
            match_str = "<<< MATCH"
        else:
            match_str = ""
        
        print(f"{ts:<26} {id_str:<12} {type_str:<6} {msg.dlc:<4} {data_str:<30} {match_str:<15}")
    
    def _print_message_simple(self, msg):
        """Print a simple CAN message line (monitor mode)"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        
        if msg.is_extended_id:
            id_str = f"0x{msg.arbitration_id:08X}"
        else:
            id_str = f"0x{msg.arbitration_id:03X}"
        
        type_str = "Ext" if msg.is_extended_id else "Std"
        data_str = ' '.join(f'{b:02X}' for b in msg.data)
        
        print(f"{ts:<26} {id_str:<12} {type_str:<6} {msg.dlc:<4} {data_str:<30}")
    
    def _format_data_pattern(self, pattern):
        """Format a data pattern for display"""
        if pattern is None:
            return "ANY"
        parts = []
        for b in pattern:
            if b is None:
                parts.append('XX')
            else:
                parts.append(f'{b:02X}')
        return ' '.join(parts)


# ==================== STANDALONE UTILITY FUNCTIONS ====================

def parse_can_id(id_str):
    """Parse a CAN ID string (hex or decimal) to integer"""
    if not id_str:
        return None
    try:
        id_str = id_str.strip()
        if id_str.startswith('0x') or id_str.startswith('0X'):
            return int(id_str, 16)
        else:
            return int(id_str, 0)
    except ValueError:
        return None


def list_predefined_messages():
    """List all predefined CAN messages"""
    print("\n" + "=" * 80)
    print("PREDEFINED CAN MESSAGES")
    print("=" * 80)
    
    if not PREDEFINED_MESSAGES:
        print("  No predefined messages found.")
        print("  Check that can_messages_config.py is in the same directory.")
        print("=" * 80 + "\n")
        return
    
    for name, config in sorted(PREDEFINED_MESSAGES.items()):
        can_id = config['id']
        is_ext = config.get('extended', True)
        id_format = "0x{:08X}" if is_ext else "0x{:03X}"
        desc = config.get('description', 'N/A')
        
        print(f"\n  {name}")
        print(f"    Description: {desc}")
        print(f"    CAN ID:      {id_format.format(can_id)} ({'Extended' if is_ext else 'Standard'})")
        
        if 'data_pattern' in config and config['data_pattern'] is not None:
            pattern_str = ' '.join(
                'XX' if b is None else f'{b:02X}' for b in config['data_pattern']
            )
            print(f"    Data Match:  {pattern_str}")
        else:
            print(f"    Data Match:  ANY")
        
        if 'data_description' in config:
            print(f"    Data Layout:")
            for idx, desc_text in sorted(config['data_description'].items()):
                print(f"      Byte {idx+1} (index {idx}): {desc_text}")
        
        if 'notes' in config and config['notes']:
            print(f"    Notes:")
            for note in config['notes']:
                print(f"      \u2022 {note}")
    
    print(f"\n{'='*80}")
    print(f"Total: {len(PREDEFINED_MESSAGES)} message(s)")
    print(f"{'='*80}\n")


def diagnose_pcan():
    """Run PCAN diagnostics"""
    print("\n" + "=" * 70)
    print("PCAN DIAGNOSTICS")
    print("=" * 70)
    
    # Check python-can
    print("\n1. python-can module:")
    try:
        import can as can_module
        print(f"   \u2713 Installed (version: {can_module.__version__})")
    except ImportError:
        print(f"   \u2717 NOT INSTALLED - run: pip install python-can")
        return
    except AttributeError:
        print(f"   \u2713 Installed (version unknown)")
    
    # Check PCAN
    print("\n2. PCAN interface:")
    channels = ['PCAN_USBBUS1', 'PCAN_USBBUS2', 'PCAN_USBBUS3']
    found = False
    for channel in channels:
        try:
            bus = can.Bus(interface='pcan', channel=channel, bitrate=250000)
            print(f"   \u2713 {channel}: Connected ({bus.channel_info})")
            bus.shutdown()
            found = True
        except Exception as e:
            print(f"   \u2717 {channel}: {e}")
    
    if not found:
        print("\n   No PCAN devices found!")
        print("   - Check USB connection")
        print("   - Verify PCAN driver is installed")
        print("   - On Windows: Check Device Manager")
        print("   - On Linux: Check with 'lsusb' and 'ip link show'")
    
    # Check config
    print(f"\n3. Message configuration:")
    print(f"   Messages defined: {len(PREDEFINED_MESSAGES)}")
    for name in sorted(PREDEFINED_MESSAGES.keys()):
        print(f"   \u2022 {name}")
    
    print("\n" + "=" * 70 + "\n")


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
                    print(f"\u2717 Unknown: {msg_name}")
                    sys.exit(1)
        elif arg.upper().startswith('ID='):
            id_str = arg.split('=', 1)[1]
            try:
                target_id = int(id_str, 16) if id_str.startswith('0x') else int(id_str, 0)
            except ValueError:
                print(f"\u2717 Invalid ID: {id_str}")
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
                print(f"\u2717 Invalid DATA: {e}")
                sys.exit(1)
        elif arg.upper().startswith('TIMEOUT='):
            try:
                timeout = float(arg.split('=', 1)[1])
                if timeout < 0:
                    raise ValueError()
            except ValueError:
                print(f"\u2717 Invalid TIMEOUT")
                sys.exit(1)
    
    return monitor_mode, target_id, target_data, timeout, predefined_list, collect_all, quiet_mode


def main():
    # Check for receiver-style arguments (MSG=, ID=, DATA=)
    receiver_style = False
    for arg in sys.argv[1:]:
        if arg.upper().startswith(('MSG=', 'ID=', 'DATA=', 'TIMEOUT=')):
            receiver_style = True
            break
        if arg in ['--monitor', '-m'] and '--send' not in sys.argv and '--interactive' not in sys.argv:
            # Only treat as receiver-style if not combined with send/interactive flags
            if not any(a.startswith('--') and a not in ['--monitor', '-m', '--quiet', '-q', '--first', '-f', '--all', '-a', '--verbose', '-v', '--list', '-l'] for a in sys.argv[1:]):
                receiver_style = True
                break
    
    if receiver_style:
        monitor_mode, target_id, target_data, timeout, predefined_list, collect_all, quiet_mode = parse_receiver_style_arguments()
        
        transceiver = CANTransceiver(
            interface=CAN_CONFIG['interface'],
            channel=CAN_CONFIG['channel'],
            bitrate=CAN_CONFIG['bitrate']
        )
        
        try:
            if monitor_mode:
                transceiver.monitor_all(duration=timeout)
            elif predefined_list:
                targets = []
                for msg_name in predefined_list:
                    msg_def = PREDEFINED_MESSAGES[msg_name]
                    targets.append({
                        'id': msg_def['id'],
                        'data': msg_def.get('data_pattern'),
                        'decode_info': msg_def,
                        'name': msg_name
                    })
                
                if len(targets) == 1:
                    found = transceiver.wait_for_message(
                        targets[0]['id'],
                        targets[0]['data'],
                        timeout,
                        targets[0]['decode_info'],
                        collect_all,
                        quiet_mode
                    )
                else:
                    found = transceiver.wait_for_messages(targets, timeout, quiet_mode, collect_all)
                sys.exit(0 if found else 1)
            elif target_id is not None:
                found = transceiver.wait_for_message(target_id, target_data, timeout, None, collect_all, quiet_mode)
                sys.exit(0 if found else 1)
            else:
                print("\u2717 No target specified. Use MSG=, ID=, or --monitor")
                sys.exit(1)
        except KeyboardInterrupt:
            print("\n\n\u2713 Stopped by user (Ctrl+C)")
            sys.exit(0)
        finally:
            transceiver.close()
        return
    
    # Standard argparse mode
    parser = argparse.ArgumentParser(
        description='PCAN CAN Transceiver - Send and Receive CAN Messages',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # RECEIVER MODE
  python pcan_transceiver.py --listen MSG=BI_RESULTS
  python pcan_transceiver.py --listen BI_RESULTS,BI_USAGE --quiet
  
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
        '''
    )
    
    # Mode selection
    mode_group = parser.add_mutually_exclusive_group(required=True)
    mode_group.add_argument('--listen', type=str, metavar='MSG=NAME',
                           help='Listen mode: MSG=BI_RESULTS or BI_RESULTS,BI_USAGE')
    mode_group.add_argument('--send', action='store_true',
                           help='Send mode: send a message')
    mode_group.add_argument('--interactive', action='store_true',
                           help='Interactive mode: build and send message interactively')
    mode_group.add_argument('--monitor', action='store_true',
                           help='Monitor all CAN traffic')
    mode_group.add_argument('--list', action='store_true',
                           help='List all predefined messages')
    mode_group.add_argument('--diagnose', action='store_true',
                           help='Run PCAN diagnostics')
    
    # Send/Interactive mode options
    parser.add_argument('--msg', type=str,
                       help='Message name for sending/interactive')
    parser.add_argument('--id', type=str,
                       help='CAN ID (hex or decimal)')
    parser.add_argument('--data', type=str,
                       help='Data bytes (e.g., "01 02 03")')
    parser.add_argument('--extended', action='store_true',
                       help='Use extended 29-bit ID')
    parser.add_argument('--standard', action='store_true',
                       help='Use standard 11-bit ID')
    parser.add_argument('--now', action='store_true',
                       help='Use current time for FC 08 messages')
    parser.add_argument('--timestamp', type=int,
                       help='Timestamp for FC 08 messages')
    parser.add_argument('--datetime', type=str,
                       help='Date/time string "YYYY-MM-DD HH:MM:SS" (for FC 08)')
    
    # Listen mode options
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Quiet mode - only show matches')
    parser.add_argument('--first', '-f', action='store_true',
                       help='Stop at first match')
    parser.add_argument('--timeout', type=float, default=0,
                       help='Timeout in seconds (0=infinite)')
    
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
                    print(f"\u2717 Unknown message: {msg_name}")
                    sys.exit(1)
                msg_def = PREDEFINED_MESSAGES[msg_name]
                targets.append({
                    'id': msg_def['id'],
                    'data': msg_def.get('data_pattern'),
                    'decode_info': msg_def,
                    'name': msg_name
                })
            
            collect_all = not args.first
            if len(targets) == 1:
                found = transceiver.wait_for_message(
                    targets[0]['id'],
                    targets[0]['data'],
                    args.timeout,
                    targets[0]['decode_info'],
                    collect_all,
                    args.quiet
                )
            else:
                found = transceiver.wait_for_messages(targets, args.timeout, args.quiet, collect_all)
            sys.exit(0 if found else 1)
        
        # Send mode
        elif args.send:
            if not args.msg and not args.id:
                print("\u2717 Error: --msg or --id required in send mode")
                sys.exit(1)
            
            # Handle datetime to timestamp conversion
            timestamp = None
            if args.datetime:
                try:
                    dt = datetime.strptime(args.datetime, "%Y-%m-%d %H:%M:%S")
                    epoch_1970 = datetime(1970, 1, 1)
                    unix_timestamp = int((dt - epoch_1970).total_seconds())
                    timestamp = unix_timestamp - EPOCH_BASE
                    
                    print(f"Input datetime:     {args.datetime} (treated as UTC)")
                    print(f"Unix timestamp:     {unix_timestamp}")
                    print(f"Custom timestamp:   {timestamp} (seconds since 2016-01-01 00:00:00)")
                    
                except ValueError as e:
                    print(f"\u2717 Error: Invalid datetime format: {e}")
                    print("  Use format: YYYY-MM-DD HH:MM:SS")
                    sys.exit(1)
            elif args.timestamp:
                timestamp = args.timestamp
            
            data = None
            if args.data:
                data = transceiver.parse_data_string(args.data)
                if data is None:
                    sys.exit(1)
            
            if args.msg:
                success = transceiver.send_predefined_message(
                    args.msg.upper(),
                    data=data,
                    timestamp=timestamp,
                    use_now=args.now
                )
            else:
                can_id = parse_can_id(args.id)
                if can_id is None:
                    print(f"\u2717 Error: Invalid CAN ID: {args.id}")
                    sys.exit(1)
                if data is None:
                    print(f"\u2717 Error: Must specify --data for custom messages")
                    sys.exit(1)
                
                is_extended = True
                if args.standard:
                    is_extended = False
                elif not args.extended:
                    is_extended = (can_id > 0x7FF)
                
                success = transceiver.send_message(can_id, data, is_extended)
            
            sys.exit(0 if success else 1)
        
        # Interactive mode
        elif args.interactive:
            if args.msg:
                success = transceiver.interactive_send(msg_name=args.msg.upper())
            elif args.id:
                can_id = parse_can_id(args.id)
                if can_id is None:
                    print(f"\u2717 Error: Invalid CAN ID: {args.id}")
                    sys.exit(1)
                
                is_extended = True
                if args.standard:
                    is_extended = False
                elif not args.extended:
                    is_extended = (can_id > 0x7FF)
                
                success = transceiver.interactive_send(can_id=can_id, is_extended=is_extended)
            else:
                print("\u2717 Error: --msg or --id required in interactive mode")
                sys.exit(1)
            
            sys.exit(0 if success else 1)
        
        # Monitor mode
        elif args.monitor:
            transceiver.monitor_all(duration=args.timeout)
    
    except KeyboardInterrupt:
        print("\n\n\u2713 Stopped by user (Ctrl+C)")
        sys.exit(0)
    finally:
        transceiver.close()


if __name__ == '__main__':
    main()