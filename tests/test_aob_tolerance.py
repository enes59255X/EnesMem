import pytest
import struct
from core.scanner import Scanner
from utils.patterns import DataType, ScanMode

class DummyRegion:
    def __init__(self, base, size):
        self.base_address = base
        self.size = size

class DummyMemory:
    def __init__(self, data: bytearray):
        self._data = data
        self._ptr_size = 8  # Simulate 64-bit process

    def get_regions(self, writable_only=False):
        return [DummyRegion(0x1000, len(self._data))]

    def read_region_chunked(self, region, chunk_size=1024):
        yield region.base_address, bytes(self._data)

    def read_bytes(self, address, size):
        offset = address - 0x1000
        if 0 <= offset <= len(self._data) - size:
            return bytes(self._data[offset:offset+size])
        return None

    def write_bytes(self, address, data):
        offset = address - 0x1000
        if 0 <= offset <= len(self._data) - len(data):
            self._data[offset:offset+len(data)] = data
            return True
        return False

def test_aob_scan():
    mem_data = bytearray(100)
    # Write a pattern: 55 8B EC 01 02 8B 45 08
    pattern_bytes = b"\x55\x8B\xEC\x01\x02\x8B\x45\x08"
    mem_data[30:30+len(pattern_bytes)] = pattern_bytes

    # Write another one that is similar but different at wildcard places:
    # 55 8B EC FF FF 8B 45 08
    pattern_bytes_2 = b"\x55\x8B\xEC\xFF\xFF\x8B\x45\x08"
    mem_data[70:70+len(pattern_bytes_2)] = pattern_bytes_2

    mem = DummyMemory(mem_data)
    scanner = Scanner(mem)

    # Search for EXACT AOB
    found = scanner.first_scan(DataType.BYTES, ScanMode.AOB, value=b"\x55\x8B\xEC\x01\x02\x8B\x45\x08")
    assert found == 1
    assert scanner.get_results()[0].address == 0x1000 + 30

    # Search for AOB with wildcard mask
    # We pass a tuple: (pattern, mask)
    # 55 8B EC ? ? 8B 45 08
    search_pattern = b"\x55\x8B\xEC\x00\x00\x8B\x45\x08"
    search_mask = "xxx??xxx"
    
    found_wildcard = scanner.first_scan(DataType.BYTES, ScanMode.AOB, value=(search_pattern, search_mask))
    assert found_wildcard == 2
    addresses = [r.address for r in scanner.get_results()]
    assert 0x1000 + 30 in addresses
    assert 0x1000 + 70 in addresses

def test_float_tolerance_scan():
    mem_data = bytearray(100)
    # Write some floats
    struct.pack_into("<f", mem_data, 20, 10.12345)
    struct.pack_into("<f", mem_data, 40, 10.12399)
    struct.pack_into("<f", mem_data, 60, 10.20000)

    mem = DummyMemory(mem_data)
    scanner = Scanner(mem)

    # First scan with small tolerance
    found = scanner.first_scan(DataType.FLOAT, ScanMode.FLOAT_TOLERANCE, value=10.123, tolerance=0.001)
    # Should match 10.12345 (diff: 0.00045) and 10.12399 (diff: 0.00099)
    assert found == 2
    addresses = [r.address for r in scanner.get_results()]
    assert 0x1000 + 20 in addresses
    assert 0x1000 + 40 in addresses

    # Next scan: value changed to 20.5 with tolerance 0.1
    struct.pack_into("<f", mem_data, 20, 20.55)
    struct.pack_into("<f", mem_data, 40, 20.70)
    
    found_next = scanner.next_scan(ScanMode.FLOAT_TOLERANCE, value=20.5, tolerance=0.1)
    # Should match only 20.55 (diff 0.05), not 20.70 (diff 0.20)
    assert found_next == 1
    assert scanner.get_results()[0].address == 0x1000 + 20

def test_string_null_terminator():
    # Verify that string search doesn't require a null terminator
    mem_data = bytearray(b"HEADER_MY_STRING_TRAILER") # No nulls around MY_STRING
    mem = DummyMemory(mem_data)
    scanner = Scanner(mem)
    
    # Search for 'MY_STRING'
    found = scanner.first_scan(DataType.STRING, ScanMode.EXACT, "MY_STRING")
    assert found == 1
    assert scanner.get_results()[0].address == 0x1000 + 7

def test_utf16_scan():
    # Verify UTF-16LE scan
    text = "Hello16"
    encoded = text.encode("utf-16-le")
    mem_data = bytearray(100)
    mem_data[40:40+len(encoded)] = encoded
    
    mem = DummyMemory(mem_data)
    scanner = Scanner(mem)
    
    found = scanner.first_scan(DataType.STRING16, ScanMode.EXACT, text)
    assert found == 1
    assert scanner.get_results()[0].address == 0x1000 + 40
