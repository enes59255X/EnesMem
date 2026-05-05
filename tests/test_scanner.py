"""
test_scanner.py — Integration tests for the scan engine.

Spawns test_app.py, performs first/next scans, verifies results.
Requires Administrator privileges (for ReadProcessMemory).

Run:
    python -m pytest tests/test_scanner.py -v
"""
import os
import sys
import subprocess
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, ROOT)

from core.process_manager import ProcessManager
from core.memory_io import MemoryIO
from core.scanner import Scanner
from utils.patterns import DataType, ScanMode


def _spawn_test_app():
    proc = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, "test_app.py")],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    )
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


class TestScanner(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.proc, cls.pid, cls.addr = _spawn_test_app()
        if not cls.pid or not cls.addr:
            raise RuntimeError("Cannot parse test_app output")
        pm = ProcessManager()
        if not pm.open_process(cls.pid):
            raise PermissionError("Run as Administrator")
        cls.pm      = pm
        cls.mem     = MemoryIO(pm.handle, pm.is_64bit)
        cls.scanner = Scanner(cls.mem)
        time.sleep(0.3)

    @classmethod
    def tearDownClass(cls):
        cls.pm.close_handle()
        cls.proc.terminate()
        cls.proc.wait(2)

    def setUp(self):
        # Reset value + scanner before each test
        self.mem.write_value(self.addr, 1000, DataType.INT32)
        self.scanner.reset()
        time.sleep(0.05)

    def test_first_scan_exact_finds_address(self):
        count = self.scanner.first_scan(DataType.INT32, ScanMode.EXACT, 1000)
        self.assertGreater(count, 0, "First scan returned 0 results")
        addrs = [r.address for r in self.scanner.get_results()]
        self.assertIn(self.addr, addrs, "Known address not in results")

    def test_next_scan_narrows_results(self):
        self.scanner.first_scan(DataType.INT32, ScanMode.EXACT, 1000)
        first_count = self.scanner.result_count

        # Change value and next-scan
        self.mem.write_value(self.addr, 2500, DataType.INT32)
        time.sleep(0.05)
        self.scanner.next_scan(ScanMode.EXACT, 2500)
        second_count = self.scanner.result_count

        self.assertLess(second_count, first_count, "Next scan should reduce results")
        addrs = [r.address for r in self.scanner.get_results()]
        self.assertIn(self.addr, addrs)

    def test_scan_increased(self):
        self.scanner.first_scan(DataType.INT32, ScanMode.UNKNOWN)
        self.mem.write_value(self.addr, 5000, DataType.INT32)
        time.sleep(0.05)
        self.scanner.next_scan(ScanMode.INCREASED)
        addrs = [r.address for r in self.scanner.get_results()]
        self.assertIn(self.addr, addrs)

    def test_scan_decreased(self):
        self.scanner.first_scan(DataType.INT32, ScanMode.UNKNOWN)
        self.mem.write_value(self.addr, 50, DataType.INT32)
        time.sleep(0.05)
        self.scanner.next_scan(ScanMode.DECREASED)
        addrs = [r.address for r in self.scanner.get_results()]
        self.assertIn(self.addr, addrs)

    def test_scan_unchanged(self):
        self.scanner.first_scan(DataType.INT32, ScanMode.EXACT, 1000)
        # Do not change value
        time.sleep(0.05)
        self.scanner.next_scan(ScanMode.UNCHANGED)
        addrs = [r.address for r in self.scanner.get_results()]
        self.assertIn(self.addr, addrs)

    def test_reset_clears_results(self):
        self.scanner.first_scan(DataType.INT32, ScanMode.EXACT, 1000)
        self.assertGreater(self.scanner.result_count, 0)
        self.scanner.reset()
        self.assertEqual(self.scanner.result_count, 0)
        self.assertEqual(self.scanner.scan_count, 0)

    def test_full_flow_first_next_write(self):
        """Simulate full CE workflow: first scan → change → next scan → verify 1 result."""
        self.scanner.first_scan(DataType.INT32, ScanMode.EXACT, 1000)
        self.mem.write_value(self.addr, 7777, DataType.INT32)
        time.sleep(0.05)
        count = self.scanner.next_scan(ScanMode.EXACT, 7777)

        results = self.scanner.get_results()
        self.assertGreater(count, 0)
        addrs = [r.address for r in results]
        self.assertIn(self.addr, addrs)

        # Write via memory_io
        ok = self.mem.write_value(self.addr, 42, DataType.INT32)
        self.assertTrue(ok)
        readback = self.mem.read_int(self.addr, size=4)
        self.assertEqual(readback, 42)


if __name__ == "__main__":
    unittest.main(verbosity=2)
