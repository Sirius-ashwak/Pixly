"""Deduplicator component for duplicate screenshot detection."""

from typing import Optional

import imagehash
from PIL import Image

from .database import ScreenshotDatabase


class DuplicateDetector:
    """Detect duplicate screenshots using perceptual hashing."""
    
    SIMILARITY_THRESHOLD: int = 5  # hamming distance
    
    def __init__(self, db: ScreenshotDatabase) -> None:
        """Initialize duplicate detector.
        
        Args:
            db: Database instance for storing and querying hashes.
        """
        self._db = db
        self._conn = db._conn  # Access underlying connection for hash queries
    
    def check_duplicate(self, filepath: str) -> tuple[bool, Optional[int]]:
        """Check if a screenshot is a duplicate.
        
        Args:
            filepath: Path to the image file.
            
        Returns:
            Tuple of (is_duplicate, duplicate_of_id).
        """
        # Calculate hash of new image
        new_hash = self.calculate_hash(filepath)
        
        # Query existing hashes
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT screenshot_id, perceptual_hash 
            FROM duplicates
        """)
        
        for row in cursor.fetchall():
            existing_hash = imagehash.hex_to_hash(row[1])
            new_hash_obj = imagehash.hex_to_hash(new_hash)
            
            # Calculate hamming distance
            distance = new_hash_obj - existing_hash
            
            if distance <= self.SIMILARITY_THRESHOLD:
                return True, row[0]
        
        return False, None
    
    def calculate_hash(self, filepath: str) -> str:
        """Calculate perceptual hash of an image.
        
        Args:
            filepath: Path to the image file.
            
        Returns:
            Hex string representation of the perceptual hash.
        """
        image = Image.open(filepath)
        phash = imagehash.phash(image)
        return str(phash)
    
    def store_hash(
        self, 
        screenshot_id: int, 
        phash: str, 
        duplicate_of: Optional[int] = None
    ) -> None:
        """Store hash in database.
        
        Args:
            screenshot_id: ID of the screenshot record.
            phash: Perceptual hash string.
            duplicate_of: ID of original if this is a duplicate.
        """
        cursor = self._conn.cursor()
        cursor.execute("""
            INSERT INTO duplicates (screenshot_id, perceptual_hash, duplicate_of)
            VALUES (?, ?, ?)
        """, (screenshot_id, phash, duplicate_of))
        self._conn.commit()
    
    def get_hamming_distance(self, hash1: str, hash2: str) -> int:
        """Calculate hamming distance between two hashes.
        
        Args:
            hash1: First hash string.
            hash2: Second hash string.
            
        Returns:
            Hamming distance (number of differing bits).
        """
        h1 = imagehash.hex_to_hash(hash1)
        h2 = imagehash.hex_to_hash(hash2)
        return h1 - h2
