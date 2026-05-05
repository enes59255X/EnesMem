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


def test_string_scan():
    mem_data = bytearray(100)
    # Write some strings
    mem_data[10:15] = b"Hello"
    mem_data[50:55] = b"World"
    
    mem = DummyMemory(mem_data)
    scanner = Scanner(mem)

    # String scan for 'Hello'
    found = scanner.first_scan(DataType.STRING, ScanMode.EXACT, "Hello")
    assert found == 1
    
    results = scanner.get_results()
    assert results[0].address == 0x1000 + 10

def test_unknown_initial_value_scan():
    mem_data = bytearray(100)
    struct.pack_into("<i", mem_data, 20, 100) # int at 20 is 100
    struct.pack_into("<i", mem_data, 60, 200) # int at 60 is 200

    mem = DummyMemory(mem_data)
    scanner = Scanner(mem)

    # Unknown Initial Value scan for INT32
    # Expect count of chunks saved
    scanner.first_scan(DataType.INT32, ScanMode.UNKNOWN)
    
    # After first UIV scan, chunks are saved to disk (_uiv_index tracks them)
    assert scanner.result_count == 0
    assert len(scanner._uiv_index) == 1  # one chunk was saved to disk

    # Modify memory
    struct.pack_into("<i", mem_data, 20, 150) # Increased
    struct.pack_into("<i", mem_data, 60, 190) # Decreased

    # Next Scan: Increased
    scanner.next_scan(ScanMode.INCREASED)
    assert scanner.result_count == 1
    assert scanner.get_results()[0].address == 0x1000 + 20
    assert scanner.get_results()[0].current_value(DataType.INT32) == 150
