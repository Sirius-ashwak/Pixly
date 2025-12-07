"""Property-based tests for AI Analyzer.

Feature: screensort, Property 6: AI analysis threshold enforcement
Feature: screensort, Property 7: Invalid category fallback
Feature: screensort, Property 8: Description sanitization
"""

from hypothesis import given, strategies as st, settings

from pixly.core.analyzer import AIAnalyzer, AnalysisResult


class TestAIAnalysisThreshold:
    """Property 6: AI analysis threshold enforcement.
    
    *For any* OCR result with confidence >= 30% and text length >= 5 characters,
    the AI analyzer SHALL attempt Gemini API categorization.
    
    **Validates: Requirements 3.1**
    """
    
    @given(
        st.floats(min_value=0.0, max_value=29.9),
        st.text(min_size=5, max_size=100)
    )
    @settings(max_examples=100)
    def test_low_confidence_uses_fallback(self, confidence: float, text: str):
        """Feature: screensort, Property 6: AI analysis threshold enforcement
        
        When confidence is below 30%, fallback should be used (no API call).
        """
        # Create analyzer with dummy key (won't be used for fallback)
        analyzer = AIAnalyzer(api_key="dummy_key")
        
        # With low confidence, should use fallback (no API call)
        result = analyzer.analyze(text, confidence)
        
        # Result should be valid
        assert isinstance(result, AnalysisResult)
        assert result.category in AIAnalyzer.CATEGORIES
        # Fallback has low confidence
        assert result.confidence <= 0.5
    
    @given(st.text(min_size=0, max_size=4))
    @settings(max_examples=100)
    def test_short_text_uses_fallback(self, text: str):
        """Feature: screensort, Property 6: AI analysis threshold enforcement
        
        When text is shorter than 5 characters, fallback should be used.
        """
        analyzer = AIAnalyzer(api_key="dummy_key")
        
        # With short text, should use fallback regardless of confidence
        result = analyzer.analyze(text, 100.0)
        
        assert isinstance(result, AnalysisResult)
        assert result.category in AIAnalyzer.CATEGORIES


class TestInvalidCategoryFallback:
    """Property 7: Invalid category fallback.
    
    *For any* category string not in the valid categories list,
    the AI analyzer SHALL return 'Other' as the category.
    
    **Validates: Requirements 3.3**
    """
    
    @given(st.text(min_size=1, max_size=50).filter(lambda x: x not in AIAnalyzer.CATEGORIES))
    @settings(max_examples=100)
    def test_invalid_category_becomes_other(self, invalid_category: str):
        """Feature: screensort, Property 7: Invalid category fallback"""
        analyzer = AIAnalyzer(api_key="dummy_key")
        
        # Simulate parsing a response with invalid category
        fake_response = f'{{"category": "{invalid_category}", "description": "test", "tags": [], "confidence": 0.5}}'
        
        result = analyzer._parse_response(fake_response)
        
        # Invalid category should become 'Other'
        assert result.category == 'Other'
    
    @given(st.sampled_from(AIAnalyzer.CATEGORIES))
    @settings(max_examples=100)
    def test_valid_category_preserved(self, valid_category: str):
        """Valid categories should be preserved."""
        analyzer = AIAnalyzer(api_key="dummy_key")
        
        fake_response = f'{{"category": "{valid_category}", "description": "test", "tags": [], "confidence": 0.5}}'
        
        result = analyzer._parse_response(fake_response)
        
        assert result.category == valid_category


class TestDescriptionSanitization:
    """Property 8: Description sanitization.
    
    *For any* input string, the sanitized description SHALL contain only
    lowercase letters, numbers, and underscores, with length at most 50 characters.
    
    **Validates: Requirements 3.6**
    """
    
    @given(st.text(min_size=0, max_size=200))
    @settings(max_examples=100)
    def test_sanitized_description_format(self, input_desc: str):
        """Feature: screensort, Property 8: Description sanitization"""
        analyzer = AIAnalyzer(api_key="dummy_key")
        
        sanitized = analyzer._sanitize_description(input_desc)
        
        # Should only contain allowed characters
        import re
        assert re.match(r'^[a-z0-9_]*$', sanitized) or sanitized == 'screenshot'
        
        # Should not exceed max length
        assert len(sanitized) <= AIAnalyzer.MAX_DESCRIPTION_LENGTH
        
        # Should not be empty (defaults to 'screenshot')
        assert len(sanitized) > 0
    
    @given(st.text(min_size=51, max_size=200))
    @settings(max_examples=100)
    def test_long_description_truncated(self, long_desc: str):
        """Feature: screensort, Property 8: Description sanitization
        
        Descriptions longer than 50 chars should be truncated.
        """
        analyzer = AIAnalyzer(api_key="dummy_key")
        
        sanitized = analyzer._sanitize_description(long_desc)
        
        assert len(sanitized) <= AIAnalyzer.MAX_DESCRIPTION_LENGTH
    
    @given(st.text(alphabet='ABCDEFGHIJKLMNOPQRSTUVWXYZ', min_size=5, max_size=20))
    @settings(max_examples=100)
    def test_uppercase_converted_to_lowercase(self, uppercase_desc: str):
        """Uppercase letters should be converted to lowercase."""
        analyzer = AIAnalyzer(api_key="dummy_key")
        
        sanitized = analyzer._sanitize_description(uppercase_desc)
        
        # Should be all lowercase
        assert sanitized == sanitized.lower()
