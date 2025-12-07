"""Property-based tests for File Organizer.

Feature: screensort, Property 9: Filename format correctness
Feature: screensort, Property 10: Description truncation
Feature: screensort, Property 11: Directory path structure
Feature: screensort, Property 17: Collision resolution uniqueness
"""

import re
import tempfile
from datetime import datetime
from pathlib import Path

from hypothesis import given, strategies as st, settings

from pixly.core.organizer import FileOrganizer


# Strategies
valid_categories = st.sampled_from(['Errors', 'Code', 'Memes', 'UI', 'Docs', 'Other'])
valid_descriptions = st.text(
    alphabet='abcdefghijklmnopqrstuvwxyz0123456789_',
    min_size=1,
    max_size=60
)
valid_extensions = st.sampled_from(['.png', '.jpg', '.jpeg'])
valid_years = st.integers(min_value=2020, max_value=2030)
valid_months = st.integers(min_value=1, max_value=12)
valid_days = st.integers(min_value=1, max_value=28)


class TestFilenameFormat:
    """Property 9: Filename format correctness.
    
    *For any* date and description, the generated filename SHALL match
    the pattern `Screenshot_YYYY_MMM_D_<sanitized_description>.<ext>`.
    
    **Validates: Requirements 4.1**
    """
    
    @given(valid_descriptions, valid_extensions, valid_years, valid_months, valid_days)
    @settings(max_examples=100)
    def test_filename_format_matches_pattern(
        self, 
        description: str, 
        ext: str,
        year: int,
        month: int,
        day: int
    ):
        """Feature: screensort, Property 9: Filename format correctness"""
        with tempfile.TemporaryDirectory() as tmpdir:
            organizer = FileOrganizer(Path(tmpdir))
            
            # Create a fake source path
            source_path = Path(tmpdir) / f"test{ext}"
            timestamp = datetime(year, month, day)
            
            filename = organizer._generate_filename(source_path, description, timestamp)
            
            # Should match pattern: Screenshot_YYYY_Mon_DD_description.ext
            pattern = r'^Screenshot_\d{4}_[A-Z][a-z]{2}_\d{1,2}_[a-z0-9_]+\.(png|jpg|jpeg)$'
            assert re.match(pattern, filename), f"Filename '{filename}' doesn't match expected pattern"
            
            # Should start with Screenshot_
            assert filename.startswith('Screenshot_')
            
            # Should end with correct extension
            assert filename.endswith(ext)


class TestDescriptionTruncation:
    """Property 10: Description truncation.
    
    *For any* description exceeding 40 characters, the filename description
    portion SHALL be truncated to exactly 40 characters.
    
    **Validates: Requirements 4.4**
    """
    
    @given(st.text(alphabet='abcdefghijklmnopqrstuvwxyz0123456789_', min_size=41, max_size=100))
    @settings(max_examples=100)
    def test_long_description_truncated(self, long_description: str):
        """Feature: screensort, Property 10: Description truncation"""
        with tempfile.TemporaryDirectory() as tmpdir:
            organizer = FileOrganizer(Path(tmpdir))
            
            source_path = Path(tmpdir) / "test.png"
            timestamp = datetime(2025, 12, 6)
            
            filename = organizer._generate_filename(source_path, long_description, timestamp)
            
            # Extract description from filename
            # Format: Screenshot_YYYY_Mon_DD_description.ext
            parts = filename.rsplit('.', 1)[0]  # Remove extension
            desc_part = parts.split('_', 4)[-1]  # Get description part
            
            # Description should be at most 40 chars
            assert len(desc_part) <= FileOrganizer.MAX_DESCRIPTION_LENGTH
    
    @given(st.text(alphabet='abcdefghijklmnopqrstuvwxyz0123456789_', min_size=1, max_size=40))
    @settings(max_examples=100)
    def test_short_description_preserved(self, short_description: str):
        """Descriptions under 40 chars should be preserved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            organizer = FileOrganizer(Path(tmpdir))
            
            source_path = Path(tmpdir) / "test.png"
            timestamp = datetime(2025, 12, 6)
            
            filename = organizer._generate_filename(source_path, short_description, timestamp)
            
            # Description should be in filename
            assert short_description in filename


class TestDirectoryPathStructure:
    """Property 11: Directory path structure.
    
    *For any* date and category, the target directory path SHALL be
    `base_dir/YYYY/Month/Category/` where Month is the full month name.
    
    **Validates: Requirements 5.1**
    """
    
    @given(valid_categories, valid_years, valid_months, valid_days)
    @settings(max_examples=100)
    def test_directory_structure_format(
        self,
        category: str,
        year: int,
        month: int,
        day: int
    ):
        """Feature: screensort, Property 11: Directory path structure"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            organizer = FileOrganizer(base_dir)
            
            timestamp = datetime(year, month, day)
            
            target_dir = organizer._build_target_dir(category, timestamp)
            
            # Should be base_dir/YYYY/Month/Category
            expected_year = str(year)
            expected_month = timestamp.strftime("%B")  # Full month name
            
            assert target_dir.parent.parent.parent == base_dir
            assert target_dir.parent.parent.name == expected_year
            assert target_dir.parent.name == expected_month
            assert target_dir.name == category


class TestCollisionResolution:
    """Property 17: Collision resolution uniqueness.
    
    *For any* sequence of files with the same base filename, the collision
    resolution SHALL produce unique filenames for each file.
    
    **Validates: Requirements 4.2**
    """
    
    @given(st.integers(min_value=2, max_value=20))
    @settings(max_examples=100)
    def test_collision_produces_unique_names(self, num_files: int):
        """Feature: screensort, Property 17: Collision resolution uniqueness"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base_dir = Path(tmpdir)
            organizer = FileOrganizer(base_dir)
            
            base_path = base_dir / "test.png"
            
            # Generate multiple resolved paths
            resolved_paths = []
            for i in range(num_files):
                # Create the file so next resolution finds collision
                if i == 0:
                    base_path.touch()
                    resolved_paths.append(base_path)
                else:
                    resolved = organizer._resolve_collision(base_path)
                    resolved.touch()
                    resolved_paths.append(resolved)
            
            # All paths should be unique
            path_strings = [str(p) for p in resolved_paths]
            assert len(path_strings) == len(set(path_strings)), "Collision resolution produced duplicate paths"
