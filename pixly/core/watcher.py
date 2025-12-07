"""File Watcher component for monitoring directories."""

import logging
import os
import threading
import time
from collections import deque
from pathlib import Path
from typing import Callable

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

logger = logging.getLogger(__name__)


class ScreenshotWatcher(FileSystemEventHandler):
    """Monitor filesystem directories for new screenshot files."""
    
    MONITORED_EXTENSIONS: set[str] = {'.png', '.jpg', '.jpeg'}
    DEBOUNCE_WINDOW: float = 0.5  # seconds
    MAX_QUEUE_SIZE: int = 100
    
    def __init__(self, processor_callback: Callable[[str], None]) -> None:
        """Initialize screenshot watcher.
        
        Args:
            processor_callback: Function to call with filepath when file is ready.
        """
        super().__init__()
        self._processor_callback = processor_callback
        self._pending: dict[str, float] = {}  # filepath -> first_seen_time
        self._queue: deque[str] = deque(maxlen=self.MAX_QUEUE_SIZE)
        self._lock = threading.Lock()
        self._running = False
        self._debounce_thread: threading.Thread | None = None
    
    def start(self) -> None:
        """Start the debounce worker thread."""
        self._running = True
        self._debounce_thread = threading.Thread(target=self._debounce_worker, daemon=True)
        self._debounce_thread.start()
    
    def stop(self) -> None:
        """Stop the debounce worker thread."""
        self._running = False
        if self._debounce_thread:
            self._debounce_thread.join(timeout=2.0)
    
    def on_created(self, event: FileSystemEvent) -> None:
        """Handle file creation event.
        
        Args:
            event: File system event from watchdog.
        """
        if event.is_directory:
            return
        
        filepath = event.src_path
        
        # Check extension
        ext = Path(filepath).suffix.lower()
        if ext not in self.MONITORED_EXTENSIONS:
            return
        
        # Filter temporary files
        filename = Path(filepath).name
        if self._is_temporary_file(filename):
            return
        
        # Add to pending with timestamp
        with self._lock:
            if filepath not in self._pending:
                self._pending[filepath] = time.time()
                logger.debug(f"Detected new file: {filepath}")
    
    def _is_temporary_file(self, filename: str) -> bool:
        """Check if filename indicates a temporary file.
        
        Args:
            filename: Name of the file.
            
        Returns:
            True if file should be ignored.
        """
        return filename.startswith('~') or filename.startswith('.')
    
    def _is_file_ready(self, filepath: str) -> bool:
        """Check if file is fully written and ready for processing.
        
        Args:
            filepath: Path to the file.
            
        Returns:
            True if file is ready.
        """
        try:
            # Check if file exists
            if not os.path.exists(filepath):
                return False
            
            # Try to open file exclusively to check if it's still being written
            # On Windows, this will fail if another process has the file open
            try:
                with open(filepath, 'rb') as f:
                    # Try to read a small amount to verify access
                    f.read(1)
                return True
            except (IOError, PermissionError):
                return False
                
        except Exception:
            return False
    
    def _debounce_worker(self) -> None:
        """Worker thread that processes pending files after debounce window."""
        while self._running:
            current_time = time.time()
            ready_files: list[str] = []
            
            with self._lock:
                # Find files that have passed debounce window
                for filepath, first_seen in list(self._pending.items()):
                    if current_time - first_seen >= self.DEBOUNCE_WINDOW:
                        if self._is_file_ready(filepath):
                            ready_files.append(filepath)
                            del self._pending[filepath]
                
                # Add ready files to queue
                for filepath in ready_files:
                    if len(self._queue) >= self.MAX_QUEUE_SIZE:
                        # Drop oldest if queue is full
                        dropped = self._queue.popleft()
                        logger.warning(f"Queue full, dropping: {dropped}")
                    self._queue.append(filepath)
            
            # Process one file from queue
            filepath_to_process = None
            with self._lock:
                if self._queue:
                    filepath_to_process = self._queue.popleft()
            
            if filepath_to_process:
                try:
                    logger.info(f"Processing: {filepath_to_process}")
                    self._processor_callback(filepath_to_process)
                except Exception as e:
                    logger.error(f"Error processing {filepath_to_process}: {e}")
            
            # Small sleep to prevent busy waiting
            time.sleep(0.1)
    
    def get_queue_size(self) -> int:
        """Get current queue size.
        
        Returns:
            Number of files in queue.
        """
        with self._lock:
            return len(self._queue)
    
    def get_pending_count(self) -> int:
        """Get count of pending files (in debounce window).
        
        Returns:
            Number of pending files.
        """
        with self._lock:
            return len(self._pending)


def start_monitoring(
    directories: list[Path], 
    processor: Callable[[str], None]
) -> tuple[Observer, ScreenshotWatcher]:
    """Start monitoring directories for new screenshots.
    
    Args:
        directories: List of directories to monitor.
        processor: Callback function for processing files.
        
    Returns:
        Tuple of (Observer, ScreenshotWatcher) for control.
    """
    watcher = ScreenshotWatcher(processor)
    watcher.start()
    
    observer = Observer()
    
    for directory in directories:
        dir_path = Path(directory)
        if dir_path.exists():
            observer.schedule(watcher, str(dir_path), recursive=False)
            logger.info(f"Monitoring: {dir_path}")
        else:
            logger.warning(f"Directory does not exist: {dir_path}")
    
    observer.start()
    
    return observer, watcher
