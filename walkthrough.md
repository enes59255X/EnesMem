# EnesMem Advanced Scanning & Memory Viewer Walkthrough

The following features have been successfully implemented, polished, and verified!

## 1. Memory Viewer (Hex Editor)
A high-performance, live-updating Memory Viewer has been added to the application. This allows for raw inspection and browsing of any memory address in the target process.

**Key Features:**
- **Virtualized Scrolling:** Handles massive memory spaces smoothly by only rendering the visible 16-byte rows.
- **Live Refresh:** Bytes that change in the target process are highlighted in **red** in real-time.
- **ASCII View:** Side-by-side display of hex bytes and their ASCII representation.
- **Address Jump:** Right-click any result in the table and select **"🔍 Browse Memory"** to jump directly to that address in the viewer.
- **Keyboard Navigation:** Support for Arrow keys and Page Up/Down for rapid browsing.

## 2. Unknown Initial Value (UIV) Scan
You can now scan for values without knowing their initial state. This is highly useful for health bars or hidden stats where the game doesn't explicitly display a number.

**How it works:**
1. Select `Unknown Initial Value` from the Scan Type dropdown.
2. Click **First Scan**. The scanner will quickly capture and store chunks of the entire process memory (in memory).
3. Do something in the game to change the value (e.g., take damage to decrease health).
4. Change the Scan Type to `Decreased Value` (or `Increased Value`, `Changed Value`, etc.).
5. Click **Next Scan**. The engine will compare the live memory against the previously saved memory chunks, keeping only the addresses that meet your criteria!

## 3. Text / String Search & AOB
You can now easily search for Strings (UTF-8 or UTF-16) and Byte Patterns (AOB) inside the memory.

**How it works:**
1. Select `String (UTF-8)`, `String (UTF-16LE)`, or `Byte Array (AOB)`.
2. Type the text or hex pattern (e.g., `55 8B EC ? ? 8B`) into the Value box.
3. Click **First Scan**. The scanner will locate all occurrences.
4. **Note:** String searches no longer require a null terminator, allowing you to find raw text embedded in data structures.

## 4. Float Tolerance
Precise float matching can be difficult due to rounding. You can now specify a **Tolerance (±)** in the UI.

**How it works:**
1. Select `Float` or `Double`.
2. Set Scan Type to `Float Tolerance (±)`.
3. Enter your target value and the allowed error margin (e.g., `100.0` with `0.1` tolerance).
4. The scanner will find all values between `99.9` and `100.1`.

### Bug Fixes & Polish
- **UI Tolerance Fix:** Resolved an issue where the tolerance value from the UI wasn't being passed to the background scan worker.
- **STRING16 Stride Fix:** Fixed a bug where UTF-16 strings were skipped during scanning because the byte-stride was incorrect.
- **Advanced Frozen Management:** 
    - Watchlist now has a "Frozen Only" filter.
    - Bulk freeze/unfreeze actions now honor active filters.
    - Manual value edits on a frozen address now correctly update the freezer's target value.

---
> [!TIP]
> All new scanning mechanisms are optimized for performance and memory efficiency. You can now run complex scans without crashing the application.

### Verification
- **Unit Tests:** 22 tests covering Memory Viewer logic, AOB, Tolerance, UIV, and String scans are passing successfully.
- **Commands:** `pytest tests/`
