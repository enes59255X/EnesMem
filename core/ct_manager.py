"""
ct_manager.py — Cheat Engine CT file import/export support.
Handles Cheat Engine 6.x/7.x .CT file format (XML-based).
"""
import xml.etree.ElementTree as ET
import base64
import zlib
from typing import List, Optional, Dict, Any
from dataclasses import dataclass
import os
import json

from utils.patterns import DataType
from utils.logger import log


@dataclass
class CTEntry:
    """Represents a single Cheat Engine entry."""
    description: str
    address: str  # May be symbolic like "game.exe+1A2B3C"
    address_real: int = 0
    vartype: str = "4 Bytes"
    dtype: DataType = DataType.INT32
    is_pointer: bool = False
    offsets: List[int] = None
    frozen: bool = False
    frozen_value: str = "0"
    
    def __post_init__(self):
        if self.offsets is None:
            self.offsets = []
        # Map CT vartype to our DataType
        self.dtype = self._map_vartype(self.vartype)
    
    @staticmethod
    def _map_vartype(vartype: str) -> DataType:
        """Map Cheat Engine variable type to our DataType."""
        mapping = {
            "Binary": DataType.BYTES,
            "Byte": DataType.INT8,
            "2 Bytes": DataType.INT16,
            "4 Bytes": DataType.INT32,
            "8 Bytes": DataType.INT64,
            "Float": DataType.FLOAT,
            "Double": DataType.DOUBLE,
            "String": DataType.STRING,
            "Array of byte": DataType.BYTES,
        }
        return mapping.get(vartype, DataType.INT32)


class CTManager:
    """
    Manages Cheat Engine CT file import and export.
    CT files are compressed XML files.
    """
    
    # CT variable type mapping (reverse)
    DTYPE_TO_CT = {
        DataType.INT8: "Byte",
        DataType.INT16: "2 Bytes",
        DataType.INT32: "4 Bytes",
        DataType.INT64: "8 Bytes",
        DataType.FLOAT: "Float",
        DataType.DOUBLE: "Double",
        DataType.STRING: "String",
        DataType.BYTES: "Array of byte",
    }
    
    @staticmethod
    def decompress_ct(data: bytes) -> str:
        """
        Decompress CT file data.
        CT files use zlib compression.
        """
        try:
            # Try zlib decompression
            decompressed = zlib.decompress(data)
            return decompressed.decode('utf-8')
        except:
            # May already be uncompressed (rare)
            return data.decode('utf-8', errors='ignore')
    
    @staticmethod
    def compress_ct(xml_string: str) -> bytes:
        """Compress XML string for CT file."""
        return zlib.compress(xml_string.encode('utf-8'))
    
    @classmethod
    def parse_ct(cls, filepath: str) -> Optional[List[CTEntry]]:
        """
        Parse a CT file and extract entries.
        
        Args:
            filepath: Path to .CT file
        
        Returns:
            List of CTEntry objects or None on error
        """
        try:
            with open(filepath, 'rb') as f:
                data = f.read()
            
            # Decompress
            xml_content = cls.decompress_ct(data)
            
            # Parse XML
            root = ET.fromstring(xml_content)
            
            entries = []
            
            # Find CheatTable element
            cheat_table = root.find('.//CheatTable')
            if cheat_table is None:
                cheat_table = root  # May be root itself
            
            # Parse CheatEntries
            for entry_elem in cheat_table.findall('.//CheatEntry'):
                entry = cls._parse_entry(entry_elem)
                if entry:
                    entries.append(entry)
            
            log.info("CTManager: Parsed %d entries from %s", len(entries), filepath)
            return entries
            
        except Exception as e:
            log.error("CTManager: Parse failed: %s", e)
            return None
    
    @classmethod
    def _parse_entry(cls, elem: ET.Element) -> Optional[CTEntry]:
        """Parse a single CheatEntry element."""
        try:
            description = elem.findtext('Description', '')
            
            # Get address
            address_elem = elem.find('Address')
            address = "0"
            address_real = 0
            if address_elem is not None:
                address = address_elem.text or "0"
                # Try to parse as hex
                try:
                    if address.startswith('0x'):
                        address_real = int(address, 16)
                    else:
                        address_real = int(address)
                except:
                    pass  # Symbolic address
            
            # Get variable type
            vartype = elem.findtext('VariableType', '4 Bytes')
            
            # Check for pointer
            is_pointer = False
            offsets = []
            
            pointer_elem = elem.find('Pointer')
            if pointer_elem is not None:
                is_pointer = True
                # Get pointer offsets
                for offset_elem in pointer_elem.findall('Offset'):
                    offset_text = offset_elem.text or "0"
                    try:
                        if offset_text.startswith('0x'):
                            offsets.append(int(offset_text, 16))
                        else:
                            offsets.append(int(offset_text))
                    except:
                        offsets.append(0)
                offsets.reverse()  # CT stores offsets in reverse order
            
            # Get frozen state
            frozen = elem.findtext('Frozen', '0') == '1'
            frozen_value = elem.findtext('FrozenValue', '0')
            
            return CTEntry(
                description=description,
                address=address,
                address_real=address_real,
                vartype=vartype,
                is_pointer=is_pointer,
                offsets=offsets,
                frozen=frozen,
                frozen_value=frozen_value
            )
            
        except Exception as e:
            log.warning("CTManager: Failed to parse entry: %s", e)
            return None
    
    @classmethod
    def export_ct(cls, entries: List[CTEntry], filepath: str, game_name: str = "") -> bool:
        """
        Export entries to CT file.
        
        Args:
            entries: List of CTEntry objects
            filepath: Output file path
            game_name: Optional game/process name
        
        Returns:
            True on success
        """
        try:
            # Build XML
            xml_parts = [
                '<?xml version="1.0" encoding="utf-8"?>',
                '<CheatTable>',
                f'  <CheatEntries>',
            ]
            
            for i, entry in enumerate(entries):
                xml_parts.append(cls._entry_to_xml(entry, i))
            
            xml_parts.extend([
                '  </CheatEntries>',
                f'  <UserdefinedSymbols/>',
                '</CheatTable>'
            ])
            
            xml_string = '\n'.join(xml_parts)
            
            # Compress and write
            compressed = cls.compress_ct(xml_string)
            
            with open(filepath, 'wb') as f:
                f.write(compressed)
            
            log.info("CTManager: Exported %d entries to %s", len(entries), filepath)
            return True
            
        except Exception as e:
            log.error("CTManager: Export failed: %s", e)
            return False
    
    @classmethod
    def _entry_to_xml(cls, entry: CTEntry, index: int) -> str:
        """Convert CTEntry to XML string."""
        vartype = cls.DTYPE_TO_CT.get(entry.dtype, "4 Bytes")
        
        lines = [
            f'    <CheatEntry>',
            f'      <ID>{index}</ID>',
            f'      <Description>"{cls._escape_xml(entry.description)}"</Description>',
            f'      <ShowAsSigned>0</ShowAsSigned>',
            f'      <VariableType>{vartype}</VariableType>',
        ]
        
        if entry.is_pointer and entry.offsets:
            # Pointer entry
            lines.append(f'      <Address>{entry.address}</Address>')
            lines.append(f'      <Pointer>')
            for offset in entry.offsets:
                lines.append(f'        <Offset>{offset:X}</Offset>')
            lines.append(f'      </Pointer>')
        else:
            # Direct address
            if entry.address_real:
                lines.append(f'      <Address>0x{entry.address_real:X}</Address>')
            else:
                lines.append(f'      <Address>{entry.address}</Address>')
        
        if entry.frozen:
            lines.append(f'      <Frozen>1</Frozen>')
            lines.append(f'      <FrozenValue>{entry.frozen_value}</FrozenValue>')
        
        lines.append(f'    </CheatEntry>')
        
        return '\n'.join(lines)
    
    @staticmethod
    def _escape_xml(text: str) -> str:
        """Escape special XML characters."""
        return (text
                .replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;'))
    
    @staticmethod
    def convert_to_watchlist_entries(ct_entries: List[CTEntry]) -> List[Dict]:
        """
        Convert CT entries to our watchlist format.
        
        Returns:
            List of dicts with watchlist entry data
        """
        watchlist_entries = []
        
        for ct_entry in ct_entries:
            entry_data = {
                "description": ct_entry.description,
                "address": ct_entry.address_real,
                "dtype": ct_entry.dtype,
                "frozen": ct_entry.frozen,
            }
            
            if ct_entry.is_pointer:
                entry_data["module_name"] = ct_entry.address  # Base module/address
                entry_data["offsets"] = ct_entry.offsets
            
            watchlist_entries.append(entry_data)
        
        return watchlist_entries
    
    @staticmethod
    def convert_from_watchlist_entries(watchlist: List[Any]) -> List[CTEntry]:
        """
        Convert our watchlist entries to CT format.
        
        Args:
            watchlist: List of WatchEntry objects
        
        Returns:
            List of CTEntry objects
        """
        ct_entries = []
        
        for entry in watchlist:
            ct_entry = CTEntry(
                description=getattr(entry, 'description', ''),
                address=f"0x{getattr(entry, 'address', 0):X}",
                address_real=getattr(entry, 'address', 0),
                vartype=CTManager.DTYPE_TO_CT.get(getattr(entry, 'dtype', DataType.INT32), "4 Bytes"),
                dtype=getattr(entry, 'dtype', DataType.INT32),
                is_pointer=bool(getattr(entry, 'module_name', None)),
                offsets=getattr(entry, 'offsets', []) or [],
                frozen=getattr(entry, 'frozen', False)
            )
            ct_entries.append(ct_entry)
        
        return ct_entries


def import_ct_file(filepath: str) -> Optional[List[Dict]]:
    """
    Convenience function to import CT file to watchlist format.
    
    Returns:
        List of entry dicts or None on error
    """
    ct_entries = CTManager.parse_ct(filepath)
    if ct_entries:
        return CTManager.convert_to_watchlist_entries(ct_entries)
    return None


def export_ct_file(watchlist: List[Any], filepath: str, game_name: str = "") -> bool:
    """
    Convenience function to export watchlist to CT file.
    
    Args:
        watchlist: List of watchlist entries
        filepath: Output file path
        game_name: Optional game name
    
    Returns:
        True on success
    """
    ct_entries = CTManager.convert_from_watchlist_entries(watchlist)
    return CTManager.export_ct(ct_entries, filepath, game_name)
