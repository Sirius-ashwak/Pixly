"""OCR Engine component for text extraction from screenshots."""

import time
from dataclasses import dataclass, field
from pathlib import Path

import pytesseract
from PIL import Image, ImageEnhance, ImageFilter


@dataclass
class OCRResult:
    """Result of OCR text extraction."""
    text: str
    confidence: float  # 0-100
    language: str = "eng"
    processing_time: float = 0.0
    preprocessing_applied: list[str] = field(default_factory=list)


class OCRError(Exception):
    """Exception raised when OCR extraction fails."""
    pass


class OCREngine:
    """Extract text from screenshot images with intelligent preprocessing."""
    
    MIN_CONFIDENCE: int = 60
    MAX_WIDTH: int = 1920
    MAX_HEIGHT: int = 1080
    TESSERACT_CONFIG: str = '--oem 3 --psm 6'
    
    def __init__(self, tesseract_path: str | None = None) -> None:
        """Initialize OCR engine.
        
        Args:
            tesseract_path: Path to tesseract executable. Uses system default if None.
        """
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
    
    def extract(self, image_path: str) -> OCRResult:
        """Extract text from image with progressive preprocessing.
        
        Args:
            image_path: Path to the image file.
            
        Returns:
            OCRResult with extracted text and metadata.
        """
        start_time = time.time()
        preprocessing_applied: list[str] = []
        
        try:
            image = Image.open(image_path)
            
            # Resize if needed
            image, resized = self._resize_if_needed(image)
            if resized:
                preprocessing_applied.append("resize")
            
            # Initial extraction
            text, confidence = self._extract_with_confidence(image)
            
            # Progressive preprocessing if confidence is low
            if confidence < self.MIN_CONFIDENCE:
                image = self._to_grayscale(image)
                preprocessing_applied.append("grayscale")
                text, confidence = self._extract_with_confidence(image)
            
            if confidence < self.MIN_CONFIDENCE:
                image = self._enhance_contrast(image)
                preprocessing_applied.append("contrast")
                text, confidence = self._extract_with_confidence(image)
            
            if confidence < self.MIN_CONFIDENCE:
                image = self._sharpen(image)
                preprocessing_applied.append("sharpen")
                text, confidence = self._extract_with_confidence(image)
            
            if confidence < self.MIN_CONFIDENCE:
                image = self._threshold(image)
                preprocessing_applied.append("threshold")
                text, confidence = self._extract_with_confidence(image)
            
            processing_time = time.time() - start_time
            
            return OCRResult(
                text=text.strip(),
                confidence=confidence,
                language="eng",
                processing_time=processing_time,
                preprocessing_applied=preprocessing_applied
            )
            
        except Exception as e:
            # Return empty result on failure
            processing_time = time.time() - start_time
            return OCRResult(
                text="",
                confidence=0.0,
                language="eng",
                processing_time=processing_time,
                preprocessing_applied=preprocessing_applied
            )
    
    def _extract_with_confidence(self, image: Image.Image) -> tuple[str, float]:
        """Extract text and calculate confidence score.
        
        Args:
            image: PIL Image to process.
            
        Returns:
            Tuple of (extracted_text, confidence_score).
        """
        # Get detailed data including confidence
        data = pytesseract.image_to_data(image, config=self.TESSERACT_CONFIG, output_type=pytesseract.Output.DICT)
        
        # Calculate average confidence from word confidences
        confidences = [int(c) for c in data['conf'] if int(c) > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        # Get the text
        text = pytesseract.image_to_string(image, config=self.TESSERACT_CONFIG)
        
        return text, avg_confidence
    
    def _resize_if_needed(self, image: Image.Image) -> tuple[Image.Image, bool]:
        """Resize image if it exceeds maximum dimensions.
        
        Args:
            image: PIL Image to potentially resize.
            
        Returns:
            Tuple of (image, was_resized).
        """
        width, height = image.size
        
        if width <= self.MAX_WIDTH and height <= self.MAX_HEIGHT:
            return image, False
        
        # Calculate scale factor to fit within bounds
        scale = min(self.MAX_WIDTH / width, self.MAX_HEIGHT / height)
        new_width = int(width * scale)
        new_height = int(height * scale)
        
        resized = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        return resized, True
    
    def _to_grayscale(self, image: Image.Image) -> Image.Image:
        """Convert image to grayscale.
        
        Args:
            image: PIL Image to convert.
            
        Returns:
            Grayscale image.
        """
        return image.convert('L')
    
    def _enhance_contrast(self, image: Image.Image) -> Image.Image:
        """Enhance image contrast.
        
        Args:
            image: PIL Image to enhance.
            
        Returns:
            Contrast-enhanced image.
        """
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(2.0)
    
    def _sharpen(self, image: Image.Image) -> Image.Image:
        """Sharpen image.
        
        Args:
            image: PIL Image to sharpen.
            
        Returns:
            Sharpened image.
        """
        return image.filter(ImageFilter.SHARPEN)
    
    def _threshold(self, image: Image.Image) -> Image.Image:
        """Apply binary threshold to image.
        
        Args:
            image: PIL Image to threshold.
            
        Returns:
            Thresholded binary image.
        """
        # Ensure grayscale
        if image.mode != 'L':
            image = image.convert('L')
        
        # Apply threshold
        return image.point(lambda x: 255 if x > 128 else 0, '1')
