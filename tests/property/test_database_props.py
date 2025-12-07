"""Property-based tests for Database.

Feature: screensort, Property 12: Database record round-trip
Feature: screensort, Property 13: FTS index synchronization
"""

import json
import tempfile
import uuid
from datetime import datetime
from pathlib import Path

from hypothesis import given, strategies as st, settings, HealthCheck

from pixly.core.database import ScreenshotDatabase, ScreenshotRecord


# Strategies for generating valid record data
valid_categories = st.sampled_from(['Errors', 'Code', 'Memes', 'UI', 'Docs', 'Other'])
valid_descriptions = st.text(alphabet='abcdefghijklmnopqrstuvwxyz0123456789_', min_size=1, max_size=40)
valid_ocr_text = st.text(min_size=0, max_size=500)
valid_confidence = st.floats(min_value=0.0, max_value=100.0, allow_nan=False)
valid_ai_confidence = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
valid_file_size = st.integers(min_value=0, max_value=100_000_000)


def make_unique_filepath() -> str:
    """Generate a unique filepath for testing."""
    return f"/test/screenshots/{uuid.uuid4()}.png"


@st.composite
def screenshot_records(draw):
    """Strategy for generating valid ScreenshotRecord objects."""
    tags = draw(st.lists(st.text(alphabet='abcdefghijklmnopqrstuvwxyz', min_size=1, max_size=20), max_size=5))
    
    return ScreenshotRecord(
        id=None,
        filepath=make_unique_filepath(),
        original_name=draw(st.text(alphabet='abcdefghijklmnopqrstuvwxyz0123456789_.', min_size=5, max_size=50)) + '.png',
        new_name=draw(valid_descriptions) + '.png',
        category=draw(valid_categories),
        description=draw(valid_descriptions),
        ocr_text=draw(valid_ocr_text),
        ocr_confidence=draw(valid_confidence),
        ai_confidence=draw(valid_ai_confidence),
        tags=json.dumps(tags),
        file_size=draw(valid_file_size),
        created_at=datetime.now().isoformat(),
        processed_at=datetime.now().isoformat(),
        is_duplicate=draw(st.booleans())
    )


class TestDatabaseRoundTrip:
    """Property 12: Database record round-trip.
    
    *For any* ScreenshotRecord inserted into the database, querying by its ID
    SHALL return an equivalent record with all fields preserved.
    
    **Validates: Requirements 6.1**
    """
    
    @given(screenshot_records())
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_insert_then_get_preserves_data(self, record: ScreenshotRecord):
        """Feature: screensort, Property 12: Database record round-trip"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = ScreenshotDatabase(db_path)
            
            try:
                # Insert record
                record_id = db.insert(record)
                
                # Retrieve record
                retrieved = db.get_by_id(record_id)
                
                # Verify all fields match
                assert retrieved is not None
                assert retrieved.id == record_id
                assert retrieved.filepath == record.filepath
                assert retrieved.original_name == record.original_name
                assert retrieved.new_name == record.new_name
                assert retrieved.category == record.category
                assert retrieved.description == record.description
                assert retrieved.ocr_text == record.ocr_text
                assert abs(retrieved.ocr_confidence - record.ocr_confidence) < 0.001
                assert abs(retrieved.ai_confidence - record.ai_confidence) < 0.001
                assert retrieved.tags == record.tags
                assert retrieved.file_size == record.file_size
                assert retrieved.is_duplicate == record.is_duplicate
            finally:
                db.close()


class TestFTSIndexSynchronization:
    """Property 13: FTS index synchronization.
    
    *For any* screenshot record inserted into the database, a search query
    containing unique text from that record's ocr_text, new_name, filepath,
    or tags SHALL return that record in results.
    
    **Validates: Requirements 6.2, 6.4**
    """
    
    @given(st.text(alphabet='abcdefghijklmnopqrstuvwxyz', min_size=8, max_size=20))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow])
    def test_inserted_record_searchable_by_ocr_text(self, unique_text: str):
        """Feature: screensort, Property 13: FTS index synchronization
        
        Records should be searchable by OCR text.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = ScreenshotDatabase(db_path)
            
            try:
                # Create record with unique OCR text
                record = ScreenshotRecord(
                    id=None,
                    filepath=make_unique_filepath(),
                    original_name="test.png",
                    new_name="screenshot_test.png",
                    category="Other",
                    description="test",
                    ocr_text=f"some text with {unique_text} in it",
                    ocr_confidence=80.0,
                    ai_confidence=0.8,
                    tags="[]",
                    file_size=1000,
                    created_at=datetime.now().isoformat(),
                    processed_at=datetime.now().isoformat(),
                    is_duplicate=False
                )
                
                record_id = db.insert(record)
                
                # Search for the unique text
                results = db.search(unique_text)
                
                # Should find the record
                assert len(results) >= 1
                assert any(r.id == record_id for r in results)
            finally:
                db.close()
    
    @given(st.text(alphabet='abcdefghijklmnopqrstuvwxyz', min_size=8, max_size=20))
    @settings(max_examples=50, suppress_health_check=[HealthCheck.too_slow], deadline=None)
    def test_inserted_record_searchable_by_new_name(self, unique_name: str):
        """Feature: screensort, Property 13: FTS index synchronization
        
        Records should be searchable by new filename.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            db = ScreenshotDatabase(db_path)
            
            try:
                record = ScreenshotRecord(
                    id=None,
                    filepath=make_unique_filepath(),
                    original_name="test.png",
                    new_name=f"screenshot_{unique_name}.png",
                    category="Other",
                    description="test",
                    ocr_text="some ocr text",
                    ocr_confidence=80.0,
                    ai_confidence=0.8,
                    tags="[]",
                    file_size=1000,
                    created_at=datetime.now().isoformat(),
                    processed_at=datetime.now().isoformat(),
                    is_duplicate=False
                )
                
                record_id = db.insert(record)
                
                # Search for the unique name
                results = db.search(unique_name)
                
                # Should find the record
                assert len(results) >= 1
                assert any(r.id == record_id for r in results)
            finally:
                db.close()
