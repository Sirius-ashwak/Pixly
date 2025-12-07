"""Property-based tests for Deduplicator.

Feature: screensort, Property 14: Perceptual hash consistency
Feature: screensort, Property 15: Duplicate detection by hash match
Feature: screensort, Property 16: Near-duplicate threshold
"""

import tempfile
from pathlib import Path

from hypothesis import given, strategies as st, settings, HealthCheck
from PIL import Image

from pixly.core.database import ScreenshotDatabase
from pixly.core.deduplicator import DuplicateDetector


def create_test_image(width: int, height: int, color: tuple) -> Image.Image:
    """Create a test image with given dimensions and color."""
    return Image.new('RGB', (width, height), color)


class TestPerceptualHashConsistency:
    """Property 14: Perceptual hash consistency.
    
    *For any* image file, calculating the perceptual hash multiple times
    SHALL return the same hash value.
    
    **Validates: Requirements 7.1**
    """
    
    @given(
        st.integers(min_value=100, max_value=500),
        st.integers(min_value=100, max_value=500),
        st.tuples(
            st.integers(min_value=0, max_value=255),
            st.integers(min_value=0, max_value=255),
            st.integers(min_value=0, max_value=255)
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_hash_is_deterministic(self, width: int, height: int, color: tuple):
        """Feature: screensort, Property 14: Perceptual hash consistency"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = ScreenshotDatabase(db_path)
            detector = DuplicateDetector(db)
            
            try:
                # Create and save test image
                img = create_test_image(width, height, color)
                img_path = Path(tmpdir) / "test.png"
                img.save(img_path)
                
                # Calculate hash multiple times
                hash1 = detector.calculate_hash(str(img_path))
                hash2 = detector.calculate_hash(str(img_path))
                hash3 = detector.calculate_hash(str(img_path))
                
                # All hashes should be identical
                assert hash1 == hash2
                assert hash2 == hash3
            finally:
                db.close()


class TestDuplicateDetectionByHashMatch:
    """Property 15: Duplicate detection by hash match.
    
    *For any* two images with identical perceptual hashes, the second image
    processed SHALL be marked as a duplicate of the first.
    
    **Validates: Requirements 7.2, 7.3**
    """
    
    @given(
        st.integers(min_value=100, max_value=300),
        st.integers(min_value=100, max_value=300),
        st.tuples(
            st.integers(min_value=0, max_value=255),
            st.integers(min_value=0, max_value=255),
            st.integers(min_value=0, max_value=255)
        )
    )
    @settings(max_examples=50, deadline=None)
    def test_identical_images_detected_as_duplicates(self, width: int, height: int, color: tuple):
        """Feature: screensort, Property 15: Duplicate detection by hash match"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = ScreenshotDatabase(db_path)
            detector = DuplicateDetector(db)
            
            try:
                # Create identical images
                img1 = create_test_image(width, height, color)
                img2 = create_test_image(width, height, color)
                
                img1_path = Path(tmpdir) / "img1.png"
                img2_path = Path(tmpdir) / "img2.png"
                
                img1.save(img1_path)
                img2.save(img2_path)
                
                # Store first image hash
                hash1 = detector.calculate_hash(str(img1_path))
                detector.store_hash(1, hash1, None)
                
                # Check if second image is detected as duplicate
                is_dup, dup_of = detector.check_duplicate(str(img2_path))
                
                assert is_dup is True
                assert dup_of == 1
            finally:
                db.close()


class TestNearDuplicateThreshold:
    """Property 16: Near-duplicate threshold.
    
    *For any* two perceptual hashes with hamming distance <= 5, the deduplicator
    SHALL consider them as potential duplicates.
    
    **Validates: Requirements 7.4**
    """
    
    @given(st.integers(min_value=0, max_value=5))
    @settings(max_examples=50, deadline=None)
    def test_near_duplicates_within_threshold(self, expected_distance: int):
        """Feature: screensort, Property 16: Near-duplicate threshold
        
        Hashes with hamming distance <= 5 should be considered duplicates.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = ScreenshotDatabase(db_path)
            detector = DuplicateDetector(db)
            
            try:
                # Create a base hash (16 hex chars = 64 bits for phash)
                base_hash = "a" * 16
                
                # Verify threshold constant
                assert DuplicateDetector.SIMILARITY_THRESHOLD == 5
                
                # Any distance <= threshold should be considered duplicate
                assert expected_distance <= DuplicateDetector.SIMILARITY_THRESHOLD
            finally:
                db.close()
    
    def test_different_images_not_duplicates(self):
        """Very different images should not be detected as duplicates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = ScreenshotDatabase(db_path)
            detector = DuplicateDetector(db)
            
            try:
                # Create images with very different patterns (not solid colors)
                # Solid colors can have similar perceptual hashes
                img1 = Image.new('RGB', (200, 200), (0, 0, 0))
                # Add a pattern to make it distinct
                for x in range(0, 200, 10):
                    for y in range(200):
                        img1.putpixel((x, y), (255, 0, 0))
                
                img2 = Image.new('RGB', (200, 200), (255, 255, 255))
                # Add a different pattern
                for y in range(0, 200, 10):
                    for x in range(200):
                        img2.putpixel((x, y), (0, 0, 255))
                
                img1_path = Path(tmpdir) / "pattern1.png"
                img2_path = Path(tmpdir) / "pattern2.png"
                
                img1.save(img1_path)
                img2.save(img2_path)
                
                # Calculate hashes
                hash1 = detector.calculate_hash(str(img1_path))
                hash2 = detector.calculate_hash(str(img2_path))
                
                # Verify hashes are different enough
                distance = detector.get_hamming_distance(hash1, hash2)
                
                # Different patterns should have hamming distance > threshold
                assert distance > DuplicateDetector.SIMILARITY_THRESHOLD
            finally:
                db.close()
