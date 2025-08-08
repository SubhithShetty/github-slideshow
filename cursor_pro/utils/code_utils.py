"""Code-specific utilities for Cursor Pro Model."""

import re
import ast
from typing import List, Dict, Tuple, Optional, Set
from pathlib import Path


class CodeUtils:
    """Utility class for code-specific operations."""
    
    @staticmethod
    def extract_imports(code: str, language: str = "python") -> List[str]:
        """
        Extract import statements from code.
        
        Args:
            code: Source code
            language: Programming language
            
        Returns:
            List of import statements
        """
        imports = []
        
        if language == "python":
            # Python imports
            for line in code.split('\n'):
                line = line.strip()
                if line.startswith('import ') or line.startswith('from '):
                    imports.append(line)
        
        elif language in ["javascript", "typescript"]:
            # JavaScript/TypeScript imports
            patterns = [
                r'import\s+.*\s+from\s+["\'][^"\']+["\']',
                r'const\s+.*\s*=\s*require\s*\(["\'][^"\']+["\']\)',
                r'import\s*\(["\'][^"\']+["\']\)'
            ]
            for pattern in patterns:
                imports.extend(re.findall(pattern, code))
        
        elif language == "java":
            # Java imports
            imports.extend(re.findall(r'import\s+[\w.]+;', code))
        
        return imports
    
    @staticmethod
    def extract_functions(code: str, language: str = "python") -> List[Dict[str, str]]:
        """
        Extract function definitions from code.
        
        Args:
            code: Source code
            language: Programming language
            
        Returns:
            List of function information dictionaries
        """
        functions = []
        
        if language == "python":
            # Python functions
            pattern = r'^\s*(async\s+)?def\s+(\w+)\s*\((.*?)\)\s*(->\s*[^:]+)?\s*:'
            for match in re.finditer(pattern, code, re.MULTILINE):
                functions.append({
                    'name': match.group(2),
                    'is_async': match.group(1) is not None,
                    'parameters': match.group(3),
                    'return_type': match.group(4),
                    'line': code[:match.start()].count('\n') + 1
                })
        
        elif language in ["javascript", "typescript"]:
            # JavaScript/TypeScript functions
            patterns = [
                r'function\s+(\w+)\s*\((.*?)\)',
                r'const\s+(\w+)\s*=\s*(?:async\s+)?\s*\((.*?)\)\s*=>',
                r'(\w+)\s*:\s*(?:async\s+)?function\s*\((.*?)\)'
            ]
            for pattern in patterns:
                for match in re.finditer(pattern, code):
                    functions.append({
                        'name': match.group(1),
                        'parameters': match.group(2),
                        'line': code[:match.start()].count('\n') + 1
                    })
        
        return functions
    
    @staticmethod
    def extract_classes(code: str, language: str = "python") -> List[Dict[str, str]]:
        """
        Extract class definitions from code.
        
        Args:
            code: Source code
            language: Programming language
            
        Returns:
            List of class information dictionaries
        """
        classes = []
        
        if language == "python":
            # Python classes
            pattern = r'^\s*class\s+(\w+)(?:\s*\(([^)]*)\))?\s*:'
            for match in re.finditer(pattern, code, re.MULTILINE):
                classes.append({
                    'name': match.group(1),
                    'base_classes': match.group(2) or '',
                    'line': code[:match.start()].count('\n') + 1
                })
        
        elif language in ["javascript", "typescript"]:
            # JavaScript/TypeScript classes
            pattern = r'class\s+(\w+)(?:\s+extends\s+(\w+))?\s*{'
            for match in re.finditer(pattern, code):
                classes.append({
                    'name': match.group(1),
                    'extends': match.group(2) or '',
                    'line': code[:match.start()].count('\n') + 1
                })
        
        elif language == "java":
            # Java classes
            pattern = r'(?:public|private|protected)?\s*(?:abstract|final)?\s*class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?\s*{'
            for match in re.finditer(pattern, code):
                classes.append({
                    'name': match.group(1),
                    'extends': match.group(2) or '',
                    'implements': match.group(3) or '',
                    'line': code[:match.start()].count('\n') + 1
                })
        
        return classes
    
    @staticmethod
    def remove_comments(code: str, language: str = "python") -> str:
        """
        Remove comments from code.
        
        Args:
            code: Source code
            language: Programming language
            
        Returns:
            Code without comments
        """
        if language == "python":
            # Remove Python comments (# and docstrings)
            lines = []
            in_docstring = False
            docstring_delimiter = None
            
            for line in code.split('\n'):
                stripped = line.strip()
                
                # Handle docstrings
                if '"""' in line or "'''" in line:
                    if not in_docstring:
                        delimiter = '"""' if '"""' in line else "'''"
                        if line.count(delimiter) == 2:
                            # Single line docstring
                            line = re.sub(r'""".*?"""', '', line)
                            line = re.sub(r"'''.*?'''", '', line)
                        else:
                            in_docstring = True
                            docstring_delimiter = delimiter
                            continue
                    else:
                        if docstring_delimiter in line:
                            in_docstring = False
                            docstring_delimiter = None
                        continue
                
                if in_docstring:
                    continue
                
                # Remove inline comments
                if '#' in line:
                    # Simple approach - doesn't handle # in strings properly
                    comment_pos = line.find('#')
                    line = line[:comment_pos]
                
                lines.append(line)
            
            return '\n'.join(lines)
        
        elif language in ["javascript", "typescript", "java"]:
            # Remove // and /* */ comments
            # Remove single line comments
            code = re.sub(r'//.*$', '', code, flags=re.MULTILINE)
            # Remove multi-line comments
            code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
            return code
        
        return code
    
    @staticmethod
    def count_complexity(code: str, language: str = "python") -> Dict[str, int]:
        """
        Count complexity metrics for code.
        
        Args:
            code: Source code
            language: Programming language
            
        Returns:
            Dictionary of complexity metrics
        """
        metrics = {
            'cyclomatic_complexity': 1,  # Base complexity
            'nesting_depth': 0,
            'decision_points': 0
        }
        
        # Count decision points and nesting
        decision_keywords = {
            'python': ['if', 'elif', 'for', 'while', 'try', 'except', 'and', 'or'],
            'javascript': ['if', 'else if', 'for', 'while', 'switch', 'case', 'try', 'catch', '&&', '||'],
            'java': ['if', 'else if', 'for', 'while', 'switch', 'case', 'try', 'catch', '&&', '||']
        }
        
        keywords = decision_keywords.get(language, decision_keywords['python'])
        
        current_depth = 0
        max_depth = 0
        
        for line in code.split('\n'):
            stripped = line.strip()
            
            # Count indentation for nesting depth
            if language == "python":
                indent = len(line) - len(line.lstrip())
                current_depth = indent // 4  # Assume 4-space indentation
            else:
                # For brace-based languages, count braces
                current_depth += line.count('{') - line.count('}')
            
            max_depth = max(max_depth, current_depth)
            
            # Count decision points
            for keyword in keywords:
                if keyword in stripped:
                    metrics['decision_points'] += stripped.count(keyword)
        
        metrics['nesting_depth'] = max_depth
        metrics['cyclomatic_complexity'] += metrics['decision_points']
        
        return metrics
    
    @staticmethod
    def format_code(code: str, language: str = "python") -> str:
        """
        Basic code formatting.
        
        Args:
            code: Source code to format
            language: Programming language
            
        Returns:
            Formatted code
        """
        lines = code.split('\n')
        formatted_lines = []
        
        if language == "python":
            # Basic Python formatting
            indent_level = 0
            
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    formatted_lines.append('')
                    continue
                
                # Decrease indent for dedent keywords
                if any(stripped.startswith(kw) for kw in ['except', 'elif', 'else', 'finally']):
                    indent_level = max(0, indent_level - 1)
                elif stripped.startswith(('return', 'break', 'continue', 'pass', 'raise')):
                    # These don't change indentation but are statements
                    pass
                
                # Apply indentation
                formatted_line = '    ' * indent_level + stripped
                formatted_lines.append(formatted_line)
                
                # Increase indent for indent keywords
                if stripped.endswith(':'):
                    indent_level += 1
        
        else:
            # Basic formatting for other languages
            indent_level = 0
            
            for line in lines:
                stripped = line.strip()
                if not stripped:
                    formatted_lines.append('')
                    continue
                
                # Decrease indent for closing braces
                if stripped.startswith('}'):
                    indent_level = max(0, indent_level - 1)
                
                # Apply indentation
                formatted_line = '    ' * indent_level + stripped
                formatted_lines.append(formatted_line)
                
                # Increase indent for opening braces
                if stripped.endswith('{'):
                    indent_level += 1
        
        return '\n'.join(formatted_lines)
    
    @staticmethod
    def extract_docstrings(code: str, language: str = "python") -> List[Dict[str, str]]:
        """
        Extract docstrings from code.
        
        Args:
            code: Source code
            language: Programming language
            
        Returns:
            List of docstring information
        """
        docstrings = []
        
        if language == "python":
            try:
                tree = ast.parse(code)
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
                        if (node.body and isinstance(node.body[0], ast.Expr) and
                            isinstance(node.body[0].value, ast.Constant) and
                            isinstance(node.body[0].value.value, str)):
                            
                            docstrings.append({
                                'type': 'function' if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else 'class',
                                'name': node.name,
                                'docstring': node.body[0].value.value,
                                'line': node.lineno
                            })
            except SyntaxError:
                # Fallback to regex if AST parsing fails
                pattern = r'(def|class)\s+(\w+).*?:\s*"""(.*?)"""'
                for match in re.finditer(pattern, code, re.DOTALL):
                    docstrings.append({
                        'type': 'function' if match.group(1) == 'def' else 'class',
                        'name': match.group(2),
                        'docstring': match.group(3).strip(),
                        'line': code[:match.start()].count('\n') + 1
                    })
        
        return docstrings
    
    @staticmethod
    def validate_syntax(code: str, language: str = "python") -> List[Dict[str, str]]:
        """
        Validate syntax of code.
        
        Args:
            code: Source code
            language: Programming language
            
        Returns:
            List of syntax errors
        """
        errors = []
        
        if language == "python":
            try:
                ast.parse(code)
            except SyntaxError as e:
                errors.append({
                    'line': e.lineno or 1,
                    'column': e.offset or 1,
                    'message': e.msg or 'Syntax error',
                    'type': 'SyntaxError'
                })
        
        # For other languages, basic bracket matching
        elif language in ["javascript", "typescript", "java"]:
            brackets = {'(': ')', '[': ']', '{': '}'}
            stack = []
            
            lines = code.split('\n')
            for line_num, line in enumerate(lines, 1):
                for col_num, char in enumerate(line, 1):
                    if char in brackets:
                        stack.append((char, line_num, col_num))
                    elif char in brackets.values():
                        if not stack:
                            errors.append({
                                'line': line_num,
                                'column': col_num,
                                'message': f'Unmatched closing bracket: {char}',
                                'type': 'BracketError'
                            })
                        else:
                            open_char, _, _ = stack.pop()
                            if brackets.get(open_char) != char:
                                errors.append({
                                    'line': line_num,
                                    'column': col_num,
                                    'message': f'Mismatched brackets: {open_char} and {char}',
                                    'type': 'BracketError'
                                })
            
            # Check for unmatched opening brackets
            for open_char, line_num, col_num in stack:
                errors.append({
                    'line': line_num,
                    'column': col_num,
                    'message': f'Unmatched opening bracket: {open_char}',
                    'type': 'BracketError'
                })
        
        return errors
    
    @staticmethod
    def get_variable_names(code: str, language: str = "python") -> Set[str]:
        """
        Extract variable names from code.
        
        Args:
            code: Source code
            language: Programming language
            
        Returns:
            Set of variable names
        """
        variables = set()
        
        if language == "python":
            # Simple regex-based extraction
            # Assignment patterns
            assignments = re.findall(r'^\s*(\w+)\s*=', code, re.MULTILINE)
            variables.update(assignments)
            
            # For loop variables
            for_vars = re.findall(r'for\s+(\w+)\s+in', code)
            variables.update(for_vars)
        
        elif language in ["javascript", "typescript"]:
            # Variable declarations
            declarations = re.findall(r'(?:var|let|const)\s+(\w+)', code)
            variables.update(declarations)
            
            # Assignment patterns
            assignments = re.findall(r'^\s*(\w+)\s*=', code, re.MULTILINE)
            variables.update(assignments)
        
        return variables
    
    @staticmethod
    def estimate_execution_time(code: str, language: str = "python") -> str:
        """
        Estimate execution time category for code.
        
        Args:
            code: Source code
            language: Programming language
            
        Returns:
            Time category (fast, medium, slow)
        """
        # Simple heuristic based on code patterns
        complexity_indicators = {
            'nested_loops': len(re.findall(r'for.*for', code, re.DOTALL)),
            'while_loops': len(re.findall(r'while', code)),
            'recursive_calls': len(re.findall(r'(\w+)\s*\(.*\1', code)),
            'file_operations': len(re.findall(r'open\s*\(|read\s*\(|write\s*\(', code)),
            'network_calls': len(re.findall(r'requests\.|urllib\.|fetch\(|axios\.', code))
        }
        
        score = sum(complexity_indicators.values())
        
        if score == 0:
            return "fast"
        elif score <= 3:
            return "medium"
        else:
            return "slow"