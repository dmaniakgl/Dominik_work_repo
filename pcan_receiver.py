#!/usr/bin/env python3
"""
PCAN CAN Message Receiver & Monitor - Production Ready
Purpose: Monitor CAN bus and collect messages during long cycles (multi-message support)

Usage:
    python pcan_receiver.py MSG=BI_RESULTS                      # Single message
    python pcan_receiver.py MSG=BI_RESULTS,BI_USAGE             # Multiple messages
    python pcan_receiver.py MSG=BI_RESULTS,BI_USAGE --quiet     # Quiet mode
    python pcan_receiver.py --list                               # List all messages

Install: pip install python-can
"""

import sys
import time
from datetime import datetime

try:
    import can
except ImportError:
    print("ERROR: python-can module not found!")
    print("Please install it using: pip install python-can")
    sys.exit(1)

try:
    from can_messages_config import PREDEFINED_MESSAGES
except ImportError:
    print("ERROR: can_messages_config.py not found!")
    print("Please ensure can_messages_config.py is in the same directory as this script.")
    sys.exit(1)


# ==================== CONFIGURATION ====================

CONFIG = {
    'interface': 'pcan',
    'channel': 'PCAN_USBBUS1',
    'bitrate': 250000,
    'timeout': 0,
    'collect_all': True,
    'quiet_mode': False,
}


class CANReceiver:
    """CAN message receiver and monitor"""
    
    def __init__(self, interface, channel, bitrate):
        self.bus = None
        try:
            self.bus = can.Bus(interface=interface, channel=channel, bitrate=bitrate)
            print(f"✓ Connected: {self.bus.channel_info}")
        except can.CanError as e:
            print(f"✗ Connection failed: {e}")
            print("\nTroubleshooting:")
            print("1. Check PCAN device is connected")
            print("2. Verify PCAN driver is installed")
            print("3. Ensure no other application is using the device")
            sys.exit(1)
        except Exception as e:
            print(f"✗ Unexpected error: {e}")
            sys.exit(1)
    
    def monitor_all(self, duration=0):
        """Monitor all CAN traffic"""
        print(f"\n{'='*80}")
        print("CAN BUS MONITOR")
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
                
                msg = self.bus.recv(timeout=0.1)
                if msg is None:
                    continue
                
                msg_count += 1
                self._print_message(msg)
                
        except KeyboardInterrupt:
            print(f"\n\n✓ Stopped by user")
        
        elapsed = time.time() - start_time
        print(f"\n{'='*80}")
        print(f"Messages: {msg_count}, Duration: {elapsed:.2f}s")
        print(f"{'='*80}\n")
    
    def wait_for_messages(self, targets, timeout=0, quiet_mode=False, collect_all=True):
        """Wait for multiple CAN messages"""
        
        print(f"\n{'='*80}")
        print(f"MONITORING MULTIPLE MESSAGES")
        print(f"{'='*80}")
        print(f"Targets: {len(targets)} | Mode: {'COLLECT ALL' if collect_all else 'STOP AT FIRST'}")
        print(f"Display: {'QUIET' if quiet_mode else 'VERBOSE'} | Timeout: {'∞' if timeout == 0 else f'{timeout}s'}")
        print(f"{'='*80}\n")
        
        for i, target in enumerate(targets, 1):
            data_str = "ANY" if target['data'] is None else self._format_data_pattern(target['data'])
            print(f"Target {i}: {target.get('name', 'Unknown')}")
            print(f"  ID: 0x{target['id']:X} | Data: {data_str}")
        
        print(f"\n{'='*80}\n")
        
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
                
                msg = self.bus.recv(timeout=0.1)
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
            print(f"\n\n✓ Stopped by user")
        
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
    
    def wait_for_message(self, target_id, target_data=None, timeout=0, decode_info=None, collect_all=True, quiet_mode=False):
        """Wait for single CAN message"""
        
        data_str = "ANY" if target_data is None else self._format_data_pattern(target_data)
        
        print(f"\n{'='*80}")
        print(f"MONITORING SINGLE MESSAGE")
        print(f"{'='*80}")
        print(f"ID: 0x{target_id:X} | Data: {data_str}")
        print(f"Mode: {'COLLECT ALL' if collect_all else 'STOP AT FIRST'} | Display: {'QUIET' if quiet_mode else 'VERBOSE'}")
        print(f"Timeout: {'∞' if timeout == 0 else f'{timeout}s'}")
        
        if decode_info and 'description' in decode_info:
            print(f"Desc: {decode_info['description']}")
        
        print(f"{'='*80}\n")
        
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
                
                msg = self.bus.recv(timeout=0.1)
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
            print(f"\n\n✓ Stopped by user")
        
        elapsed = time.time() - start_time
        print(f"\n{'='*80}")
        print(f"SUMMARY: {elapsed:.2f}s | Messages: {msg_count} | Matches: {match_count}")
        print(f"{'='*80}\n")
        
        return match_count > 0
    
    def _decode_special_fields(self, msg, special_decode):
        """Generic decoder for special fields"""
        decoded = {}
        
        for field_name, field_info in special_decode.items():
            try:
                field_type = field_info['type']
                
                if field_type == '16bit':
                    bytes_idx = field_info['bytes']
                    if len(msg.data) > max(bytes_idx):
                        if field_info.get('endian', 'little') == 'little':
                            value = (msg.data[bytes_idx[1]] << 8) | msg.data[bytes_idx[0]]
                        else:
                            value = (msg.data[bytes_idx[0]] << 8) | msg.data[bytes_idx[1]]
                        decoded[field_name] = {
                            'value': value,
                            'hex': f'0x{value:04X}',
                            'description': field_info['description']
                        }
                
                elif field_type == '32bit':
                    bytes_idx = field_info['bytes']
                    if len(msg.data) > max(bytes_idx):
                        if field_info.get('endian', 'little') == 'little':
                            value = (msg.data[bytes_idx[3]] << 24) | (msg.data[bytes_idx[2]] << 16) | \
                                    (msg.data[bytes_idx[1]] << 8) | msg.data[bytes_idx[0]]
                        else:
                            value = (msg.data[bytes_idx[0]] << 24) | (msg.data[bytes_idx[1]] << 16) | \
                                    (msg.data[bytes_idx[2]] << 8) | msg.data[bytes_idx[3]]
                        decoded[field_name] = {
                            'value': value,
                            'hex': f'0x{value:08X}',
                            'description': field_info['description']
                        }
                
                elif field_type == '16bit_signed':
                    bytes_idx = field_info['bytes']
                    if len(msg.data) > max(bytes_idx):
                        if field_info.get('endian', 'little') == 'little':
                            raw_value = (msg.data[bytes_idx[1]] << 8) | msg.data[bytes_idx[0]]
                        else:
                            raw_value = (msg.data[bytes_idx[0]] << 8) | msg.data[bytes_idx[1]]
                        
                        value = raw_value if raw_value < 0x8000 else raw_value - 0x10000
                        decoded[field_name] = {'value': value, 'description': field_info['description']}
                        
                        if 'status_func' in field_info:
                            decoded[field_name]['status'] = field_info['status_func'](value)
                
                elif field_type == 'nibble_lower':
                    byte_idx = field_info['byte']
                    if len(msg.data) > byte_idx:
                        lower = msg.data[byte_idx] & 0x0F
                        upper = (msg.data[byte_idx] >> 4) & 0x0F
                        decoded[field_name] = {
                            'value': lower,
                            'upper_nibble': upper,
                            'description': field_info['description']
                        }
                        if 'values' in field_info:
                            decoded[field_name]['text'] = field_info['values'].get(lower, 'Unknown')
                
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
                        
                        if 'hex' in data and 'text' in data:
                            print(f"    {desc}: {data['value']} ({data['hex']}) = {data['text']}")
                        elif 'hex' in data:
                            print(f"    {desc}: {data['value']} ({data['hex']})")
                        elif 'text' in data and 'upper_nibble' in data:
                            print(f"    {desc}:")
                            print(f"      Upper: 0x{data['upper_nibble']:X} | Lower: 0x{data['value']:X} = {data['text']}")
                        elif 'status' in data:
                            print(f"    {desc}: {data['value']} days → {data['status']}")
                        elif 'bit_position' in data:
                            print(f"    {desc}:")
                            print(f"      Byte Value: 0x{data['byte_value']:02X}")
                            print(f"      Bit {data['bit_position']}: {data['value']} = {data.get('text', data['value'])}")
                        else:
                            print(f"    {desc}: {data['value']}")
        
        print(f"{'-'*80}\n")
    
    def _check_match(self, msg, target_id, target_data):
        """Check if message matches target"""
        if msg.arbitration_id != target_id:
            return False
        if target_data is None:
            return True
        if len(msg.data) != len(target_data):
            return False
        for i, expected in enumerate(target_data):
            if expected is not None and (i >= len(msg.data) or msg.data[i] != expected):
                return False
        return True
    
    def _print_message(self, msg, match=None):
        """Print CAN message"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        id_str = f"0x{msg.arbitration_id:X}"
        msg_type = "Ext" if msg.is_extended_id else "Std"
        data = ' '.join(f'{b:02X}' for b in msg.data) if len(msg.data) > 0 else ""
        match_str = "✓ MATCH" if match else ""
        print(f"{ts:<26} {id_str:<12} {msg_type:<6} {msg.dlc:<4} {data:<30} {match_str}")
    
    def _print_message_multi(self, msg, match=None, match_name=None):
        """Print CAN message with multi-target indicator"""
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        id_str = f"0x{msg.arbitration_id:X}"
        msg_type = "Ext" if msg.is_extended_id else "Std"
        data = ' '.join(f'{b:02X}' for b in msg.data) if len(msg.data) > 0 else ""
        match_str = f"✓ {match_name}" if (match and match_name) else ("✓ MATCH" if match else "")
        print(f"{ts:<26} {id_str:<12} {msg_type:<6} {msg.dlc:<4} {data:<30} {match_str}")
    
    def _format_data_pattern(self, data_pattern):
        """Format data pattern for display"""
        if data_pattern is None:
            return "ANY"
        parts = ['XX' if b is None else f'{b:02X}' for b in data_pattern]
        return "[" + " ".join(parts) + "]"
    
    def close(self):
        """Close CAN bus"""
        if self.bus:
            try:
                self.bus.shutdown()
                print("✓ Disconnected")
            except Exception as e:
                print(f"⚠ Disconnect warning: {e}")


def parse_arguments():
    """Parse command line arguments"""
    target_id = None
    target_data = None
    monitor_mode = False
    timeout = CONFIG['timeout']
    predefined_list = []
    collect_all = CONFIG['collect_all']
    quiet_mode = CONFIG['quiet_mode']
    
    for arg in sys.argv[1:]:
        if arg in ['--monitor', '-m']:
            monitor_mode = True
        elif arg in ['--list', '-l']:
            print_predefined_messages()
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


def print_predefined_messages():
    """Print predefined messages"""
    print("\n" + "="*80)
    print("PREDEFINED MESSAGES")
    print("="*80)
    for name, msg_def in PREDEFINED_MESSAGES.items():
        print(f"\n{name}: {msg_def['description']}")
        print(f"  ID: 0x{msg_def['id']:X}")
    print("\n" + "="*80 + "\n")


def print_usage():
    """Print usage"""
    print("PCAN CAN Receiver")
    print("="*80)
    print("\nUsage:")
    print("  python pcan_receiver.py MSG=BI_RESULTS --quiet")
    print("  python pcan_receiver.py MSG=BI_RESULTS,BI_USAGE --quiet")
    print("  python pcan_receiver.py --list")
    print("\n" + "="*80)


def main():
    """Main function"""
    try:
        monitor_mode, target_id, target_data, timeout, predefined_list, collect_all, quiet_mode = parse_arguments()
        
        if not monitor_mode and target_id is None and len(predefined_list) == 0:
            print("✗ No target specified!\n")
            print_usage()
            sys.exit(1)
        
        receiver = CANReceiver(CONFIG['interface'], CONFIG['channel'], CONFIG['bitrate'])
        
        try:
            if monitor_mode:
                receiver.monitor_all(duration=timeout)
                sys.exit(0)
            elif len(predefined_list) > 1:
                targets = []
                for msg_name in predefined_list:
                    msg_def = PREDEFINED_MESSAGES[msg_name]
                    targets.append({
                        'id': msg_def['id'],
                        'data': msg_def.get('data_pattern'),
                        'decode_info': msg_def,
                        'name': msg_name
                    })
                found = receiver.wait_for_messages(targets, timeout, quiet_mode, collect_all)
                sys.exit(0 if found else 1)
            else:
                decode_info = None
                if len(predefined_list) == 1:
                    msg_def = PREDEFINED_MESSAGES[predefined_list[0]]
                    target_id = msg_def['id']
                    target_data = msg_def.get('data_pattern')
                    decode_info = msg_def
                found = receiver.wait_for_message(target_id, target_data, timeout, decode_info, collect_all, quiet_mode)
                sys.exit(0 if found else 1)
        except KeyboardInterrupt:
            print("\n✓ Stopped by user")
            sys.exit(0)
        finally:
            receiver.close()
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()