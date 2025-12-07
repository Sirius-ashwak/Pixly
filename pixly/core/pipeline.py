"""Processing Pipeline component for orchestrating screenshot processing."""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

from .analyzer import AIAnalyzer
from .config import Config
from .database import ScreenshotDatabase, ScreenshotRecord
from .deduplicator import DuplicateDetector
from .ocr import OCREngine
from .organizer import FileOrganizer
from .watcher import ScreenshotWatcher, start_monitoring

logger = logging.getLogger(__name__)


class ProcessingPipeline:
    """Orchestrate all processing stages for a screenshot."""
    
    def __init__(self, config: Config) -> None:
        """Initialize processing pipeline.
        
        Args:
            config: Application configuration.
        """
        self._config = config
        
        # Initialize components
        self._ocr = OCREngine(config.tesseract_path)
        self._analyzer = AIAnalyzer(config.gemini_api_key, config.ai_model)
        self._organizer = FileOrganizer(config.screenshots_dir)
        self._db = ScreenshotDatabase(config.db_path)
        self._deduplicator = DuplicateDetector(self._db)
        
        # Watcher components (initialized on start)
        self._observer = None
        self._watcher = None
    
    def process_screenshot(self, filepath: str) -> None:
        """Process a single screenshot through the pipeline.
        
        Pipeline stages:
        1. OCR - Extract text from image
        2. AI Analysis - Categorize content
        3. Organize - Rename and move file
        4. Index - Store metadata in database
        5. Dedupe - Check for duplicates
        
        Args:
            filepath: Path to the screenshot file.
        """
        logger.info(f"Processing screenshot: {filepath}")
        
        try:
            original_path = Path(filepath)
            original_name = original_path.name
            file_size = original_path.stat().st_size
            created_at = datetime.fromtimestamp(original_path.stat().st_ctime)
            
            # Stage 1: OCR
            try:
                ocr_result = self._ocr.extract(filepath)
                logger.debug(f"OCR confidence: {ocr_result.confidence}")
            except Exception as e:
                logger.error(f"OCR failed: {e}")
                # Fallback: empty OCR result
                from .ocr import OCRResult
                ocr_result = OCRResult(
                    text="",
                    confidence=0.0,
                    language="eng",
                    processing_time=0.0,
                    preprocessing_applied=[]
                )
            
            # Stage 2: AI Analysis
            try:
                analysis = self._analyzer.analyze(ocr_result.text, ocr_result.confidence)
                logger.debug(f"Category: {analysis.category}")
            except Exception as e:
                logger.error(f"AI analysis failed: {e}")
                # Fallback: use fallback analysis
                analysis = self._analyzer._fallback_analysis(ocr_result.text)
            
            # Stage 3: Organize (rename and move)
            try:
                new_path, new_name = self._organizer.organize(
                    original_path,
                    analysis.category,
                    analysis.description,
                    created_at
                )
                logger.info(f"Organized to: {new_path}")
            except Exception as e:
                logger.error(f"Organization failed: {e}")
                # Keep original location
                new_path = original_path
                new_name = original_name
            
            # Stage 4: Index in database
            try:
                record = ScreenshotRecord(
                    id=None,
                    filepath=str(new_path),
                    original_name=original_name,
                    new_name=new_name,
                    category=analysis.category,
                    description=analysis.description,
                    ocr_text=ocr_result.text,
                    ocr_confidence=ocr_result.confidence,
                    ai_confidence=analysis.confidence,
                    tags=json.dumps(analysis.tags),
                    file_size=file_size,
                    created_at=created_at.isoformat(),
                    processed_at=datetime.now().isoformat(),
                    is_duplicate=False
                )
                record_id = self._db.insert(record)
                logger.debug(f"Indexed with ID: {record_id}")
            except Exception as e:
                logger.error(f"Database insert failed: {e}")
                record_id = None
            
            # Stage 5: Duplicate detection
            if record_id:
                try:
                    phash = self._deduplicator.calculate_hash(str(new_path))
                    is_dup, dup_of = self._deduplicator.check_duplicate(str(new_path))
                    
                    if is_dup:
                        self._db.mark_duplicate(record_id, dup_of)
                        logger.info(f"Marked as duplicate of {dup_of}")
                    
                    self._deduplicator.store_hash(record_id, phash, dup_of if is_dup else None)
                except Exception as e:
                    logger.error(f"Deduplication failed: {e}")
            
            logger.info(f"Successfully processed: {new_name}")
            
        except Exception as e:
            logger.error(f"Pipeline failed for {filepath}: {e}")
    
    def start(self) -> None:
        """Start the processing pipeline with file monitoring."""
        logger.info("Starting Pixly pipeline...")
        
        # Start monitoring
        self._observer, self._watcher = start_monitoring(
            self._config.monitored_dirs,
            self.process_screenshot
        )
        
        logger.info(f"Monitoring {len(self._config.monitored_dirs)} directories")
    
    def stop(self) -> None:
        """Stop the processing pipeline."""
        logger.info("Stopping Pixly pipeline...")
        
        if self._watcher:
            self._watcher.stop()
        
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5.0)
        
        self._db.close()
        
        logger.info("Pipeline stopped")
    
    def scan_directory(self, directory: Path) -> int:
        """Scan and process all existing screenshots in a directory.
        
        Args:
            directory: Directory to scan.
            
        Returns:
            Number of files processed.
        """
        logger.info(f"Scanning directory: {directory}")
        
        count = 0
        extensions = {'.png', '.jpg', '.jpeg'}
        
        for filepath in Path(directory).iterdir():
            if filepath.is_file() and filepath.suffix.lower() in extensions:
                # Skip temp files
                if filepath.name.startswith('~') or filepath.name.startswith('.'):
                    continue
                
                try:
                    self.process_screenshot(str(filepath))
                    count += 1
                except Exception as e:
                    logger.error(f"Failed to process {filepath}: {e}")
        
        logger.info(f"Scanned {count} files")
        return count
