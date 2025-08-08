"""
Cursor Pro Model - An AI-powered coding assistant

This package provides a comprehensive AI coding assistant with capabilities including:
- Code understanding and analysis
- Intelligent code generation and editing
- Context-aware suggestions
- Multi-language support
- Real-time collaboration features
"""

__version__ = "0.1.0"
__author__ = "Cursor Pro Team"
__email__ = "dev@cursorpro.ai"

from .core.model import CursorProModel
from .core.config import Config
from .api.server import create_app

__all__ = ["CursorProModel", "Config", "create_app"]