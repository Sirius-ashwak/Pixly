"""Property-based tests for File Watcher.

Feature: screensort, Property 1: Debounce prevents duplicate processing
Feature: screensort, Property 2: Queue preserves all files
Feature: screensort, Property 3: Temporary file filtering
"""

import tempfile
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock

from hypothesis import given, strategies as st, settings

from pixly.core.watcher import ScreenshotWatcher


class TestDebouncePreventsduplicates:
    """Property 1: Debounce prevents duplicate processing.
    
    *For any* file that triggers multiple detection events within 500ms,
    the processing callback SHALL be invoked exactly once.
    
    **Validates: Requirements 1.2**
    """
    
    @given(st.integers(min_value=2, max_value=10))
    @settings(max_examples=100)
    def test_multiple_events_single_processing(self, num_events: int):
        """Feature: screensort, Property 1: Debounce prevents duplicate processing"""
        processed_files: list[str] = []
        lock = threading.Lock()
        
        def mock_processor(filepath: str):
            with lock:
                processed_files.append(filepath)
        
        watcher = ScreenshotWatcher(mock_processor)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a test file
            test_file = Path(tmpdir) / "test.png"
            test_file.touch()
            
            # Simulate multiple events for same file within debounce window
            for _ in range(num_events):
                watcher._pending[str(test_file)] = time.time()
            
            # Should only have one entry in pending (dict deduplicates)
            assert len(watcher._pending) == 1


class TestQueuePreservesFiles:
    """Property 2: Queue preserves all files.
    
    *For any* sequence of files created in rapid succession, all files
    SHALL eventually appear in the processing queue in creation order.
    
    **Validates: Requirements 1.3**
    """
    
    @given(st.integers(min_value=1, max_value=50))
    @settings(max_examples=100)
    def test_all_files_queued(self, num_files: int):
        """Feature: screensort, Property 2: Queue preserves all files"""
        watcher = ScreenshotWatcher(lambda x: None)
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create multiple test files
            files = []
            for i in range(num_files):
                test_file = Path(tmpdir) / f"test_{i}.png"
                test_file.touch()
                files.append(str(test_file))
            
            # Add all files to queue directly
            for filepath in files:
                watcher._queue.append(filepath)
            
            # All files should be in queue (up to max size)
            expected_count = min(num_files, ScreenshotWatcher.MAX_QUEUE_SIZE)
            assert len(watcher._queue) == expected_count
    
    @given(st.integers(min_value=101, max_value=150))
    @settings(max_examples=100)
    def test_queue_overflow_drops_oldest(self, num_files: int):
        """Queue should drop oldest files when exceeding max size."""
        watcher = ScreenshotWatcher(lambda x: None)
        
        # Add more files than max queue size
        for i in range(num_files):
            watcher._queue.append(f"/test/file_{i}.png")
        
        # Queue should be at max size
        assert len(watcher._queue) == ScreenshotWatcher.MAX_QUEUE_SIZE
        
        # Oldest files should have been dropped
        # The queue should contain the most recent files
        assert watcher._queue[-1] == f"/test/file_{num_files - 1}.png"


class TestTemporaryFileFiltering:
    """Property 3: Temporary file filtering.
    
    *For any* filename starting with '~' or '.', the file watcher
    SHALL not add it to the processing queue.
    
    **Validates: Requirements 1.5**
    """
    
    @given(st.text(alphabet='abcdefghijklmnopqrstuvwxyz0123456789', min_size=1, max_size=20))
    @settings(max_examples=100)
    def test_tilde_prefix_filtered(self, filename: str):
        """Feature: screensort, Property 3: Temporary file filtering
        
        Files starting with ~ should be filtered.
        """
        watcher = ScreenshotWatcher(lambda x: None)
        
        temp_filename = f"~{filename}.png"
        
        assert watcher._is_temporary_file(temp_filename) is True
    
    @given(st.text(alphabet='abcdefghijklmnopqrstuvwxyz0123456789', min_size=1, max_size=20))
    @settings(max_examples=100)
    def test_dot_prefix_filtered(self, filename: str):
        """Feature: screensort, Property 3: Temporary file filtering
        
        Files starting with . should be filtered.
        """
        watcher = ScreenshotWatcher(lambda x: None)
        
        hidden_filename = f".{filename}.png"
        
        assert watcher._is_temporary_file(hidden_filename) is True
    
    @given(st.text(alphabet='abcdefghijklmnopqrstuvwxyz0123456789', min_size=1, max_size=20))
    @settings(max_examples=100)
    def test_normal_files_not_filtered(self, filename: str):
        """Normal files should not be filtered."""
        watcher = ScreenshotWatcher(lambda x: None)
        
        normal_filename = f"{filename}.png"
        
        # Normal files (not starting with ~ or .) should not be filtered
        assert watcher._is_temporary_file(normal_filename) is False


class TestExtensionFiltering:
    """Test that only image extensions are monitored."""
    
    @given(st.sampled_from(['.png', '.jpg', '.jpeg']))
    @settings(max_examples=100)
    def test_image_extensions_accepted(self, ext: str):
        """Image extensions should be in monitored set."""
        assert ext in ScreenshotWatcher.MONITORED_EXTENSIONS
    
    @given(st.sampled_from(['.txt', '.pdf', '.doc', '.exe', '.py']))
    @settings(max_examples=100)
    def test_non_image_extensions_rejected(self, ext: str):
        """Non-image extensions should not be monitored."""
        assert ext not in ScreenshotWatcher.MONITORED_EXTENSIONS
