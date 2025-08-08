"""Tests for code parsers."""

import pytest
from cursor_pro.parsers.factory import ParserFactory
from cursor_pro.parsers.python_parser import PythonParser
from cursor_pro.parsers.base import Symbol, Dependency, CodeIssue


class TestParserFactory:
    """Test cases for ParserFactory."""
    
    def test_create_python_parser(self):
        """Test creating Python parser."""
        parser = ParserFactory.create_parser("python")
        assert isinstance(parser, PythonParser)
        assert parser.language == "python"
    
    def test_create_parser_with_extension(self):
        """Test creating parser with file extension."""
        parser = ParserFactory.create_parser(".py")
        assert isinstance(parser, PythonParser)
    
    def test_create_unsupported_parser(self):
        """Test creating parser for unsupported language."""
        parser = ParserFactory.create_parser("unsupported")
        assert parser is None
    
    def test_supported_languages(self):
        """Test getting supported languages."""
        languages = ParserFactory.supported_languages()
        assert "python" in languages
        assert "py" in languages
    
    def test_is_supported(self):
        """Test checking if language is supported."""
        assert ParserFactory.is_supported("python")
        assert ParserFactory.is_supported(".py")
        assert not ParserFactory.is_supported("unsupported")
    
    def test_register_parser(self):
        """Test registering new parser."""
        class TestParser:
            def __init__(self):
                self.language = "test"
        
        ParserFactory.register_parser("test", TestParser)
        
        parser = ParserFactory.create_parser("test")
        assert isinstance(parser, TestParser)
        assert parser.language == "test"


class TestPythonParser:
    """Test cases for PythonParser."""
    
    @pytest.fixture
    def parser(self):
        """Create Python parser instance."""
        return PythonParser()
    
    def test_parser_initialization(self, parser):
        """Test parser initialization."""
        assert parser.language == "python"
    
    def test_parse_simple_code(self, parser):
        """Test parsing simple Python code."""
        code = """
def hello_world():
    '''A simple function.'''
    print("Hello, World!")

class TestClass:
    def method(self):
        pass
"""
        result = parser.parse(code)
        
        assert len(result.symbols) >= 3  # function, class, method
        assert len(result.dependencies) == 0
        assert result.language == "python"
        assert isinstance(result.metrics, dict)
    
    def test_get_symbols(self, parser):
        """Test symbol extraction."""
        code = """
async def async_function(param1, param2: int) -> str:
    return "result"

class MyClass(BaseClass):
    def __init__(self):
        self.value = 42
"""
        symbols = parser.get_symbols(code)
        
        function_symbols = [s for s in symbols if s.type == "function"]
        class_symbols = [s for s in symbols if s.type == "class"]
        
        assert len(function_symbols) >= 1
        assert len(class_symbols) >= 1
        
        async_func = next((s for s in function_symbols if s.name == "async_function"), None)
        assert async_func is not None
        assert async_func.is_async is True
        assert "param1" in async_func.parameters
        assert "param2" in async_func.parameters
    
    def test_get_dependencies(self, parser):
        """Test dependency extraction."""
        code = """
import os
import sys as system
from pathlib import Path
from typing import List, Dict, Optional
from .local_module import LocalClass
"""
        dependencies = parser.get_dependencies(code)
        
        import_deps = [d for d in dependencies if d.type == "import"]
        from_deps = [d for d in dependencies if d.type == "from_import"]
        
        assert len(import_deps) >= 2
        assert len(from_deps) >= 3
        
        # Check specific imports
        os_import = next((d for d in import_deps if d.name == "os"), None)
        assert os_import is not None
        
        sys_import = next((d for d in import_deps if d.name == "sys"), None)
        assert sys_import is not None
        assert sys_import.alias == "system"
        
        path_import = next((d for d in from_deps if d.name == "Path"), None)
        assert path_import is not None
        assert path_import.source == "pathlib"
    
    def test_get_issues(self, parser):
        """Test issue detection."""
        code = """
def bad_function():
	# Tab indentation (should be spaces)
	x = 1; y = 2  # Multiple statements on one line
	# This line is way too long and exceeds the recommended line length limit which should be around 80-120 characters depending on the style guide
	print("Hello")  
"""  # Trailing whitespace
        
        issues = parser.get_issues(code)
        
        issue_types = [issue.rule for issue in issues]
        assert "pep8-indentation" in issue_types
        assert "pep8-multiple-statements" in issue_types
        assert "line-length" in issue_types
        assert "trailing-whitespace" in issue_types
    
    def test_validate_syntax_valid(self, parser):
        """Test syntax validation with valid code."""
        code = """
def valid_function():
    return 42
"""
        issues = parser.validate_syntax(code)
        assert len(issues) == 0
    
    def test_validate_syntax_invalid(self, parser):
        """Test syntax validation with invalid code."""
        code = """
def invalid_function(:
    return 42
"""
        issues = parser.validate_syntax(code)
        assert len(issues) > 0
        assert issues[0].type == "error"
        assert "syntax-error" in issues[0].rule
    
    def test_get_complexity_metrics(self, parser):
        """Test complexity metrics calculation."""
        code = """
def complex_function(x):
    if x > 0:
        for i in range(x):
            if i % 2 == 0:
                try:
                    result = 1 / i
                except ZeroDivisionError:
                    result = 0
                while result < 10:
                    result += 1
    return result
"""
        metrics = parser.get_complexity_metrics(code)
        
        assert "cyclomatic_complexity" in metrics
        assert "function_count" in metrics
        assert "class_count" in metrics
        assert metrics["cyclomatic_complexity"] > 1
        assert metrics["function_count"] >= 1
    
    def test_regex_fallback(self, parser):
        """Test regex-based parsing fallback for invalid syntax."""
        # Invalid syntax that can't be parsed by AST
        code = """
def function_with_syntax_error(:
    print("This has syntax errors")

class MyClass:
    def method(self):
        pass
"""
        # Should still extract some symbols using regex
        symbols = parser._get_symbols_regex(code)
        
        # Should find the class even with function syntax error
        class_symbols = [s for s in symbols if s.type == "class"]
        assert len(class_symbols) >= 1
        assert class_symbols[0].name == "MyClass"
    
    def test_comment_prefix(self, parser):
        """Test comment prefix detection."""
        assert parser.get_comment_prefix() == "#"
    
    def test_parse_with_docstrings(self, parser):
        """Test parsing code with docstrings."""
        code = '''
def documented_function():
    """
    This is a docstring.
    
    Returns:
        str: A greeting message.
    """
    return "Hello"

class DocumentedClass:
    """A class with documentation."""
    
    def method(self):
        """A method with documentation."""
        pass
'''
        result = parser.parse(code)
        
        # Check that docstrings are captured
        function_symbols = [s for s in result.symbols if s.type == "function"]
        class_symbols = [s for s in result.symbols if s.type == "class"]
        
        documented_func = next((s for s in function_symbols if s.name == "documented_function"), None)
        assert documented_func is not None
        assert documented_func.docstring is not None
        assert "This is a docstring" in documented_func.docstring
        
        documented_class = next((s for s in class_symbols if s.name == "DocumentedClass"), None)
        assert documented_class is not None
        assert documented_class.docstring is not None


class TestBaseParser:
    """Test cases for BaseParser functionality."""
    
    def test_get_metrics(self):
        """Test basic metrics calculation."""
        # Using PythonParser as concrete implementation
        parser = PythonParser()
        
        code = """
# This is a comment
def hello():
    print("Hello, World!")
    
    # Another comment
    return "done"

# Final comment
"""
        metrics = parser.get_metrics(code)
        
        assert "total_lines" in metrics
        assert "code_lines" in metrics
        assert "blank_lines" in metrics
        assert "comment_lines" in metrics
        assert "total_characters" in metrics
        assert "average_line_length" in metrics
        assert "code_to_comment_ratio" in metrics
        
        assert metrics["total_lines"] > 0
        assert metrics["code_lines"] > 0
        assert metrics["comment_lines"] > 0
    
    def test_find_symbol_at_position(self):
        """Test finding symbol at specific position."""
        parser = PythonParser()
        
        code = """
def function1():
    pass

def function2():
    pass
"""
        symbol = parser.find_symbol_at_position(code, 2, 5)  # Line 2, somewhere in function1
        assert symbol is not None
        assert symbol.name == "function1"
    
    def test_get_symbol_references(self):
        """Test finding symbol references."""
        parser = PythonParser()
        
        code = """
def calculate():
    value = 42
    return value

result = calculate()
print(calculate())
"""
        references = parser.get_symbol_references(code, "calculate")
        
        # Should find at least the definition and two calls
        assert len(references) >= 3
    
    def test_suggest_refactoring(self):
        """Test refactoring suggestions."""
        parser = PythonParser()
        
        # Create code with long function
        long_function_lines = ["def very_long_function():"] + ["    print('line')" for _ in range(60)]
        code = "\n".join(long_function_lines)
        
        suggestions = parser.suggest_refactoring(code)
        
        assert len(suggestions) > 0
        assert any("very long" in suggestion.lower() for suggestion in suggestions)


@pytest.mark.parametrize("code,expected_symbols", [
    ("def test(): pass", 1),
    ("class Test: pass", 1),
    ("def func1(): pass\ndef func2(): pass", 2),
    ("", 0),
])
def test_symbol_extraction_parametrized(code, expected_symbols):
    """Test symbol extraction with various code samples."""
    parser = PythonParser()
    symbols = parser.get_symbols(code)
    assert len(symbols) == expected_symbols


@pytest.mark.parametrize("code,expected_deps", [
    ("import os", 1),
    ("from sys import path", 1),
    ("import os\nimport sys", 2),
    ("", 0),
])
def test_dependency_extraction_parametrized(code, expected_deps):
    """Test dependency extraction with various code samples."""
    parser = PythonParser()
    dependencies = parser.get_dependencies(code)
    assert len(dependencies) == expected_deps