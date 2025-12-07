"""AI Analyzer component for screenshot categorization."""

import json
import re
import time
from dataclasses import dataclass, field

import google.generativeai as genai


@dataclass
class AnalysisResult:
    """Result of AI content analysis."""
    category: str  # 'Errors', 'Code', 'Memes', 'UI', 'Docs', 'Other'
    description: str  # max 50 chars, sanitized
    tags: list[str] = field(default_factory=list)  # max 5 tags
    confidence: float = 0.0  # 0-1
    raw_response: str = ""


class AIAnalyzer:
    """Categorize screenshot content using Gemini AI."""
    
    CATEGORIES: list[str] = ['Errors', 'Code', 'Memes', 'UI', 'Docs', 'Other']
    MIN_OCR_CONFIDENCE: float = 30.0
    MIN_TEXT_LENGTH: int = 5
    MAX_DESCRIPTION_LENGTH: int = 50
    
    # Keyword patterns for fallback categorization
    FALLBACK_KEYWORDS: dict[str, list[str]] = {
        'Errors': ['error', 'exception', 'traceback', 'failed', 'failure', 'crash', 'bug', 'warning'],
        'Code': ['def ', 'function', 'class ', 'import ', 'const ', 'var ', 'let ', 'return', '{}', '[]', '=>'],
        'Memes': ['lol', 'lmao', 'meme', 'funny', 'joke', 'haha'],
        'UI': ['button', 'click', 'menu', 'dialog', 'window', 'settings', 'preferences'],
        'Docs': ['documentation', 'readme', 'guide', 'tutorial', 'manual', 'instructions'],
    }
    
    PROMPT_TEMPLATE = """Analyze this screenshot text and categorize it.

Text from screenshot:
{text}

Respond with JSON only:
{{
    "category": "one of: Errors, Code, Memes, UI, Docs, Other",
    "description": "brief description under 50 chars",
    "tags": ["tag1", "tag2", "tag3"],
    "confidence": 0.0 to 1.0
}}"""
    
    def __init__(self, api_key: str, model: str = 'gemini-1.5-flash') -> None:
        """Initialize AI analyzer.
        
        Args:
            api_key: Gemini API key.
            model: Model name to use.
        """
        genai.configure(api_key=api_key)
        self._model = genai.GenerativeModel(model)
        self._last_request_time: float = 0.0
        self._min_interval: float = 4.0  # 4 seconds = 15 requests/minute
    
    def analyze(self, ocr_text: str, ocr_confidence: float) -> AnalysisResult:
        """Analyze OCR text and return categorization.
        
        Args:
            ocr_text: Text extracted from screenshot.
            ocr_confidence: Confidence score from OCR (0-100).
            
        Returns:
            AnalysisResult with category and metadata.
        """
        # Check if we should use AI or fallback
        if ocr_confidence < self.MIN_OCR_CONFIDENCE or len(ocr_text.strip()) < self.MIN_TEXT_LENGTH:
            return self._fallback_analysis(ocr_text)
        
        try:
            self._enforce_rate_limit()
            
            prompt = self.PROMPT_TEMPLATE.format(text=ocr_text[:1000])  # Limit text length
            response = self._model.generate_content(prompt)
            
            return self._parse_response(response.text)
            
        except Exception:
            # Fall back to rule-based on any error
            return self._fallback_analysis(ocr_text)
    
    def _parse_response(self, response_text: str) -> AnalysisResult:
        """Parse JSON response from Gemini.
        
        Args:
            response_text: Raw response text from API.
            
        Returns:
            AnalysisResult parsed from response.
        """
        try:
            # Extract JSON from response (may have markdown code blocks)
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if not json_match:
                raise ValueError("No JSON found in response")
            
            data = json.loads(json_match.group())
            
            category = data.get('category', 'Other')
            if category not in self.CATEGORIES:
                category = 'Other'
            
            description = self._sanitize_description(data.get('description', ''))
            tags = data.get('tags', [])[:5]  # Max 5 tags
            confidence = float(data.get('confidence', 0.5))
            confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]
            
            return AnalysisResult(
                category=category,
                description=description,
                tags=tags,
                confidence=confidence,
                raw_response=response_text
            )
            
        except (json.JSONDecodeError, ValueError, KeyError):
            return AnalysisResult(
                category='Other',
                description='unknown_content',
                tags=[],
                confidence=0.0,
                raw_response=response_text
            )
    
    def _fallback_analysis(self, text: str) -> AnalysisResult:
        """Rule-based fallback categorization using keywords.
        
        Args:
            text: Text to analyze.
            
        Returns:
            AnalysisResult based on keyword matching.
        """
        text_lower = text.lower()
        
        # Check each category's keywords
        for category, keywords in self.FALLBACK_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    description = self._sanitize_description(f"{category.lower()}_content")
                    return AnalysisResult(
                        category=category,
                        description=description,
                        tags=[category.lower()],
                        confidence=0.3,
                        raw_response=""
                    )
        
        # Default to Other
        return AnalysisResult(
            category='Other',
            description='unknown_content',
            tags=[],
            confidence=0.1,
            raw_response=""
        )
    
    def _sanitize_description(self, desc: str) -> str:
        """Sanitize description to allowed characters only.
        
        Args:
            desc: Raw description string.
            
        Returns:
            Sanitized description with only lowercase letters, numbers, underscores.
        """
        # Convert to lowercase
        desc = desc.lower()
        
        # Replace spaces with underscores
        desc = desc.replace(' ', '_')
        
        # Keep only allowed characters
        desc = re.sub(r'[^a-z0-9_]', '', desc)
        
        # Remove consecutive underscores
        desc = re.sub(r'_+', '_', desc)
        
        # Strip leading/trailing underscores
        desc = desc.strip('_')
        
        # Truncate to max length
        if len(desc) > self.MAX_DESCRIPTION_LENGTH:
            desc = desc[:self.MAX_DESCRIPTION_LENGTH]
        
        # Ensure non-empty
        if not desc:
            desc = 'screenshot'
        
        return desc
    
    def _enforce_rate_limit(self) -> None:
        """Enforce minimum interval between API requests."""
        now = time.time()
        elapsed = now - self._last_request_time
        
        if elapsed < self._min_interval:
            time.sleep(self._min_interval - elapsed)
        
        self._last_request_time = time.time()
