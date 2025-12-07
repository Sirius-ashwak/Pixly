"""Database component for metadata storage and full-text search."""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class ScreenshotRecord:
    """Record representing a processed screenshot."""
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
    is_duplicate: bool = False


class ScreenshotDatabase:
    """Store metadata and enable full-text search using SQLite with FTS5."""
    
    def __init__(self, db_path: Path) -> None:
        """Initialize database.
        
        Args:
            db_path: Path to SQLite database file.
        """
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path))
        self._conn.row_factory = sqlite3.Row
        self._init_schema()
    
    def _init_schema(self) -> None:
        """Initialize database schema with tables and FTS5 index."""
        cursor = self._conn.cursor()
        
        # Main screenshots table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS screenshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filepath TEXT UNIQUE NOT NULL,
                original_name TEXT NOT NULL,
                new_name TEXT NOT NULL,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                ocr_text TEXT,
                ocr_confidence REAL,
                ai_confidence REAL,
                tags TEXT,
                file_size INTEGER,
                created_at TEXT NOT NULL,
                processed_at TEXT NOT NULL,
                is_duplicate BOOLEAN DEFAULT 0
            )
        """)
        
        # FTS5 full-text search virtual table
        cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS screenshots_fts USING fts5(
                filepath,
                new_name,
                ocr_text,
                tags,
                content=screenshots,
                content_rowid=id
            )
        """)
        
        # Triggers to keep FTS index in sync
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS screenshots_ai AFTER INSERT ON screenshots BEGIN
                INSERT INTO screenshots_fts(rowid, filepath, new_name, ocr_text, tags)
                VALUES (new.id, new.filepath, new.new_name, new.ocr_text, new.tags);
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS screenshots_ad AFTER DELETE ON screenshots BEGIN
                INSERT INTO screenshots_fts(screenshots_fts, rowid, filepath, new_name, ocr_text, tags)
                VALUES ('delete', old.id, old.filepath, old.new_name, old.ocr_text, old.tags);
            END
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS screenshots_au AFTER UPDATE ON screenshots BEGIN
                INSERT INTO screenshots_fts(screenshots_fts, rowid, filepath, new_name, ocr_text, tags)
                VALUES ('delete', old.id, old.filepath, old.new_name, old.ocr_text, old.tags);
                INSERT INTO screenshots_fts(rowid, filepath, new_name, ocr_text, tags)
                VALUES (new.id, new.filepath, new.new_name, new.ocr_text, new.tags);
            END
        """)
        
        # Duplicates table for perceptual hashes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS duplicates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                screenshot_id INTEGER NOT NULL,
                perceptual_hash TEXT NOT NULL,
                duplicate_of INTEGER,
                FOREIGN KEY (screenshot_id) REFERENCES screenshots(id)
            )
        """)
        
        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_category ON screenshots(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_created ON screenshots(created_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_hash ON duplicates(perceptual_hash)")
        
        self._conn.commit()
    
    def insert(self, record: ScreenshotRecord) -> int:
        """Insert a screenshot record.
        
        Args:
            record: ScreenshotRecord to insert.
            
        Returns:
            ID of inserted record.
        """
        cursor = self._conn.cursor()
        
        cursor.execute("""
            INSERT INTO screenshots (
                filepath, original_name, new_name, category, description,
                ocr_text, ocr_confidence, ai_confidence, tags, file_size,
                created_at, processed_at, is_duplicate
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.filepath,
            record.original_name,
            record.new_name,
            record.category,
            record.description,
            record.ocr_text,
            record.ocr_confidence,
            record.ai_confidence,
            record.tags,
            record.file_size,
            record.created_at,
            record.processed_at,
            record.is_duplicate
        ))
        
        self._conn.commit()
        return cursor.lastrowid
    
    def get_by_id(self, record_id: int) -> Optional[ScreenshotRecord]:
        """Get a screenshot record by ID.
        
        Args:
            record_id: ID of record to retrieve.
            
        Returns:
            ScreenshotRecord or None if not found.
        """
        cursor = self._conn.cursor()
        cursor.execute("SELECT * FROM screenshots WHERE id = ?", (record_id,))
        row = cursor.fetchone()
        
        if row is None:
            return None
        
        return self._row_to_record(row)
    
    def search(self, query: str, limit: int = 50) -> list[ScreenshotRecord]:
        """Search screenshots using FTS5.
        
        Args:
            query: Search query string.
            limit: Maximum number of results.
            
        Returns:
            List of matching ScreenshotRecord objects.
        """
        cursor = self._conn.cursor()
        
        # Use FTS5 MATCH for full-text search
        cursor.execute("""
            SELECT s.* FROM screenshots s
            JOIN screenshots_fts fts ON s.id = fts.rowid
            WHERE screenshots_fts MATCH ?
            ORDER BY rank
            LIMIT ?
        """, (query, limit))
        
        return [self._row_to_record(row) for row in cursor.fetchall()]
    
    def get_stats(self) -> dict:
        """Get statistics about stored screenshots.
        
        Returns:
            Dictionary with statistics.
        """
        cursor = self._conn.cursor()
        
        # Total count
        cursor.execute("SELECT COUNT(*) FROM screenshots")
        total = cursor.fetchone()[0]
        
        # Total size
        cursor.execute("SELECT COALESCE(SUM(file_size), 0) FROM screenshots")
        total_size = cursor.fetchone()[0]
        
        # Duplicate count
        cursor.execute("SELECT COUNT(*) FROM screenshots WHERE is_duplicate = 1")
        duplicates = cursor.fetchone()[0]
        
        # By category
        cursor.execute("""
            SELECT category, COUNT(*) as count 
            FROM screenshots 
            GROUP BY category
        """)
        by_category = {row['category']: row['count'] for row in cursor.fetchall()}
        
        return {
            'total': total,
            'total_size': total_size,
            'duplicates': duplicates,
            'by_category': by_category
        }
    
    def get_recent(self, limit: int = 20) -> list[ScreenshotRecord]:
        """Get most recently processed screenshots.
        
        Args:
            limit: Maximum number of results.
            
        Returns:
            List of ScreenshotRecord objects.
        """
        cursor = self._conn.cursor()
        cursor.execute("""
            SELECT * FROM screenshots 
            ORDER BY processed_at DESC 
            LIMIT ?
        """, (limit,))
        
        return [self._row_to_record(row) for row in cursor.fetchall()]
    
    def mark_duplicate(self, record_id: int, duplicate_of: Optional[int] = None) -> None:
        """Mark a screenshot as duplicate.
        
        Args:
            record_id: ID of record to mark.
            duplicate_of: ID of original record (optional).
        """
        cursor = self._conn.cursor()
        cursor.execute(
            "UPDATE screenshots SET is_duplicate = 1 WHERE id = ?",
            (record_id,)
        )
        self._conn.commit()
    
    def _row_to_record(self, row: sqlite3.Row) -> ScreenshotRecord:
        """Convert database row to ScreenshotRecord.
        
        Args:
            row: SQLite Row object.
            
        Returns:
            ScreenshotRecord instance.
        """
        return ScreenshotRecord(
            id=row['id'],
            filepath=row['filepath'],
            original_name=row['original_name'],
            new_name=row['new_name'],
            category=row['category'],
            description=row['description'],
            ocr_text=row['ocr_text'],
            ocr_confidence=row['ocr_confidence'],
            ai_confidence=row['ai_confidence'],
            tags=row['tags'],
            file_size=row['file_size'],
            created_at=row['created_at'],
            processed_at=row['processed_at'],
            is_duplicate=bool(row['is_duplicate'])
        )
    
    def close(self) -> None:
        """Close database connection."""
        self._conn.close()
