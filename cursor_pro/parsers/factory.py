"""Parser factory for creating language-specific parsers."""

from typing import Optional
from .base import BaseParser
from .python_parser import PythonParser


class ParserFactory:
    """Factory for creating language-specific parsers."""
    
    _parsers = {
        "python": PythonParser,
        "py": PythonParser,
    }
    
    @classmethod
    def create_parser(cls, language: str) -> Optional[BaseParser]:
        """
        Create a parser for the specified language.
        
        Args:
            language: Programming language name or file extension
            
        Returns:
            Parser instance or None if language is not supported
        """
        language = language.lower().strip()
        
        # Remove leading dot from file extensions
        if language.startswith('.'):
            language = language[1:]
        
        parser_class = cls._parsers.get(language)
        if parser_class:
            return parser_class()
        
        return None
    
    @classmethod
    def register_parser(cls, language: str, parser_class: type):
        """
        Register a new parser for a language.
        
        Args:
            language: Language name or extension
            parser_class: Parser class to register
        """
        cls._parsers[language.lower()] = parser_class
    
    @classmethod
    def supported_languages(cls) -> list:
        """Get list of supported languages."""
        return list(cls._parsers.keys())
    
    @classmethod
    def is_supported(cls, language: str) -> bool:
        """Check if a language is supported."""
        language = language.lower().strip()
        if language.startswith('.'):
            language = language[1:]
        return language in cls._parsers