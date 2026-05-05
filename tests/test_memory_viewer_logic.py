import pytest
from unittest.mock import MagicMock
from PyQt6.QtWidgets import QApplication
from gui.memory_viewer import MemoryViewer, BYTES_PER_ROW, ROWS_VISIBLE

@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app

def test_memory_viewer_address_alignment(qapp):
    """Verify that setting an address aligns it to 16 bytes."""
    viewer = MemoryViewer()
    viewer.set_address(0x12345678)
    assert viewer._current_address == 0x12345670
    
    viewer.set_address(0x1234567F)
    assert viewer._current_address == 0x12345670

def test_memory_viewer_scrolling(qapp):
    """Verify that scrolling updates the current address correctly."""
    viewer = MemoryViewer()
    viewer._active = True
    viewer._current_address = 0x1000
    
    # Scroll down 1 row
    viewer._on_scroll(50001)
    assert viewer._current_address == 0x1000 + BYTES_PER_ROW
    
    # Scroll up 2 rows
    viewer._on_scroll(49999)
    # Note: _on_scroll uses relative delta from 50000
    # Current addr was 0x1010. Delta from 50000 to 49999 is -1 row.
    # 0x1010 - 16 = 0x1000
    assert viewer._current_address == 0x1000

def test_memory_viewer_refresh_logic(qapp):
    """Verify that refresh reads the correct number of bytes."""
    mock_io = MagicMock()
    mock_io.read_bytes.return_value = b"\xAA" * (ROWS_VISIBLE * BYTES_PER_ROW)
    
    viewer = MemoryViewer(memory_io=mock_io)
    viewer.set_address(0x2000)
    
    # set_address calls refresh(force=True)
    assert viewer._current_address == 0x2000
    mock_io.read_bytes.assert_called_with(0x2000, ROWS_VISIBLE * BYTES_PER_ROW)
    assert viewer._bytes_data == b"\xAA" * (ROWS_VISIBLE * BYTES_PER_ROW)
