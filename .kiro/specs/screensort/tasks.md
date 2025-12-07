# Implementation Plan

- [x] 1. Set up project structure and dependencies


  - [x] 1.1 Create project directory structure and initialize Python package



    - Create `screensort/` package with `__init__.py`
    - Create subdirectories: `core/`, `cli/`, `web/`, `tests/`
    - Create `pyproject.toml` with dependencies
    - _Requirements: All_

  - [x] 1.2 Create configuration module and data classes


    - Implement `Config` dataclass with all configuration fields
    - Implement `load_config()` and `save_config()` functions
    - Load API key from environment variable `GEMINI_API_KEY`
    - _Requirements: 10.1, 10.2_

- [x] 2. Implement OCR Engine component


  - [x] 2.1 Create OCRResult dataclass and OCREngine class


    - Implement `OCRResult` with text, confidence, language, processing_time, preprocessing_applied
    - Implement `extract()` method with OEM 3 and PSM 6 configuration
    - _Requirements: 2.1, 2.3_


  - [x] 2.2 Implement preprocessing strategies
    - Implement grayscale, contrast, sharpen, threshold methods
    - Implement progressive preprocessing when confidence < 60%
    - Implement image resizing for images > 1920x1080
    - _Requirements: 2.2, 2.4, 2.5_

  - [x] 2.3 Write property tests for OCR Engine


    - **Property 4: OCR result structure completeness**
    - **Property 5: Large image resizing**
    - **Validates: Requirements 2.3, 2.4**


- [x] 3. Implement AI Analyzer component


  - [x] 3.1 Create AnalysisResult dataclass and AIAnalyzer class


    - Implement `AnalysisResult` with category, description, tags, confidence
    - Implement `analyze()` with confidence threshold check (>= 30%, >= 5 chars)
    - _Requirements: 3.1_


  - [x] 3.2 Implement response parsing and sanitization
    - Implement `_parse_response()` to extract JSON fields from Gemini response
    - Implement `_sanitize_description()` for lowercase, alphanumeric, underscore, max 50 chars
    - Implement invalid category fallback to "Other"
    - _Requirements: 3.2, 3.3, 3.6_


  - [x] 3.3 Implement fallback categorization and rate limiting
    - Implement `_fallback_analysis()` with keyword-based categorization
    - Implement `_enforce_rate_limit()` with 4-second minimum interval
    - _Requirements: 3.4, 3.5_

  - [x] 3.4 Write property tests for AI Analyzer


    - **Property 6: AI analysis threshold enforcement**
    - **Property 7: Invalid category fallback**
    - **Property 8: Description sanitization**
    - **Validates: Requirements 3.1, 3.3, 3.6**

- [x] 4. Implement File Organizer component

  - [x] 4.1 Create FileOrganizer class with filename generation


    - Implement `_generate_filename()` with format `Screenshot_YYYY_MMM_D_description.ext`
    - Implement description truncation to 40 characters
    - _Requirements: 4.1, 4.4_


  - [x] 4.2 Implement directory structure and collision resolution
    - Implement `_build_target_dir()` for `base_dir/YYYY/Month/Category/` structure
    - Implement `_resolve_collision()` with numeric counter and MD5 hash fallback
    - Implement `organize()` method to move files
    - _Requirements: 4.2, 4.3, 5.1, 5.2, 5.3, 5.4_

  - [x] 4.3 Write property tests for File Organizer


    - **Property 9: Filename format correctness**
    - **Property 10: Description truncation**
    - **Property 11: Directory path structure**
    - **Property 17: Collision resolution uniqueness**
    - **Validates: Requirements 4.1, 4.4, 5.1, 4.2**



- [ ] 5. Checkpoint
  - Ensure all tests pass, ask the user if questions arise.


- [x] 6. Implement Database component


  - [x] 6.1 Create ScreenshotRecord dataclass and database schema


    - Implement `ScreenshotRecord` dataclass with all metadata fields
    - Implement `_init_schema()` to create tables, FTS5 index, and triggers
    - _Requirements: 6.1, 6.2_

  - [x] 6.2 Implement CRUD operations and search

    - Implement `insert()` method for screenshot records
    - Implement `search()` method using FTS5 across filepath, new_name, ocr_text, tags
    - Implement `get_stats()` for statistics aggregation
    - _Requirements: 6.3, 6.4_

  - [x] 6.3 Write property tests for Database


    - **Property 12: Database record round-trip**
    - **Property 13: FTS index synchronization**
    - **Validates: Requirements 6.1, 6.2, 6.4**

- [x] 7. Implement Deduplicator component


  - [x] 7.1 Create DuplicateDetector class


    - Implement `calculate_hash()` using imagehash perceptual hashing
    - Implement `check_duplicate()` with hamming distance <= 5 threshold
    - Implement `store_hash()` to save hash and duplicate relationship
    - _Requirements: 7.1, 7.2, 7.3, 7.4_



  - [x] 7.2 Write property tests for Deduplicator
    - **Property 14: Perceptual hash consistency**
    - **Property 15: Duplicate detection by hash match**
    - **Property 16: Near-duplicate threshold**
    - **Validates: Requirements 7.1, 7.2, 7.3, 7.4**

- [x] 8. Implement File Watcher component


  - [x] 8.1 Create ScreenshotWatcher class


    - Implement `ScreenshotWatcher` extending `FileSystemEventHandler`
    - Implement `on_created()` to detect new .png/.jpg/.jpeg files
    - Implement temporary file filtering (~ and . prefixes)
    - Implement `_is_file_ready()` to check file is fully written
    - _Requirements: 1.1, 1.4, 1.5_


  - [x] 8.2 Implement debouncing and queue management
    - Implement 500ms debounce window using threading
    - Implement processing queue with max size 100
    - Implement `start_monitoring()` function
    - _Requirements: 1.2, 1.3, 11.4_

  - [x] 8.3 Write property tests for File Watcher


    - **Property 1: Debounce prevents duplicate processing**
    - **Property 2: Queue preserves all files**
    - **Property 3: Temporary file filtering**
    - **Validates: Requirements 1.2, 1.3, 1.5**

- [x] 9. Checkpoint

  - Ensure all tests pass, ask the user if questions arise.


- [x] 10. Implement Processing Pipeline


  - [x] 10.1 Create ProcessingPipeline orchestrator


    - Implement `process_screenshot()` to coordinate: OCR → AI → Organize → Index → Dedupe
    - Implement error handling with fallbacks at each stage
    - Implement `start()` and `stop()` methods
    - _Requirements: 11.1, 11.2, 11.3_

- [x] 11. Implement CLI Interface


  - [x] 11.1 Create CLI with argparse


    - Implement `screensort start` command to start monitoring
    - Implement `screensort search <query>` command
    - Implement `screensort stats` command
    - Implement `screensort scan <directory>` command
    - Implement `screensort config --add-dir <path>` command
    - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 12. Implement Web Dashboard

  - [x] 12.1 Create Flask web application


    - Implement `GET /` route for dashboard HTML
    - Implement `GET /api/stats` for statistics JSON
    - Implement `GET /api/search?q=<query>` for search results
    - Implement `GET /api/recent` for recent screenshots
    - Create dashboard HTML template with stats cards and charts
    - _Requirements: 9.1, 9.2, 9.3, 9.4_


- [x] 13. Final Checkpoint

  - Ensure all tests pass, ask the user if questions arise.
