"""Property-based tests for OCR Engine.

Feature: screensort, Property 4: OCR result structure completeness
Feature: screensort, Property 5: Large image resizing
"""

import tempfile
from pathlib import Path

from hypothesis import given, strategies as st, settings
from PIL import Image

from pixly.core.ocr import OCREngine, OCRResult


class TestOCRResultStructure:
    """Property 4: OCR result structure completeness.
    
    *For any* image processed by the OCR engine, the result SHALL contain
    text (possibly empty), confidence score in range [0, 100], and a list
    of preprocessing strategies applied.
    
    **Validates: Requirements 2.3**
    """
    
    @given(st.integers(min_value=100, max_value=300), st.integers(min_value=100, max_value=300))
    @settings(max_examples=50, deadline=None)
    def test_ocr_result_has_required_fields(self, width: int, height: int):
        """Feature: screensort, Property 4: OCR result structure completeness"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple test image
            img = Image.new('RGB', (width, height), (255, 255, 255))
            temp_path = Path(tmpdir) / "test.png"
            img.save(temp_path)
            
            engine = OCREngine()
            result = engine.extract(str(temp_path))
            
            # Verify result is OCRResult
            assert isinstance(result, OCRResult)
            
            # Verify text field exists and is string
            assert isinstance(result.text, str)
            
            # Verify confidence is in valid range [0, 100]
            assert isinstance(result.confidence, (int, float))
            assert 0 <= result.confidence <= 100
            
            # Verify preprocessing_applied is a list
            assert isinstance(result.preprocessing_applied, list)
            
            # Verify processing_time is non-negative
            assert result.processing_time >= 0
            
            # Verify language is set
            assert isinstance(result.language, str)
            assert len(result.language) > 0


class TestLargeImageResizing:
    """Property 5: Large image resizing.
    
    *For any* image with dimensions exceeding 1920x1080, the OCR engine
    SHALL resize the image before processing such that the processed
    dimensions are at most 1920x1080.
    
    **Validates: Requirements 2.4**
    """
    
    @given(
        st.integers(min_value=1921, max_value=3000),
        st.integers(min_value=1081, max_value=3000)
    )
    @settings(max_examples=50, deadline=None)
    def test_large_images_are_resized(self, width: int, height: int):
        """Feature: screensort, Property 5: Large image resizing"""
        engine = OCREngine()
        
        # Create oversized image
        img = Image.new('RGB', (width, height), (255, 255, 255))
        
        # Test resize function directly
        resized_img, was_resized = engine._resize_if_needed(img)
        
        # Should have been resized
        assert was_resized is True
        
        # Resulting dimensions should be within bounds
        new_width, new_height = resized_img.size
        assert new_width <= OCREngine.MAX_WIDTH
        assert new_height <= OCREngine.MAX_HEIGHT
    
    @given(
        st.integers(min_value=100, max_value=1920),
        st.integers(min_value=100, max_value=1080)
    )
    @settings(max_examples=50, deadline=None)
    def test_small_images_not_resized(self, width: int, height: int):
        """Images within bounds should not be resized."""
        engine = OCREngine()
        
        # Create image within bounds
        img = Image.new('RGB', (width, height), (255, 255, 255))
        
        # Test resize function
        resized_img, was_resized = engine._resize_if_needed(img)
        
        # Should not have been resized
        assert was_resized is False
        
        # Dimensions should be unchanged
        assert resized_img.size == (width, height)
