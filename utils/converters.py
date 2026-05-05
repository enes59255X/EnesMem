"""
converters.py — Type-safe conversion between raw bytes and Python values.
Used by memory_io.py and scanner.py.
"""
import struct
from utils.patterns import DataType, DATA_TYPE_STRUCT, DATA_TYPE_SIZE


# ─── Bytes → Python value ─────────────────────────────────────────────────────

def bytes_to_value(raw: bytes, dtype: DataType) -> int | float | str | bytes | None:
    """Convert a raw bytes buffer to a Python value of the given DataType."""
    if dtype in DATA_TYPE_STRUCT:
        fmt = DATA_TYPE_STRUCT[dtype]
        size = struct.calcsize(fmt)
        if len(raw) < size:
            return None
        return struct.unpack_from(fmt, raw)[0]

    if dtype == DataType.STRING:
        try:
            return raw.split(b"\x00")[0].decode("utf-8", errors="replace")
        except Exception:
            return None

    if dtype == DataType.STRING16:
        try:
            # Find null terminator (two consecutive zero bytes)
            idx = 0
            while idx + 1 < len(raw):
                if raw[idx] == 0 and raw[idx + 1] == 0:
                    break
                idx += 2
            return raw[:idx].decode("utf-16-le", errors="replace")
        except Exception:
            return None

    if dtype == DataType.BYTES:
        return raw

    return None


# ─── Python value → bytes ─────────────────────────────────────────────────────

def value_to_bytes(value: int | float | str | bytes, dtype: DataType) -> bytes | None:
    """Pack a Python value into raw bytes for the given DataType."""
    if dtype in DATA_TYPE_STRUCT:
        fmt = DATA_TYPE_STRUCT[dtype]
        try:
            return struct.pack(fmt, value)
        except (struct.error, TypeError):
            return None

    if dtype == DataType.STRING:
        if isinstance(value, str):
            return value.encode("utf-8")
        return None

    if dtype == DataType.STRING16:
        if isinstance(value, str):
            return value.encode("utf-16-le")
        return None

    if dtype == DataType.BYTES:
        if isinstance(value, (bytes, bytearray)):
            return bytes(value)
        # Accept hex string: "DE AD BE EF"
        if isinstance(value, str):
            try:
                return bytes.fromhex(value.replace(" ", ""))
            except ValueError:
                return None

    return None


# ─── String → Python value (user input parsing) ───────────────────────────────

def parse_user_input(text: str, dtype: DataType) -> int | float | str | bytes | None:
    """
    Parse a user-supplied string into the appropriate Python type.
    Returns None if parsing fails.
    """
    text = text.strip()

    if dtype in (DataType.INT8, DataType.INT16, DataType.INT32, DataType.INT64):
        try:
            # Support hex (0x prefix) and decimal
            return int(text, 0)
        except ValueError:
            return None

    if dtype in (DataType.FLOAT, DataType.DOUBLE):
        try:
            return float(text)
        except ValueError:
            return None

    if dtype in (DataType.STRING, DataType.STRING16):
        return text  # Raw string

    if dtype == DataType.BYTES:
        if "?" in text:
            parts = text.split()
            pattern = bytearray()
            mask = ""
            for p in parts:
                if "?" in p:
                    pattern.append(0)
                    mask += "?"
                else:
                    try:
                        pattern.append(int(p, 16))
                        mask += "x"
                    except ValueError:
                        return None
            return (bytes(pattern), mask)
        else:
            try:
                return bytes.fromhex(text.replace(" ", ""))
            except ValueError:
                return None

    return None


# ─── Display helpers ──────────────────────────────────────────────────────────

def format_value(value: int | float | str | bytes | None, dtype: DataType) -> str:
    """Format a value for display in the results table."""
    if value is None:
        return "???"
    if isinstance(value, float):
        return f"{value:.6g}"
    if isinstance(value, bytes):
        return " ".join(f"{b:02X}" for b in value)
    return str(value)


def format_address(address: int) -> str:
    """Format an address as a hex string with appropriate width."""
    # Mask to 64-bit unsigned to handle negative numbers from signed casts
    address &= 0xFFFFFFFFFFFFFFFF
    if address > 0xFFFFFFFF:
        return f"{address:016X}"
    return f"{address:08X}"
