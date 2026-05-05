"""
freeze_manager.py — Enhanced freeze manager with per-entry intervals, bulk ops,
and hold-key mode. Drop-in replacement for core/freezer.py.
"""
import threading
import time
from dataclasses import dataclass, field
from typing import Optional, Callable

from core.memory_io import MemoryIO
from utils.converters import value_to_bytes
from utils.logger import log
from utils.patterns import DataType


@dataclass
class FreezeEntry:
    address:     int
    value:       object
    dtype:       DataType
    interval_ms: int   = 50
    active:      bool  = True
    description: str   = ""
    _last_write: float = field(default=0.0, repr=False)


class FreezeManager:
    """
    Enhanced memory freezer.
    - Per-entry write intervals
    - Bulk freeze / unfreeze / remove
    - Active toggle per entry
    - Event callback on each write
    """

    def __init__(self, memory: MemoryIO, default_interval_ms: int = 50) -> None:
        self._mem        = memory
        self._default_ms = default_interval_ms
        self._entries:   dict[int, FreezeEntry] = {}
        self._lock       = threading.RLock()
        self._running    = False
        self._thread:    Optional[threading.Thread] = None
        self._on_tick:   Optional[Callable] = None

    # ── Configuration ─────────────────────────────────────────────────────────

    def set_tick_callback(self, cb: Callable) -> None:
        """Called after each write: cb(address, value, success)."""
        self._on_tick = cb

    # ── Per-entry API ─────────────────────────────────────────────────────────

    def freeze(
        self,
        address:     int,
        value:       object,
        dtype:       DataType,
        interval_ms: int = 0,
        description: str = "",
    ) -> None:
        interval = interval_ms or self._default_ms
        with self._lock:
            self._entries[address] = FreezeEntry(
                address=address,
                value=value,
                dtype=dtype,
                interval_ms=interval,
                active=True,
                description=description,
            )
        if not self._running:
            self.start()
        log.debug("Frozen 0x%X = %r (%s) @ %dms", address, value, dtype.name, interval)

    def unfreeze(self, address: int) -> None:
        with self._lock:
            self._entries.pop(address, None)
        log.debug("Unfrozen 0x%X", address)

    def set_active(self, address: int, active: bool) -> None:
        with self._lock:
            if address in self._entries:
                self._entries[address].active = active

    def set_interval(self, address: int, interval_ms: int) -> None:
        with self._lock:
            if address in self._entries:
                self._entries[address].interval_ms = max(10, interval_ms)

    def update_value(self, address: int, value: object) -> None:
        with self._lock:
            if address in self._entries:
                self._entries[address].value = value

    def is_frozen(self, address: int) -> bool:
        with self._lock:
            e = self._entries.get(address)
            return e is not None and e.active

    # ── Bulk API ──────────────────────────────────────────────────────────────

    def freeze_all(self) -> None:
        with self._lock:
            for e in self._entries.values():
                e.active = True

    def unfreeze_all(self) -> None:
        with self._lock:
            for e in self._entries.values():
                e.active = False

    def remove_all(self) -> None:
        with self._lock:
            self._entries.clear()
        self.stop()

    def get_entries(self) -> list[FreezeEntry]:
        with self._lock:
            return list(self._entries.values())

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread  = threading.Thread(
            target=self._loop, daemon=True, name="FreezeManager"
        )
        self._thread.start()
        log.info("FreezeManager started (interval=%dms)", self._default_ms)

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None
        log.info("FreezeManager stopped")

    # ── Internal ──────────────────────────────────────────────────────────────

    def _loop(self) -> None:
        while self._running:
            now = time.monotonic()
            min_sleep = self._default_ms / 1000.0

            with self._lock:
                snapshot = list(self._entries.values())

            for entry in snapshot:
                if not entry.active:
                    continue
                deadline = entry._last_write + entry.interval_ms / 1000.0
                if now >= deadline:
                    raw = value_to_bytes(entry.value, entry.dtype)
                    ok  = False
                    if raw is not None:
                        ok = self._mem.write_bytes(entry.address, raw)
                    entry._last_write = now
                    if self._on_tick:
                        try:
                            self._on_tick(entry.address, entry.value, ok)
                        except Exception:
                            pass
                else:
                    min_sleep = min(min_sleep, deadline - now)

            time.sleep(max(min_sleep, 0.005))
