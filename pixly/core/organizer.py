"""File Organizer component for filename generation and file organization."""

import hashlib
import logging
import re
import shutil
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class FileOrganizer:
    """Generate meaningful filenames and organize files into folder structure."""
    
    MAX_DESCRIPTION_LENGTH: int = 40
    MAX_COLLISION_COUNTER: int = 100
    
    def __init__(self, base_dir: Path) -> None:
        """Initialize file organizer.
        
        Args:
            base_dir: Base directory for organized screenshots.
        """
        self._base_dir = Path(base_dir)
    
    def organize(
        self, 
        source_path: Path, 
        category: str, 
        description: str,
        timestamp: datetime | None = None
    ) -> tuple[Path, str]:
        """Organize a screenshot file into the target directory structure.
        
        Args:
            source_path: Path to the source screenshot file.
            category: Category for the screenshot.
            description: Description for the filename.
            timestamp: Optional timestamp (uses file mtime if not provided).
            
        Returns:
            Tuple of (new_filepath, new_filename).
            
        Raises:
            FileNotFoundError: If source file doesn't exist.
            OSError: If file move fails.
        """
        source_path = Path(source_path)
        
        if not source_path.exists():
            raise FileNotFoundError(f"Source file not found: {source_path}")
        
        # Get timestamp
        if timestamp is None:
            timestamp = datetime.fromtimestamp(source_path.stat().st_mtime)
        
        # Build target directory
        target_dir = self._build_target_dir(category, timestamp)
        
        # Generate filename
        new_filename = self._generate_filename(source_path, description, timestamp)
        
        # Resolve collisions
        target_path = self._resolve_collision(target_dir / new_filename)
        
        # Create directory if needed
        target_dir.mkdir(parents=True, exist_ok=True)
        
        # Move file
        try:
            shutil.move(str(source_path), str(target_path))
            return target_path, target_path.name
        except Exception as e:
            logger.error(f"Failed to move file {source_path} to {target_path}: {e}")
            raise
    
    def _generate_filename(
        self, 
        original_path: Path, 
        description: str,
        timestamp: datetime
    ) -> str:
        """Generate filename in format Screenshot_YYYY_MMM_D_description.ext.
        
        Args:
            original_path: Original file path (for extension).
            description: Description to include in filename.
            timestamp: Timestamp for the filename.
            
        Returns:
            Generated filename string.
        """
        # Truncate description if needed
        if len(description) > self.MAX_DESCRIPTION_LENGTH:
            description = description[:self.MAX_DESCRIPTION_LENGTH]
        
        # Format: Screenshot_YYYY_MMM_D_description.ext
        date_str = timestamp.strftime("%Y_%b_%d")  # e.g., 2025_Dec_6
        ext = original_path.suffix.lower()
        
        return f"Screenshot_{date_str}_{description}{ext}"
    
    def _build_target_dir(self, category: str, timestamp: datetime) -> Path:
        """Build target directory path: base_dir/YYYY/Month/Category/.
        
        Args:
            category: Screenshot category.
            timestamp: Timestamp for directory structure.
            
        Returns:
            Path to target directory.
        """
        year = str(timestamp.year)
        month = timestamp.strftime("%B")  # Full month name
        
        return self._base_dir / year / month / category
    
    def _resolve_collision(self, path: Path) -> Path:
        """Resolve filename collision by appending counter or hash.
        
        Args:
            path: Proposed file path.
            
        Returns:
            Unique file path.
        """
        if not path.exists():
            return path
        
        stem = path.stem
        suffix = path.suffix
        parent = path.parent
        
        # Try numeric counters first
        for i in range(2, self.MAX_COLLISION_COUNTER + 2):
            new_path = parent / f"{stem}_{i}{suffix}"
            if not new_path.exists():
                return new_path
        
        # Fall back to MD5 hash suffix
        hash_suffix = hashlib.md5(str(path).encode()).hexdigest()[:6]
        return parent / f"{stem}_{hash_suffix}{suffix}"
