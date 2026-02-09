"""
CAN Messages Configuration File
Contains all predefined CAN message definitions for PCAN receiver

Add new message definitions here following the same structure.
"""

PREDEFINED_MESSAGES = {
    'BI_RESULTS': {
        'description': 'FC 46: BI Results (Biological Indicator Results)',
        'id': 0x102E0900,  # Extended ID: 0x102EXY00, XY=09 (Display)
        'extended': True,
        'data_pattern': None,  # Match ANY data from this ID
        'data_description': {
            0: 'Cycle Number (Bits 0-7)',
            1: 'Cycle Number (Bits 8-15)',
            2: 'Unused (Upper Nibble) | BI Result (Lower Nibble)',
            3: 'Time/Date Stamp (Bits 0-7)',
            4: 'Time/Date Stamp (Bits 8-15)',
            5: 'Time/Date Stamp (Bits 16-23)',
            6: 'Time/Date Stamp (Bits 24-31)',
            7: 'Cycle Status',
        },
        'special_decode': {
            'cycle_number': {
                'type': '16bit',
                'bytes': [0, 1],  # Data 1-2
                'endian': 'little',
                'description': 'Combined Cycle Number'
            },
            'bi_result': {
                'type': 'nibble_lower',
                'byte': 2,  # Data 3
                'description': 'BI Result',
                'values': {0: 'Fail', 1: 'Pass', 2: 'Pending', 3: 'Unknown'}
            },
            'timestamp': {
                'type': '32bit',
                'bytes': [3, 4, 5, 6],  # Data 4-7
                'endian': 'little',
                'description': 'Combined Time/Date Stamp'
            },
            'cycle_status': {
                'type': 'byte_enum',
                'byte': 7,  # Data 8
                'description': 'Cycle Status',
                'values': {0: 'Completed', 1: 'Failed', 2: 'Interrupted', 3: 'Pending'}
            }
        },
        'notes': [
            'Origin: Display Interface (Node ID: 0x09)',
            'Destination: Connectivity Module (Node ID: 0x11 / 17 decimal)',
            'BI Result (Data 3 lower nibble): 0=Fail, 1=Pass, 2=Pending, 3=Unknown',
            'Cycle Status (Data 8): 0=Completed, 1=Failed, 2=Interrupted, 3=Pending',
        ]
    },
    
    'BI_USAGE': {
        'description': 'FC 78: BI Usage Notification (Due Date Indicator)',
        'id': 0x104E0900,  # Extended ID: 0x104EXY00, XY=09 (Display)
        'extended': True,
        'data_pattern': None,  # Match ANY data from this ID
        'data_description': {
            0: 'Days from Due (Bits 0-7) - signed 16-bit',
            1: 'Days from Due (Bits 8-15) - signed 16-bit',
        },
        'special_decode': {
            'days_from_due': {
                'type': '16bit_signed',
                'bytes': [0, 1],  # Data 1-2
                'endian': 'little',
                'description': 'Days from Due',
                'status_func': lambda val: 'OVERDUE by {} days'.format(abs(val)) if val < 0 else ('DUE TODAY' if val == 0 else 'Due in {} days'.format(val))
            }
        },
        'notes': [
            'Origin: Display Interface (Node ID: 0x09)',
            'Destination: Cloud/Connectivity Module',
            'Days from Due: 0=Due today, Negative=Overdue, Positive=Future',
        ]
    },
    
    'CURRENT_DATETIME_CONNECTIVITY': {
        'description': 'FC 08: Current Date/Time from Connectivity (Node 0x11)',
        'id': 0x10081100,  # Extended ID: 0x1008XY00, XY=11 (Connectivity Interface - Node 17 decimal)
        'extended': True,
        'data_pattern': None,  # Match ANY data from this ID
        'data_description': {
            0: 'Date/Time Stamp (Bits 0-7)',
            1: 'Date/Time Stamp (Bits 8-15)',
            2: 'Date/Time Stamp (Bits 16-23)',
            3: 'Date/Time Stamp (Bits 24-31)',
            4: 'Reserved/Unused',
        },
        'special_decode': {
            'timestamp': {
                'type': '32bit',
                'bytes': [0, 1, 2, 3],  # Data 1-4
                'endian': 'little',
                'description': 'Seconds since 2016-01-01 00:00:00',
                'epoch_base': 1451606400  # Unix timestamp for 2016-01-01 00:00:00 UTC
            }
        },
        'notes': [
            'Origin: Connectivity Interface (Node ID: 0x11 / 17 decimal)',
            'Timestamp: Raw seconds since 01/01/2016 @ 00:00:00',
            'Base epoch: 1451606400 (Unix timestamp for 2016-01-01)',
        ]
    },
    
    'CURRENT_DATETIME_DISPLAY': {
        'description': 'FC 08: Current Date/Time from Display (Node 0x09)',
        'id': 0x10080900,  # Extended ID: 0x1008XY00, XY=09 (Display)
        'extended': True,
        'data_pattern': None,  # Match ANY data from this ID
        'data_description': {
            0: 'Date/Time Stamp (Bits 0-7)',
            1: 'Date/Time Stamp (Bits 8-15)',
            2: 'Date/Time Stamp (Bits 16-23)',
            3: 'Date/Time Stamp (Bits 24-31)',
            4: 'Reserved/Unused',
        },
        'special_decode': {
            'timestamp': {
                'type': '32bit',
                'bytes': [0, 1, 2, 3],  # Data 1-4
                'endian': 'little',
                'description': 'Seconds since 2016-01-01 00:00:00',
                'epoch_base': 1451606400  # Unix timestamp for 2016-01-01 00:00:00 UTC
            }
        },
        'notes': [
            'Origin: Display Interface (Node ID: 0x09)',
            'Timestamp: Raw seconds since 01/01/2016 @ 00:00:00',
            'Base epoch: 1451606400 (Unix timestamp for 2016-01-01)',
        ]
    },
    
    'CURRENT_DATETIME_CONTROL': {
        'description': 'FC 08: Current Date/Time from Control Board (Node 0x07)',
        'id': 0x10080700,  # Extended ID: 0x1008XY00, XY=07 (Control Board)
        'extended': True,
        'data_pattern': None,  # Match ANY data from this ID
        'data_description': {
            0: 'Date/Time Stamp (Bits 0-7)',
            1: 'Date/Time Stamp (Bits 8-15)',
            2: 'Date/Time Stamp (Bits 16-23)',
            3: 'Date/Time Stamp (Bits 24-31)',
            4: 'Reserved/Unused',
        },
        'special_decode': {
            'timestamp': {
                'type': '32bit',
                'bytes': [0, 1, 2, 3],  # Data 1-4
                'endian': 'little',
                'description': 'Seconds since 2016-01-01 00:00:00',
                'epoch_base': 1451606400  # Unix timestamp for 2016-01-01 00:00:00 UTC
            }
        },
        'notes': [
            'Origin: Control Board (Node ID: 0x07)',
            'Timestamp: Raw seconds since 01/01/2016 @ 00:00:00',
            'Base epoch: 1451606400 (Unix timestamp for 2016-01-01)',
        ]
    },
    
    'CURRENT_DATETIME_SENSOR_CONTROL': {
        'description': 'FC 08: Current Date/Time from Sensor Control (Node 0x1E)',
        'id': 0x10081E00,  # Extended ID: 0x1008XY00, XY=1E (Sensor Control)
        'extended': True,
        'data_pattern': None,  # Match ANY data from this ID
        'data_description': {
            0: 'Date/Time Stamp (Bits 0-7)',
            1: 'Date/Time Stamp (Bits 8-15)',
            2: 'Date/Time Stamp (Bits 16-23)',
            3: 'Date/Time Stamp (Bits 24-31)',
            4: 'Reserved/Unused',
        },
        'special_decode': {
            'timestamp': {
                'type': '32bit',
                'bytes': [0, 1, 2, 3],  # Data 1-4
                'endian': 'little',
                'description': 'Seconds since 2016-01-01 00:00:00',
                'epoch_base': 1451606400  # Unix timestamp for 2016-01-01 00:00:00 UTC
            }
        },
        'notes': [
            'Origin: Sensor Control (Node ID: 0x1E / 30)',
            'Timestamp: Raw seconds since 01/01/2016 @ 00:00:00',
            'Base epoch: 1451606400 (Unix timestamp for 2016-01-01)',
        ]
    },
    
    'PRODUCT_IN_USE': {
        'description': 'FC 99: Product In-Use Status',
        'id': 0x10630900,  # Extended ID: 0x1063XY00, XY=09 (Display)
        'extended': True,
        'data_pattern': None,  # Match ANY data from this ID
        'data_description': {
            0: 'In Use Status (Bit 0: 0=Not in Use, 1=In Use)',
        },
        'special_decode': {
            'in_use_status': {
                'type': 'bit_field',
                'byte': 0,
                'bit': 0,  # Bit 0
                'description': 'Product In-Use Status',
                'values': {0: 'Not in Use', 1: 'In Use'}
            }
        },
        'notes': [
            'Origin: Display (Node ID: 0x09)',
            'Reports whether the product is currently in use',
            'Bit 0: 0=Not in Use, 1=In Use',
            'DLC: 1 byte',
        ]
    },
    
    'DISPLAY_SUCCESS': {
        'description': 'Display Update Success Message',
        'id': 0x114F0900,
        'extended': True,
        'data_pattern': [0xFF, 0x00, 0x81],
        'data_description': {
            0: 'Status Flag (0xFF = Success)',
            1: 'Reserved (0x00)',
            2: 'Message Type (0x81)',
        },
        'notes': ['Indicates successful firmware update completion']
    },
    
    'DISPLAY_ERROR': {
        'description': 'Display Update Error Message',
        'id': 0x114F0900,
        'extended': True,
        'data_pattern': [0xFF, 0x00, 0x81],
        'data_description': {
            0: 'Status Flag (0xFF = Error)',
            1: 'Reserved (0x00)',
            2: 'Message Type (0x81)',
        },
        'notes': ['Indicates firmware update failure']
    },
}


# ==================== HOW TO ADD NEW MESSAGES ====================
"""
To add a new CAN message definition, copy this template:

'YOUR_MESSAGE_NAME': {
    'description': 'Your message description',
    'id': 0x12345678,  # CAN ID in hex
    'extended': True,  # True for 29-bit ID, False for 11-bit ID
    'data_pattern': None,  # None = match any data, or [0x01, 0x02, None, ...] for specific pattern
    'data_description': {
        0: 'Description of Data byte 1',
        1: 'Description of Data byte 2',
        # ... add more as needed
    },
    'special_decode': {
        'field_name': {
            'type': '16bit',  # Options: 16bit, 32bit, 16bit_signed, nibble_lower, nibble_upper, byte_enum
            'bytes': [0, 1],  # Which bytes to combine
            'endian': 'little',  # 'little' or 'big'
            'description': 'Field description'
        },
        # Add more fields as needed
    },
    'notes': [
        'Additional notes about this message',
    ]
},

DECODER TYPES AVAILABLE:
- '16bit': 16-bit unsigned integer (2 bytes)
- '32bit': 32-bit unsigned integer (4 bytes)
- '16bit_signed': 16-bit signed integer (2 bytes)
- 'nibble_lower': Lower 4 bits of a byte
- 'nibble_upper': Upper 4 bits of a byte
- 'byte_enum': Single byte with value mapping

EXAMPLE - Adding a temperature sensor message:

'TEMP_SENSOR': {
    'description': 'Temperature Sensor Data',
    'id': 0x200,
    'extended': False,
    'data_pattern': None,
    'data_description': {
        0: 'Temperature (Bits 0-7)',
        1: 'Temperature (Bits 8-15)',
        2: 'Sensor Status',
    },
    'special_decode': {
        'temperature': {
            'type': '16bit',
            'bytes': [0, 1],
            'endian': 'big',
            'description': 'Temperature (°C)'
        },
        'status': {
            'type': 'byte_enum',
            'byte': 2,
            'description': 'Sensor Status',
            'values': {0: 'OK', 1: 'Warning', 2: 'Error'}
        }
    },
    'notes': ['Temperature in Celsius * 10']
},
"""