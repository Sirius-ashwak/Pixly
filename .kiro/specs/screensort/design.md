# ScreenSort Design Document

## Overview

ScreenSort is a Python-based desktop application that provides real-time screenshot organization through AI-powered content analysis. The system monitors designated filesystem directories, processes new screenshots through an OCR and AI pipeline, and organizes them into a structured folder hierarchy with meaningful filenames. A SQLite database with FTS5 enables instant full-text search, while perceptual hashing detects duplicates.

The architecture follows a pipeline pattern where each component has a single responsibility, enabling easy testing and maintenance. The system is designed for Windows 10/11 as the primary target platform, with Python 3.11+ as the runtime.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER LAYER                               │
│  • Takes screenshots (Ctrl+Shift+S, Snipping Tool, etc.)        │
│  • CLI: screensort [start|search|stats|scan|config]             │
│  • Web Dashboard: http://localhost:5000                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                    INTERFACE LAYER                               │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │  CLI (argparse)  │  │  Flask Web App   │                     │
│  └────────┬─────────┘  └────────┬─────────┘                     │
└───────────┼─────────────────────┼───────────────────────────────┘
            │                     │
┌───────────▼─────────────────────▼───────────────────────────────┐
│                    CORE LAYER                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Processing Pipeline (Orchestrator)                       │   │
│  │  • Coordinates all processing stages                      │   │
│  │  • Handles errors and fallbacks                           │   │
│  └──────────────────────────────────────────────────────────┘   │
│                             │                                    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │
│  │  File    │→│  OCR     │→│  AI      │→│  File    │           │
│  │  Watcher │ │  Engine  │ │  Analyzer│ │  Organizer│          │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │
│                                                                  │
│  ┌──────────────────┐  ┌──────────────────┐                     │
│  │  Deduplicator    │  │  Config Manager  │                     │
│  └──────────────────┘  └──────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      DATA LAYER                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  SQLite Database (screenshots.db)                        │   │
│  │  • screenshots table (metadata)                          │   │
│  │  • screenshots_fts (FTS5 full-text search)              │   │
│  │  • duplicates table (perceptual hashes)                 │   │
│  │  • analytics table (daily stats)                        │   │
│  └──────────────────────────────────────────────────────────┘   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  File System                                              │   │
│  │  ~/Screenshots/YYYY/Month/Category/                       │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

## Components and Interfaces

### 1. File Watcher Component

**Responsibility:** Monitor filesystem directories for new screenshot files in real-time.

**Interface:**
```python
class ScreenshotWatcher(FileSystemEventHandler):
    MONITORED_EXTENSIONS: set[str] = {'.png', '.jpg', '.jpeg'}
    DEBOUNCE_WINDOW: float = 0.5  # seconds
    MAX_QUEUE_SIZE: int = 100
    
    def __init__(self, processor_callback: Callable[[str], None]) -> None: ...
    def on_created(self, event: FileSystemEvent) -> None: ...
    def _debounce_worker(self) -> None: ...
    def _is_file_ready(self, filepath: str) -> bool: ...

def start_monitoring(directories: list[Path], processor: Callable) -> Observer: ...
```

**Dependencies:** watchdog library

### 2. OCR Engine Component

**Responsibility:** Extract text from screenshot images with intelligent preprocessing.

**Interface:**
```python
@dataclass
class OCRResult:
    text: str
    confidence: float  # 0-100
    language: str
    processing_time: float
    preprocessing_applied: list[str]

class OCREngine:
    MIN_CONFIDENCE: int = 60
    TESSERACT_CONFIG: str = '--oem 3 --psm 6'
    
    def __init__(self, tesseract_path: Optional[str] = None) -> None: ...
    def extract(self, image_path: str) -> OCRResult: ...
    def _calculate_confidence(self, image: Image) -> float: ...
    def _to_grayscale(self, image: Image) -> Image: ...
    def _enhance_contrast(self, image: Image) -> Image: ...
    def _sharpen(self, image: Image) -> Image: ...
    def _threshold(self, image: Image) -> Image: ...

class OCRError(Exception): ...
```

**Dependencies:** pytesseract, Pillow

### 3. AI Analyzer Component

**Responsibility:** Categorize screenshot content and generate intelligent descriptions.

**Interface:**
```python
@dataclass
class AnalysisResult:
    category: str  # 'Errors', 'Code', 'Memes', 'UI', 'Docs', 'Other'
    description: str  # max 50 chars, sanitized
    tags: list[str]  # max 5 tags
    confidence: float  # 0-1
    raw_response: str

class AIAnalyzer:
    CATEGORIES: list[str] = ['Errors', 'Code', 'Memes', 'UI', 'Docs', 'Other']
    
    def __init__(self, api_key: str, model: str = 'gemini-1.5-flash') -> None: ...
    def analyze(self, ocr_text: str, ocr_confidence: float) -> AnalysisResult: ...
    def _parse_response(self, response_text: str) -> AnalysisResult: ...
    def _fallback_analysis(self, text: str) -> AnalysisResult: ...
    def _sanitize_description(self, desc: str) -> str: ...
    def _enforce_rate_limit(self) -> None: ...
```

**Dependencies:** google-generativeai

### 4. File Organizer Component

**Responsibility:** Generate meaningful filenames and organize files into folder structure.

**Interface:**
```python
class FileOrganizer:
    def __init__(self, base_dir: Path) -> None: ...
    def organize(self, source_path: Path, category: str, description: str) -> tuple[Path, str]: ...
    def _generate_filename(self, original_path: Path, description: str) -> str: ...
    def _build_target_dir(self, category: str) -> Path: ...
    def _resolve_collision(self, path: Path) -> Path: ...
```

**Dependencies:** None (stdlib only)

### 5. Database Component

**Responsibility:** Store metadata and enable full-text search.

**Interface:**
```python
@dataclass
class ScreenshotRecord:
    id: Optional[int]
    filepath: str
    original_name: str
    new_name: str
    category: str
    description: str
    ocr_text: str
    ocr_confidence: float
    ai_confidence: float
    tags: str  # JSON array as string
    file_size: int
    created_at: str
    processed_at: str
    is_duplicate: bool

class ScreenshotDatabase:
    def __init__(self, db_path: Path) -> None: ...
    def _init_schema(self) -> None: ...
    def insert(self, record: ScreenshotRecord) -> int: ...
    def search(self, query: str, limit: int = 50) -> list[ScreenshotRecord]: ...
    def get_stats(self) -> dict: ...
    def close(self) -> None: ...
```

**Dependencies:** sqlite3 (stdlib)

### 6. Deduplicator Component

**Responsibility:** Detect duplicate screenshots using perceptual hashing.

**Interface:**
```python
class DuplicateDetector:
    SIMILARITY_THRESHOLD: int = 5  # hamming distance
    
    def __init__(self, db: ScreenshotDatabase) -> None: ...
    def check_duplicate(self, filepath: str) -> bool: ...
    def calculate_hash(self, filepath: str) -> str: ...
    def store_hash(self, screenshot_id: int, phash: str, duplicate_of: Optional[int]) -> None: ...
```

**Dependencies:** imagehash, Pillow

### 7. Processing Pipeline Component

**Responsibility:** Orchestrate all processing stages for a screenshot.

**Interface:**
```python
class ProcessingPipeline:
    def __init__(self, config: Config) -> None: ...
    def process_screenshot(self, filepath: str) -> None: ...
    def start(self) -> None: ...
    def stop(self) -> None: ...
```

### 8. Configuration Manager Component

**Responsibility:** Load and manage application configuration.

**Interface:**
```python
@dataclass
class Config:
    monitored_dirs: list[Path]
    screenshots_dir: Path
    db_path: Path
    gemini_api_key: str
    tesseract_path: Optional[str]
    ocr_min_confidence: int
    ai_model: str
    ai_rate_limit_rpm: int

def load_config(config_path: Path = None) -> Config: ...
def save_config(config: Config, config_path: Path) -> None: ...
```

### 9. CLI Interface

**Responsibility:** Provide command-line interface for user interaction.

**Commands:**
- `screensort start` - Start background monitoring
- `screensort stop` - Stop background service
- `screensort search <query>` - Search screenshots
- `screensort stats` - Display statistics
- `screensort scan <directory>` - Process existing screenshots
- `screensort config --add-dir <path>` - Add monitored directory

### 10. Web Dashboard

**Responsibility:** Provide visual interface for statistics and search.

**Endpoints:**
- `GET /` - Dashboard HTML page
- `GET /api/stats` - Statistics JSON
- `GET /api/search?q=<query>` - Search results JSON
- `GET /api/recent` - Recent screenshots JSON

## Data Models

### Database Schema

```sql
-- Main screenshots table
CREATE TABLE screenshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filepath TEXT UNIQUE NOT NULL,
    original_name TEXT NOT NULL,
    new_name TEXT NOT NULL,
    category TEXT NOT NULL,
    description TEXT NOT NULL,
    ocr_text TEXT,
    ocr_confidence REAL,
    ai_confidence REAL,
    tags TEXT,  -- JSON array
    file_size INTEGER,
    created_at TEXT NOT NULL,
    processed_at TEXT NOT NULL,
    is_duplicate BOOLEAN DEFAULT 0
);

-- FTS5 full-text search virtual table
CREATE VIRTUAL TABLE screenshots_fts USING fts5(
    filepath,
    new_name,
    ocr_text,
    tags,
    content=screenshots,
    content_rowid=id
);

-- Duplicates table for perceptual hashes
CREATE TABLE duplicates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    screenshot_id INTEGER NOT NULL,
    perceptual_hash TEXT NOT NULL,
    duplicate_of INTEGER,
    FOREIGN KEY (screenshot_id) REFERENCES screenshots(id)
);

-- Analytics table for daily stats
CREATE TABLE analytics (
    date TEXT PRIMARY KEY,
    total_screenshots INTEGER,
    by_category TEXT,  -- JSON object
    total_size_mb REAL
);

-- Indexes
CREATE INDEX idx_category ON screenshots(category);
CREATE INDEX idx_created ON screenshots(created_at);
CREATE INDEX idx_hash ON duplicates(perceptual_hash);
```

### Configuration File (YAML)

```yaml
monitored_dirs:
  - ~/Desktop
  - ~/Screenshots
  - ~/Downloads
screenshots_dir: ~/Screenshots
db_path: ~/.screensort/screenshots.db
gemini_api_key: ${GEMINI_API_KEY}
tesseract_path: "C:/Program Files/Tesseract-OCR/tesseract.exe"
ocr:
  min_confidence: 60
  languages: ["eng"]
ai:
  model: "gemini-1.5-flash"
  rate_limit_rpm: 15
organization:
  date_format: "%Y/%B"
  categories: [Errors, Code, Memes, UI, Docs, Other]
deduplication:
  enabled: true
  auto_delete: false
  similarity_threshold: 5
```

### File System Structure

```
~/Screenshots/
├── 2025/
│   ├── December/
│   │   ├── Errors/
│   │   │   └── Screenshot_2025_Dec_6_python_import_error.png
│   │   ├── Code/
│   │   ├── Memes/
│   │   ├── UI/
│   │   ├── Docs/
│   │   └── Other/
│   └── January/
└── 2024/
```

