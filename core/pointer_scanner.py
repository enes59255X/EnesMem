"""
pointer_scanner.py — Static pointer resolution and multi-level chain scanning.
Resolves [module_base + offset1] + offset2 + ... chains.
"""
import struct
import json
from dataclasses import dataclass, asdict
from typing import Optional, Callable

from core.memory_io import MemoryIO
from core.process_manager import ProcessManager
from utils.logger import log
from utils.patterns import DataType


@dataclass
class PointerChain:
    module_name: str
    base_addr:   int
    offsets:     list[int]
    final_addr:  int
    value:       Optional[str] = None


class PointerScanner:
    def __init__(self, memory: MemoryIO, process: ProcessManager) -> None:
        self._mem     = memory
        self._process = process
        self._ptr_fmt = "<Q" if memory._is_64bit else "<I"
        self._ptr_size = 8 if memory._is_64bit else 4
        self._cancelled = False

    def cancel(self) -> None:
        self._cancelled = True
    def resolve_pointer(self, base_addr: int, offsets: list[int]) -> Optional[int]:
        """
        Walk a pointer chain starting from base_addr.
        Returns the final resolved address or None on failure.
        """
        # Validate memory handle
        if not self._mem or not getattr(self._mem, '_handle', None):
            return None
        
        ptr_mask = (1 << (8 * self._ptr_size)) - 1
        addr = base_addr & ptr_mask
        
        # Validate starting address
        if addr < 0x1000 or addr > 0x00007FFF00000000:
            return None
        
        for i, offset in enumerate(offsets):
            try:
                raw = self._mem.read_bytes(addr, self._ptr_size)
                if raw is None or len(raw) < self._ptr_size:
                    return None
                
                pointed = struct.unpack_from(self._ptr_fmt, raw)[0]
                
                # Validate dereferenced pointer
                if pointed == 0 or pointed < 0x1000:
                    return None
                
                # Check for pointer pointing to itself (circular reference)
                if pointed == addr:
                    return None
                    
                addr = (pointed + offset) & ptr_mask
                
                # Validate computed address
                if addr < 0x1000 or addr > 0x00007FFF00000000:
                    return None
                    
            except struct.error:
                return None
            except Exception as e:
                log.debug("resolve_pointer exception at step %d, addr=0x%X: %s", i, addr, e)
                return None

        return addr

    def resolve_from_module(
        self, module_name: str, offsets: list[int]
    ) -> Optional[int]:
        """
        Resolve a pointer chain using a module base as starting point.
        """
        # Validate parameters
        if not module_name or not offsets:
            return None
        
        if not self._process or not self._mem:
            return None
        
        try:
            mod = self._process.find_module(module_name)
            if mod is None:
                return None
            
            if not mod.base_addr or mod.base_addr < 0x1000:
                return None

            static_addr = mod.base_addr + offsets[0]
            
            # Validate static address
            if static_addr < 0x1000:
                return None
            
            if len(offsets) == 1:
                return static_addr

            return self.resolve_pointer(static_addr, offsets[1:])
        except Exception as e:
            log.debug("resolve_from_module exception: %s", e)
            return None

    def find_pointer_chains(self, *args, **kwargs):
        """Alias for auto_scan used by the UI."""
        return self.auto_scan(*args, **kwargs)

    def auto_scan(
        self,
        target_addr: int,
        max_depth:   int = 3,
        max_offset:  int = 2048,
        progress_cb: Optional[Callable[[int], None]] = None,
    ) -> list[PointerChain]:
        """
        Highly optimized multi-threaded BFS pointer scan.
        """
        import bisect
        from array import array
        from concurrent.futures import ThreadPoolExecutor

        log.info("Auto pointer scan: target=0x%X depth=%d offset=%d", target_addr, max_depth, max_offset)
        self._cancelled = False
        
        regions = self._mem.get_regions(exclude_mapped=False)
        if not regions:
            return []

        # Build a list of valid address ranges for fast pointer validation
        valid_ranges = sorted([(r.base, r.base + r.size) for r in regions])
        region_starts = [r[0] for r in valid_ranges]
        region_ends = [r[1] for r in valid_ranges]

        min_valid = region_starts[0]
        max_valid = region_ends[-1]

        log.info("Building pointer index using parallel workers...")
        
        # We'll use a thread pool to scan regions in parallel.
        # This is safe because we are only reading and ReadProcessMemory is thread-safe.
        results_pointed_to = []
        results_source_addr = []
        
        total_size = sum(r.size for r in regions)
        processed_size = [0] # List for closure mutation
        
        def scan_region(region):
            if self._cancelled: return None
            
            # Validate region
            if not region or not hasattr(region, 'base') or not hasattr(region, 'size'):
                return None
            
            # Validate memory handle
            if not self._mem or not getattr(self._mem, '_handle', None):
                return None
            
            # Heuristic: skip massive mapped files unless small
            if region.type_ == 0x40000 and region.size > 200 * 1024 * 1024:
                processed_size[0] += region.size
                return None
            
            # Skip invalid regions
            if region.base < 0x1000 or region.size == 0 or region.size > 0x100000000:
                return None

            try:
                ptrs = array('Q')
                srcs = array('Q')
                
                fmt = 'Q' if self._ptr_size == 8 else 'I'
                chunk_size = 1024 * 1024 # 1MB chunks
                
                for offset in range(0, region.size, chunk_size):
                    if self._cancelled: break
                    size = min(chunk_size, region.size - offset)
                    arr = self._mem.read_into_array(region.base + offset, size, fmt=fmt)
                    if not arr: 
                        processed_size[0] += size
                        continue
                    
                    # Local caching for extreme loop performance in pure Python
                    ptrs_append = ptrs.append
                    srcs_append = srcs.append
                    base_addr = region.base + offset
                    ptr_sz = self._ptr_size
                    last_start = -1
                    last_end = -1
                    
                    # Validation loop
                    for i, val in enumerate(arr):
                        if min_valid <= val <= max_valid:
                            # 1. Check last matched region (fast cache)
                            if last_start <= val < last_end:
                                ptrs_append(val)
                                srcs_append(base_addr + (i * ptr_sz))
                            else:
                                # 2. Binary search
                                idx = bisect.bisect_right(region_starts, val) - 1
                                if idx >= 0 and val < region_ends[idx]:
                                    ptrs_append(val)
                                    srcs_append(base_addr + (i * ptr_sz))
                                    last_start = region_starts[idx]
                                    last_end = region_ends[idx]
                    
                    processed_size[0] += size
                    # Progress reporting (approximate since multi-threaded)
                    if progress_cb and offset % (chunk_size * 4) == 0:
                        progress_cb(int((processed_size[0] / total_size) * 60))
                
                return ptrs, srcs
            except Exception as e:
                log.error("Exception in scan_region: %s", e)
                return None

        with ThreadPoolExecutor(max_workers=8) as executor:
            task_results = list(executor.map(scan_region, regions))

        if self._cancelled: return []

        # Merge results from threads
        log.info("Merging and sorting pointer index...")
        final_ptrs = array('Q')
        final_srcs = array('Q')
        for res in task_results:
            if res:
                final_ptrs.extend(res[0])
                final_srcs.extend(res[1])

        if not final_ptrs:
            log.warning("No pointers found in memory!")
            return []

        log.info("Index merged: %d pointers. Sorting for BFS...", len(final_ptrs))
        # This is the memory-intensive part. We use zip and sort.
        # Removing the lambda key makes it 10x faster since Python can sort tuples in C natively.
        indexed_data = sorted(zip(final_ptrs, final_srcs))
        idx_pointed_to = [x[0] for x in indexed_data] # Still needed for bisect

        # 3. BFS Scan using the index
        log.info("Starting BFS search (depth limit=%d)...", max_depth)
        queue: list[tuple[int, list[int]]] = [(target_addr, [])]
        results: list[PointerChain] = []
        modules = self._process.get_modules()
        seen_targets = {target_addr}

        for current_depth in range(1, max_depth + 1):
            if self._cancelled or not queue: break
            log.info("Depth %d: processing %d candidates", current_depth, len(queue))
            
            next_queue = []
            seen_in_depth = set()

            for target, path in queue:
                if self._cancelled: break
                
                # Binary search for range [target - max_offset, target]
                start_idx = bisect.bisect_left(idx_pointed_to, target - max_offset)
                end_idx = bisect.bisect_right(idx_pointed_to, target)
                
                for i in range(start_idx, end_idx):
                    pointed_to, source_addr = indexed_data[i]
                    offset = target - pointed_to
                    
                    if source_addr in seen_in_depth: continue
                    seen_in_depth.add(source_addr)

                    new_path = [offset] + path
                    
                    owner = self._find_owning_module(source_addr, modules)
                    if owner:
                        results.append(PointerChain(
                            module_name=owner.name,
                            base_addr=source_addr,
                            offsets=[source_addr - owner.base_addr] + new_path,
                            final_addr=target_addr
                        ))
                    elif current_depth < max_depth:
                        if source_addr not in seen_targets:
                            next_queue.append((source_addr, new_path))
                            seen_targets.add(source_addr)
            
            queue = next_queue
            # Cap queue to prevent memory explosion in very complex processes
            if len(queue) > 100000:
                log.warning("Queue too large (%d), capping to 100k", len(queue))
                queue = queue[:100000]
            
            if progress_cb:
                progress_cb(60 + int((current_depth / max_depth) * 40))

        log.info("Scan complete: %d chains found", len(results))
        if progress_cb: progress_cb(100)
        return results

    def export_chains(self, chains: list[PointerChain], filepath: str) -> None:
        data = [asdict(c) for c in chains]
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def import_chains(self, filepath: str) -> list[PointerChain]:
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [PointerChain(**d) for d in data]
        except Exception as e:
            log.error("Failed to import chains from %s: %s", filepath, e)
            return []

    def rebase(self, chain: PointerChain, new_module_base: int) -> PointerChain:
        chain.base_addr = new_module_base + chain.offsets[0]
        chain.final_addr = self.resolve_pointer(chain.base_addr, chain.offsets[1:]) or 0
        return chain

    @staticmethod
    def _find_owning_module(addr: int, modules):
        for mod in modules:
            if mod.base_addr <= addr < mod.base_addr + mod.size:
                return mod
        return None

    def filter_chains(
        self,
        chains: list[PointerChain],
        expected_value: any,
        dtype: DataType,
        progress_cb: Optional[Callable[[int], None]] = None
    ) -> list[PointerChain]:
        """
        Filter a list of pointer chains by checking if they still point to a specific value.
        Useful after a game restart.
        """
        valid = []
        total = len(chains)
        log.info("Filtering %d chains for value %s (%s)", total, expected_value, dtype.name)
        
        for i, chain in enumerate(chains):
            if self._cancelled: break
            
            # Resolve the chain in the current process state
            addr = self.resolve_from_module(chain.module_name, chain.offsets)
            if addr:
                val = self._mem.read_value(addr, dtype)
                # If expected_value is None, we just refresh the chain without filtering
                if expected_value is None or val == expected_value:
                    chain.final_addr = addr # Update with new resolved address
                    valid.append(chain)
            
            if progress_cb and i % 100 == 0:
                progress_cb(int((i / total) * 100))
        
        if progress_cb: progress_cb(100)
        log.info("Filter done: %d chains remaining", len(valid))
        return valid
