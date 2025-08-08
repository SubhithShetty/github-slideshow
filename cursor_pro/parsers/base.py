"""Base parser class for code analysis."""

from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class Symbol:
    """Represents a code symbol (variable, function, class, etc.)."""
    name: str
    type: str  # function, class, variable, module, etc.
    line: int
    column: int
    end_line: Optional[int] = None
    end_column: Optional[int] = None
    scope: Optional[str] = None
    docstring: Optional[str] = None
    parameters: Optional[List[str]] = None
    return_type: Optional[str] = None
    visibility: Optional[str] = None  # public, private, protected
    is_static: bool = False
    is_async: bool = False


@dataclass
class Dependency:
    """Represents a code dependency (import, include, etc.)."""
    name: str
    type: str  # import, from_import, include, require, etc.
    source: Optional[str] = None  # module/file being imported from
    alias: Optional[str] = None
    line: int = 0
    is_relative: bool = False


@dataclass
class CodeIssue:
    """Represents a code issue (error, warning, suggestion)."""
    type: str  # error, warning, suggestion
    message: str
    line: int
    column: int
    severity: str = "medium"  # low, medium, high, critical
    rule: Optional[str] = None
    fix_suggestion: Optional[str] = None


@dataclass
class ParseResult:
    """Result of parsing a code file."""
    symbols: List[Symbol]
    dependencies: List[Dependency]
    issues: List[CodeIssue]
    metrics: Dict[str, Any]
    syntax_tree: Optional[Any] = None
    language: str = ""
    file_path: str = ""


class BaseParser(ABC):
    """
    Abstract base class for language-specific code parsers.
    
    Each parser should implement methods to:
    - Parse code into symbols and dependencies
    - Analyze code quality and issues
    - Extract metrics and statistics
    - Provide language-specific insights
    """
    
    def __init__(self, language: str):
        """Initialize the parser."""
        self.language = language
        self.logger = logging.getLogger(f"{__name__}.{language}")
    
    @abstractmethod
    def parse(self, code: str, file_path: str = "") -> ParseResult:
        """
        Parse code and extract symbols, dependencies, and issues.
        
        Args:
            code: Source code to parse
            file_path: Path to the source file
            
        Returns:
            ParseResult with extracted information
        """
        pass
    
    @abstractmethod
    def get_symbols(self, code: str) -> List[Symbol]:
        """Extract symbols (functions, classes, variables) from code."""
        pass
    
    @abstractmethod
    def get_dependencies(self, code: str) -> List[Dependency]:
        """Extract dependencies (imports, requires) from code."""
        pass
    
    def get_issues(self, code: str) -> List[CodeIssue]:
        """
        Analyze code for issues. Base implementation provides common checks.
        
        Args:
            code: Source code to analyze
            
        Returns:
            List of found issues
        """
        issues = []
        
        # Basic checks that apply to most languages
        lines = code.split('\n')
        
        for i, line in enumerate(lines):
            line_num = i + 1
            
            # Long line check
            if len(line) > 120:
                issues.append(CodeIssue(
                    type="warning",
                    message="Line too long (>120 characters)",
                    line=line_num,
                    column=120,
                    severity="low",
                    rule="line-length"
                ))
            
            # Trailing whitespace
            if line.endswith(' ') or line.endswith('\t'):
                issues.append(CodeIssue(
                    type="warning",
                    message="Trailing whitespace",
                    line=line_num,
                    column=len(line.rstrip()),
                    severity="low",
                    rule="trailing-whitespace"
                ))
            
            # TODO comments
            if 'TODO' in line or 'FIXME' in line or 'HACK' in line:
                issues.append(CodeIssue(
                    type="suggestion",
                    message="TODO/FIXME comment found",
                    line=line_num,
                    column=line.find('TODO') if 'TODO' in line else line.find('FIXME'),
                    severity="low",
                    rule="todo-comment"
                ))
        
        return issues
    
    def get_metrics(self, code: str) -> Dict[str, Any]:
        """
        Calculate code metrics.
        
        Args:
            code: Source code to analyze
            
        Returns:
            Dictionary of metrics
        """
        lines = code.split('\n')
        
        # Basic metrics
        total_lines = len(lines)
        code_lines = len([line for line in lines if line.strip() and not line.strip().startswith(self.get_comment_prefix())])
        blank_lines = len([line for line in lines if not line.strip()])
        comment_lines = total_lines - code_lines - blank_lines
        
        # Character count
        total_chars = len(code)
        
        # Average line length
        avg_line_length = sum(len(line) for line in lines) / total_lines if total_lines > 0 else 0
        
        return {
            "total_lines": total_lines,
            "code_lines": code_lines,
            "blank_lines": blank_lines,
            "comment_lines": comment_lines,
            "total_characters": total_chars,
            "average_line_length": round(avg_line_length, 2),
            "code_to_comment_ratio": round(code_lines / max(comment_lines, 1), 2)
        }
    
    def get_complexity_metrics(self, code: str) -> Dict[str, Any]:
        """
        Calculate complexity metrics. Base implementation provides basic metrics.
        
        Args:
            code: Source code to analyze
            
        Returns:
            Dictionary of complexity metrics
        """
        # Count nesting levels, control structures, etc.
        lines = code.split('\n')
        
        # Basic complexity indicators
        control_structures = 0
        max_nesting = 0
        current_nesting = 0
        
        for line in lines:
            stripped = line.strip()
            
            # Count control structures (language-agnostic patterns)
            control_keywords = ['if', 'else', 'for', 'while', 'switch', 'case', 'try', 'catch']
            for keyword in control_keywords:
                if stripped.startswith(keyword + ' ') or stripped.startswith(keyword + '('):
                    control_structures += 1
            
            # Estimate nesting level by indentation
            indent_level = len(line) - len(line.lstrip())
            current_nesting = indent_level // 4  # Assume 4-space indentation
            max_nesting = max(max_nesting, current_nesting)
        
        return {
            "control_structures": control_structures,
            "max_nesting_level": max_nesting,
            "estimated_complexity": control_structures + max_nesting
        }
    
    @abstractmethod
    def get_comment_prefix(self) -> str:
        """Return the comment prefix for this language."""
        pass
    
    def find_symbol_at_position(self, code: str, line: int, column: int) -> Optional[Symbol]:
        """
        Find the symbol at a specific position in the code.
        
        Args:
            code: Source code
            line: Line number (1-indexed)
            column: Column number (0-indexed)
            
        Returns:
            Symbol at the position, if any
        """
        symbols = self.get_symbols(code)
        
        for symbol in symbols:
            if symbol.line == line:
                # Simple check if column is within reasonable range
                # More sophisticated parsers can override this
                return symbol
        
        return None
    
    def get_symbol_references(self, code: str, symbol_name: str) -> List[int]:
        """
        Find all references to a symbol in the code.
        
        Args:
            code: Source code
            symbol_name: Name of the symbol to find
            
        Returns:
            List of line numbers where the symbol is referenced
        """
        references = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines):
            if symbol_name in line:
                # Basic word boundary check
                import re
                if re.search(r'\b' + re.escape(symbol_name) + r'\b', line):
                    references.append(i + 1)
        
        return references
    
    def suggest_refactoring(self, code: str) -> List[str]:
        """
        Suggest potential refactoring opportunities.
        
        Args:
            code: Source code to analyze
            
        Returns:
            List of refactoring suggestions
        """
        suggestions = []
        symbols = self.get_symbols(code)
        metrics = self.get_complexity_metrics(code)
        
        # Long function detection
        functions = [s for s in symbols if s.type == 'function']
        for func in functions:
            if func.end_line and (func.end_line - func.line) > 50:
                suggestions.append(f"Function '{func.name}' is very long ({func.end_line - func.line} lines). Consider breaking it into smaller functions.")
        
        # High complexity warning
        if metrics.get('estimated_complexity', 0) > 20:
            suggestions.append("Code has high complexity. Consider simplifying control flow and reducing nesting.")
        
        # Too many functions in one file
        if len(functions) > 20:
            suggestions.append(f"File contains many functions ({len(functions)}). Consider splitting into multiple modules.")
        
        return suggestions
    
    def validate_syntax(self, code: str) -> List[CodeIssue]:
        """
        Validate syntax of the code. Base implementation is minimal.
        
        Args:
            code: Source code to validate
            
        Returns:
            List of syntax issues
        """
        issues = []
        
        # Basic bracket matching
        brackets = {'(': ')', '[': ']', '{': '}'}
        stack = []
        lines = code.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            for col_num, char in enumerate(line):
                if char in brackets:
                    stack.append((char, line_num, col_num))
                elif char in brackets.values():
                    if not stack:
                        issues.append(CodeIssue(
                            type="error",
                            message=f"Unmatched closing bracket '{char}'",
                            line=line_num,
                            column=col_num,
                            severity="high",
                            rule="bracket-matching"
                        ))
                    else:
                        open_char, _, _ = stack.pop()
                        if brackets.get(open_char) != char:
                            issues.append(CodeIssue(
                                type="error",
                                message=f"Mismatched brackets: '{open_char}' and '{char}'",
                                line=line_num,
                                column=col_num,
                                severity="high",
                                rule="bracket-matching"
                            ))
        
        # Check for unmatched opening brackets
        for open_char, line_num, col_num in stack:
            issues.append(CodeIssue(
                type="error",
                message=f"Unmatched opening bracket '{open_char}'",
                line=line_num,
                column=col_num,
                severity="high",
                rule="bracket-matching"
            ))
        
        return issues