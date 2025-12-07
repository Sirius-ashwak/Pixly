# Requirements Document

## Introduction

ScreenSort is an AI-powered screenshot organization system that automatically monitors filesystem directories for new screenshots, extracts text using OCR, analyzes content using Google Gemini AI to determine category and purpose, renames files intelligently, organizes them into dated folder structures, indexes content for full-text search, and detects duplicate screenshots using perceptual hashing. The system targets knowledge workers (developers, students, designers) who capture 20-50 screenshots daily and struggle with organization, naming, and searchability.

## Glossary

- **ScreenSort**: The AI-powered screenshot organization system being developed
- **OCR (Optical Character Recognition)**: Technology that extracts text from images using Tesseract engine
- **Tesseract**: Open-source OCR engine (version 5.3.0+) used for text extraction
- **Gemini AI**: Google's AI model (gemini-1.5-flash) used for content categorization
- **FTS5**: SQLite Full-Text Search extension for instant content search
- **Perceptual Hash**: Image fingerprinting technique for duplicate detection
- **File Watcher**: Component using watchdog library to monitor filesystem for new files
- **Processing Pipeline**: Sequential workflow: OCR → AI Analysis → Rename → Organize → Index → Dedupe
- **Category**: Classification of screenshot content (Errors, Code, Memes, UI, Docs, Other)
- **Debounce**: Technique to prevent duplicate processing of rapidly created files (500ms window)

## Requirements

### Requirement 1

**User Story:** As a knowledge worker, I want new screenshots to be automatically detected and processed, so that I don't have to manually organize them.

#### Acceptance Criteria

1. WHEN a new .png or .jpg file is created in a monitored directory THEN the ScreenSort system SHALL detect the file within 500 milliseconds
2. WHEN a file is detected THEN the ScreenSort system SHALL apply a 500ms debounce window to prevent duplicate processing of the same file
3. WHEN multiple screenshots are created in rapid succession THEN the ScreenSort system SHALL queue them for sequential processing
4. WHILE a file is being written by another process THEN the ScreenSort system SHALL wait until the file is fully written before processing
5. WHEN a temporary file (starting with ~ or .) is created THEN the ScreenSort system SHALL ignore the file

### Requirement 2

**User Story:** As a user, I want text to be extracted from my screenshots, so that the content can be analyzed and searched.

#### Acceptance Criteria

1. WHEN a screenshot is processed THEN the ScreenSort OCR engine SHALL extract text using Tesseract with OEM 3 and PSM 6 configuration
2. WHEN initial OCR extraction yields confidence below 60% THEN the ScreenSort OCR engine SHALL apply progressive preprocessing strategies (grayscale, contrast enhancement, sharpening, thresholding)
3. WHEN OCR extraction completes THEN the ScreenSort OCR engine SHALL return the extracted text, confidence score (0-100), and list of preprocessing strategies applied
4. WHEN a screenshot exceeds 1920x1080 resolution THEN the ScreenSort OCR engine SHALL resize the image before processing to optimize performance
5. WHEN OCR extraction fails after all preprocessing strategies THEN the ScreenSort OCR engine SHALL return an empty result with zero confidence

### Requirement 3

**User Story:** As a user, I want my screenshots to be intelligently categorized, so that they are organized by content type.

#### Acceptance Criteria

1. WHEN OCR text is extracted with confidence above 30% and contains at least 5 characters THEN the ScreenSort AI analyzer SHALL send the text to Gemini API for categorization
2. WHEN the Gemini API responds THEN the ScreenSort AI analyzer SHALL parse the JSON response to extract category, description, tags, and confidence score
3. WHEN the Gemini API returns an invalid category THEN the ScreenSort AI analyzer SHALL default to the "Other" category
4. WHEN the Gemini API fails or OCR confidence is below 30% THEN the ScreenSort AI analyzer SHALL use rule-based fallback categorization using keyword matching
5. WHILE processing screenshots THEN the ScreenSort AI analyzer SHALL enforce a minimum 4-second interval between API requests to respect the 15 requests/minute rate limit
6. WHEN generating a description THEN the ScreenSort AI analyzer SHALL sanitize the text to contain only lowercase letters, numbers, and underscores with maximum 50 characters

### Requirement 4

**User Story:** As a user, I want my screenshots to be renamed with meaningful names, so that I can identify them without opening the files.

#### Acceptance Criteria

1. WHEN a screenshot is processed THEN the ScreenSort organizer SHALL generate a filename in the format "Screenshot_YYYY_MMM_D_description.ext"
2. WHEN the generated filename already exists in the target directory THEN the ScreenSort organizer SHALL append a numeric counter (e.g., _2, _3) to create a unique filename
3. WHEN more than 100 filename collisions occur THEN the ScreenSort organizer SHALL append a 6-character MD5 hash suffix instead of a counter
4. WHEN the description exceeds 40 characters THEN the ScreenSort organizer SHALL truncate the description to 40 characters

### Requirement 5

**User Story:** As a user, I want my screenshots organized into a logical folder structure, so that I can browse them by date and category.

#### Acceptance Criteria

1. WHEN a screenshot is processed THEN the ScreenSort organizer SHALL move the file to a directory structure of base_dir/YYYY/Month/Category/
2. WHEN the target directory does not exist THEN the ScreenSort organizer SHALL create the directory hierarchy automatically
3. WHEN a file move operation fails THEN the ScreenSort organizer SHALL preserve the original file in its source location and log the error
4. WHEN a screenshot is successfully moved THEN the ScreenSort organizer SHALL return the new file path and filename

### Requirement 6

**User Story:** As a user, I want to search my screenshots by content, so that I can quickly find specific screenshots.

#### Acceptance Criteria

1. WHEN a screenshot is processed THEN the ScreenSort database SHALL store metadata including filepath, original name, new name, category, description, OCR text, confidence scores, tags, file size, and timestamps
2. WHEN a screenshot record is inserted THEN the ScreenSort database SHALL automatically update the FTS5 full-text search index via database triggers
3. WHEN a user performs a search query THEN the ScreenSort database SHALL return matching results ranked by relevance within 100 milliseconds for up to 10,000 indexed screenshots
4. WHEN a search query is executed THEN the ScreenSort database SHALL search across filepath, new_name, ocr_text, and tags fields

### Requirement 7

**User Story:** As a user, I want duplicate screenshots to be detected, so that I can avoid wasting storage space.

#### Acceptance Criteria

1. WHEN a screenshot is processed THEN the ScreenSort deduplicator SHALL calculate a perceptual hash of the image
2. WHEN a perceptual hash matches an existing hash in the database THEN the ScreenSort deduplicator SHALL mark the screenshot as a duplicate
3. WHEN a duplicate is detected THEN the ScreenSort system SHALL mark the file as duplicate in the database without automatically deleting it
4. WHEN checking for near-duplicates THEN the ScreenSort deduplicator SHALL consider images with hamming distance of 5 or less as potential duplicates

### Requirement 8

**User Story:** As a user, I want to interact with ScreenSort via command line, so that I can control the system and search screenshots.

#### Acceptance Criteria

1. WHEN a user executes "screensort start" THEN the ScreenSort CLI SHALL start the background monitoring service and display a confirmation message
2. WHEN a user executes "screensort search [query]" THEN the ScreenSort CLI SHALL display matching screenshots with filename, filepath, and category
3. WHEN a user executes "screensort stats" THEN the ScreenSort CLI SHALL display total screenshots, total size, duplicate count, and breakdown by category
4. WHEN a user executes "screensort scan [directory]" THEN the ScreenSort CLI SHALL process all existing screenshots in the specified directory
5. WHEN a user executes "screensort config --add-dir [path]" THEN the ScreenSort CLI SHALL add the specified directory to the monitored directories list

### Requirement 9

**User Story:** As a user, I want a web dashboard to visualize my screenshot statistics, so that I can understand my screenshot usage patterns.

#### Acceptance Criteria

1. WHEN a user accesses http://localhost:5000 THEN the ScreenSort web dashboard SHALL display statistics cards showing total screenshots, total size, duplicate count, and space saved
2. WHEN the dashboard loads THEN the ScreenSort web dashboard SHALL display a bar chart showing screenshot counts by category
3. WHEN a user enters a search query in the dashboard THEN the ScreenSort web dashboard SHALL display matching results with filename, category, timestamp, and OCR preview
4. WHEN the dashboard loads THEN the ScreenSort web dashboard SHALL display the 20 most recently processed screenshots

### Requirement 10

**User Story:** As a user, I want my API keys stored securely, so that my credentials are protected.

#### Acceptance Criteria

1. WHEN storing the Gemini API key THEN the ScreenSort configuration system SHALL read the key from environment variables rather than plaintext configuration files
2. WHEN the API key is not found in environment variables THEN the ScreenSort system SHALL display an error message and refuse to start AI analysis

### Requirement 11

**User Story:** As a user, I want the system to handle errors gracefully, so that processing continues even when individual screenshots fail.

#### Acceptance Criteria

1. WHEN OCR extraction fails for a screenshot THEN the ScreenSort pipeline SHALL continue processing with fallback categorization
2. WHEN the Gemini API is unavailable THEN the ScreenSort pipeline SHALL use rule-based fallback categorization and continue processing
3. WHEN a file operation fails THEN the ScreenSort pipeline SHALL log the error and continue processing the next screenshot in the queue
4. WHEN the processing queue exceeds 100 items THEN the ScreenSort system SHALL drop the oldest pending file and log a warning
