"""
freezer.py — Background value freezer.
Single daemon thread writes frozen addresses every FREEZE_INTERVAL_SEC.
Thread-safe with RLock.
"""
import threading
import time
from typing import Optional

from core.memory_io import MemoryIO
from utils.converters import value_to_bytes
from utils.logger import log
from utils.patterns import DataType, FREEZE_INTERVAL_SEC


class FrozenEntry:
    __slots__ = ("value", "dtype", "raw_bytes")

    def __init__(self, value, dtype: DataType) -> None:
        self.value = value
        self.dtype = dtype
        self.raw_bytes: Optional[bytes] = value_to_bytes(value, dtype)


class Freezer:
    def __init__(self, memory: MemoryIO, interval: float = FREEZE_INTERVAL_SEC) -> None:
        self._mem      = memory
        self._interval = interval
        self._lock     = threading.RLock()
        self._frozen:  dict[int, FrozenEntry] = {}
        self._stop     = threading.Event()
        self._thread:  Optional[threading.Thread] = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="EnesMem-Freezer", daemon=True
        )
        self._thread.start()
        log.info("Freezer started (interval=%.3fs)", self._interval)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=2.0)
        self.unfreeze_all()
        log.info("Freezer stopped")

    def freeze(self, address: int, value, dtype: DataType) -> None:
        entry = FrozenEntry(value, dtype)
        if entry.raw_bytes is None:
            log.warning("freeze: cannot pack value=%r dtype=%s", value, dtype)
            return
        with self._lock:
            self._frozen[address] = entry
        if not (self._thread and self._thread.is_alive()):
            self.start()
        log.debug("Frozen 0x%X = %r (%s)", address, value, dtype.name)

    def unfreeze(self, address: int) -> None:
        with self._lock:
            self._frozen.pop(address, None)
        log.debug("Unfrozen 0x%X", address)

    def unfreeze_all(self) -> None:
        with self._lock:
            self._frozen.clear()

    def is_frozen(self, address: int) -> bool:
        with self._lock:
            return address in self._frozen

    def frozen_addresses(self) -> list[int]:
        with self._lock:
            return list(self._frozen.keys())

    def get_entry(self, address: int) -> Optional[FrozenEntry]:
        with self._lock:
            return self._frozen.get(address)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                with self._lock:
                    # Filter out entries with None raw_bytes
                    writes = []
                    for addr, entry in self._frozen.items():
                        if entry.raw_bytes:
                            writes.append((addr, entry.raw_bytes))
                
                if writes:
                    # Use batch write to reduce overhead and log noise
                    # write_batch already logs the failure count and first few addrs
                    self._mem.write_batch(writes)
            except Exception as e:
                log.error("Freezer: loop error: %s", e, exc_info=True)
            
            self._stop.wait(timeout=self._interval)
