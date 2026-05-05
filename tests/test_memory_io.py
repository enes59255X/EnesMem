"""
test_memory_io.py — Integration tests for MemoryIO using test_app.py as target.

Run AFTER starting test_app.py in a separate terminal:
    python test_app.py

Then run:
    python -m pytest tests/test_memory_io.py -v
"""
import ctypes
import os
import struct
import subprocess
import sys
import time
import unittest

# Must find test_app PID and its address somehow.
# For automated testing we spawn test_app and parse its stdout.

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from core.process_manager import ProcessManager
from core.memory_io import MemoryIO
from utils.patterns import DataType


def _spawn_test_app() -> tuple[subprocess.Popen, int, int]:
    """
    Spawn test_app.py, parse its PID and address from stdout.
    Returns (proc, pid, addr).
    """
    proc = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, "test_app.py")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    # Read header lines until we have PID and Address
    pid, addr = None, None
    deadline = time.time() + 5.0
    while time.time() < deadline:
        line = proc.stdout.readline()
        if "PID" in line:
            pid = int(line.split(":")[1].strip())
        if "Address" in line:
            addr = int(line.split(":")[1].strip(), 16)
        if pid and addr:
            break
    return proc, pid, addr


class TestMemoryIO(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.proc, cls.pid, cls.addr = _spawn_test_app()
        if not cls.pid or not cls.addr:
            raise RuntimeError("Could not parse test_app output")

        pm = ProcessManager()
        ok = pm.open_process(cls.pid)
        if not ok:
            raise PermissionError(
                f"Cannot open PID {cls.pid}. Run as Administrator."
            )
        cls.pm   = pm
        cls.mem  = MemoryIO(pm.handle, pm.is_64bit)
        time.sleep(0.2)

    @classmethod
    def tearDownClass(cls):
        cls.pm.close_handle()
        cls.proc.terminate()
        cls.proc.wait(2)

    def test_read_int32(self):
        val = self.mem.read_int(self.addr, size=4, signed=True)
        self.assertIsNotNone(val, "read_int returned None")
        self.assertEqual(val, 1000, f"Expected 1000, got {val}")

    def test_read_value_int32(self):
        val = self.mem.read_value(self.addr, DataType.INT32)
        self.assertIsNotNone(val)
        self.assertIsInstance(val, int)
        self.assertEqual(val, 1000)

    def test_write_and_read_back(self):
        new_val = 9999
        ok = self.mem.write_value(self.addr, new_val, DataType.INT32)
        self.assertTrue(ok, "write_value failed")
        time.sleep(0.05)
        read_back = self.mem.read_int(self.addr, size=4, signed=True)
        self.assertEqual(read_back, new_val, f"Expected {new_val}, got {read_back}")

    def test_read_bytes_length(self):
        raw = self.mem.read_bytes(self.addr, 4)
        self.assertIsNotNone(raw)
        self.assertEqual(len(raw), 4)

    def test_region_enumeration(self):
        regions = self.mem.get_regions()
        self.assertGreater(len(regions), 0)
        # All regions should be non-zero size
        for r in regions:
            self.assertGreater(r.size, 0)

    def test_write_float(self):
        # Write a float to a test address — verify via read_float
        val = 3.14
        raw = struct.pack("<f", val)
        ok = self.mem.write_bytes(self.addr, raw)
        self.assertTrue(ok)
        result = self.mem.read_float(self.addr)
        self.assertAlmostEqual(result, val, places=4)

    def tearDown(self):
        # Reset counter to 1000 after each test
        self.mem.write_value(self.addr, 1000, DataType.INT32)
        time.sleep(0.02)


if __name__ == "__main__":
    unittest.main(verbosity=2)
