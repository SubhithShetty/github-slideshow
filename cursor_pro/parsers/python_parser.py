"""Python code parser implementation."""

import ast
import re
from typing import Dict, List, Optional, Any
from .base import BaseParser, Symbol, Dependency, CodeIssue, ParseResult


class PythonParser(BaseParser):
    """Python-specific code parser using AST."""
    
    def __init__(self):
        """Initialize the Python parser."""
        super().__init__("python")
    
    def parse(self, code: str, file_path: str = "") -> ParseResult:
        """
        Parse Python code and extract comprehensive information.
        
        Args:
            code: Python source code
            file_path: Path to the source file
            
        Returns:
            ParseResult with extracted information
        """
        try:
            # Parse into AST
            tree = ast.parse(code)
            
            # Extract information
            symbols = self.get_symbols(code)
            dependencies = self.get_dependencies(code)
            issues = self.get_issues(code)
            issues.extend(self.validate_syntax(code))
            metrics = self.get_metrics(code)
            metrics.update(self.get_complexity_metrics(code))
            
            return ParseResult(
                symbols=symbols,
                dependencies=dependencies,
                issues=issues,
                metrics=metrics,
                syntax_tree=tree,
                language=self.language,
                file_path=file_path
            )
            
        except SyntaxError as e:
            return ParseResult(
                symbols=[],
                dependencies=[],
                issues=[CodeIssue(
                    type="error",
                    message=f"Syntax error: {e.msg}",
                    line=e.lineno or 1,
                    column=e.offset or 0,
                    severity="critical",
                    rule="syntax-error"
                )],
                metrics=self.get_metrics(code),
                language=self.language,
                file_path=file_path
            )
    
    def get_symbols(self, code: str) -> List[Symbol]:
        """Extract Python symbols using AST."""
        symbols = []
        
        try:
            tree = ast.parse(code)
            visitor = PythonSymbolVisitor()
            visitor.visit(tree)
            symbols = visitor.symbols
        except SyntaxError:
            # Fallback to regex-based parsing
            symbols = self._get_symbols_regex(code)
        
        return symbols
    
    def _get_symbols_regex(self, code: str) -> List[Symbol]:
        """Fallback regex-based symbol extraction."""
        symbols = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines):
            line_num = i + 1
            
            # Function definitions
            func_match = re.match(r'^\s*(async\s+)?def\s+(\w+)\s*\((.*?)\)\s*(->\s*[^:]+)?\s*:', line)
            if func_match:
                is_async = func_match.group(1) is not None
                func_name = func_match.group(2)
                params = func_match.group(3)
                return_type = func_match.group(4)
                
                # Extract parameter names
                param_list = []
                if params:
                    param_list = [p.strip().split('=')[0].split(':')[0].strip() 
                                 for p in params.split(',') if p.strip()]
                
                symbols.append(Symbol(
                    name=func_name,
                    type="function",
                    line=line_num,
                    column=line.find('def'),
                    parameters=param_list,
                    return_type=return_type.strip('->').strip() if return_type else None,
                    is_async=is_async
                ))
            
            # Class definitions
            class_match = re.match(r'^\s*class\s+(\w+)(?:\s*\(([^)]*)\))?\s*:', line)
            if class_match:
                class_name = class_match.group(1)
                bases = class_match.group(2)
                
                symbols.append(Symbol(
                    name=class_name,
                    type="class",
                    line=line_num,
                    column=line.find('class'),
                    parameters=[b.strip() for b in bases.split(',')] if bases else []
                ))
            
            # Variable assignments (simple cases)
            var_match = re.match(r'^\s*(\w+)\s*=\s*', line)
            if var_match and not line.strip().startswith('#'):
                var_name = var_match.group(1)
                if var_name not in ['def', 'class', 'if', 'for', 'while']:  # Avoid keywords
                    symbols.append(Symbol(
                        name=var_name,
                        type="variable",
                        line=line_num,
                        column=line.find(var_name)
                    ))
        
        return symbols
    
    def get_dependencies(self, code: str) -> List[Dependency]:
        """Extract Python imports and dependencies."""
        dependencies = []
        
        try:
            tree = ast.parse(code)
            visitor = PythonImportVisitor()
            visitor.visit(tree)
            dependencies = visitor.dependencies
        except SyntaxError:
            # Fallback to regex-based parsing
            dependencies = self._get_dependencies_regex(code)
        
        return dependencies
    
    def _get_dependencies_regex(self, code: str) -> List[Dependency]:
        """Fallback regex-based dependency extraction."""
        dependencies = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines):
            line_num = i + 1
            stripped = line.strip()
            
            # import module
            import_match = re.match(r'import\s+([\w.]+)(?:\s+as\s+(\w+))?', stripped)
            if import_match:
                module = import_match.group(1)
                alias = import_match.group(2)
                
                dependencies.append(Dependency(
                    name=module,
                    type="import",
                    alias=alias,
                    line=line_num,
                    is_relative=module.startswith('.')
                ))
            
            # from module import item
            from_import_match = re.match(r'from\s+([\w.]+)\s+import\s+(.+)', stripped)
            if from_import_match:
                module = from_import_match.group(1)
                imports = from_import_match.group(2)
                
                # Handle multiple imports
                import_items = [item.strip() for item in imports.split(',')]
                for item in import_items:
                    # Handle "as" aliases
                    if ' as ' in item:
                        name, alias = item.split(' as ')
                        name, alias = name.strip(), alias.strip()
                    else:
                        name, alias = item.strip(), None
                    
                    dependencies.append(Dependency(
                        name=name,
                        type="from_import",
                        source=module,
                        alias=alias,
                        line=line_num,
                        is_relative=module.startswith('.')
                    ))
        
        return dependencies
    
    def get_issues(self, code: str) -> List[CodeIssue]:
        """Python-specific code issues analysis."""
        issues = super().get_issues(code)  # Get base issues
        
        lines = code.split('\n')
        
        for i, line in enumerate(lines):
            line_num = i + 1
            stripped = line.strip()
            
            # PEP 8 violations
            
            # Indentation should be 4 spaces
            if line.startswith('\t'):
                issues.append(CodeIssue(
                    type="warning",
                    message="Use 4 spaces for indentation, not tabs",
                    line=line_num,
                    column=0,
                    severity="medium",
                    rule="pep8-indentation"
                ))
            
            # Multiple statements on one line
            if ';' in stripped and not stripped.startswith('#'):
                issues.append(CodeIssue(
                    type="warning",
                    message="Multiple statements on one line",
                    line=line_num,
                    column=stripped.find(';'),
                    severity="medium",
                    rule="pep8-multiple-statements"
                ))
            
            # Blank line issues
            if i > 0:
                prev_line = lines[i-1].strip()
                
                # Two blank lines before class/function at module level
                if (stripped.startswith('def ') or stripped.startswith('class ')) and prev_line and not prev_line.startswith('@'):
                    # Check if we need blank lines
                    blank_lines_before = 0
                    j = i - 1
                    while j >= 0 and not lines[j].strip():
                        blank_lines_before += 1
                        j -= 1
                    
                    if stripped.startswith('class ') and blank_lines_before < 2:
                        issues.append(CodeIssue(
                            type="warning",
                            message="Two blank lines expected before class definition",
                            line=line_num,
                            column=0,
                            severity="low",
                            rule="pep8-blank-lines"
                        ))
            
            # Import order issues
            if stripped.startswith('import ') or stripped.startswith('from '):
                # Check for imports after non-import statements
                for j in range(i):
                    prev = lines[j].strip()
                    if (prev and not prev.startswith('#') and 
                        not prev.startswith('import ') and 
                        not prev.startswith('from ') and
                        not prev.startswith('"""') and
                        not prev.startswith("'''")):
                        issues.append(CodeIssue(
                            type="warning",
                            message="Imports should be at the top of the file",
                            line=line_num,
                            column=0,
                            severity="medium",
                            rule="pep8-import-order"
                        ))
                        break
            
            # Naming conventions
            func_match = re.match(r'^\s*def\s+(\w+)', line)
            if func_match:
                func_name = func_match.group(1)
                if not re.match(r'^[a-z_][a-z0-9_]*$', func_name):
                    issues.append(CodeIssue(
                        type="warning",
                        message=f"Function name '{func_name}' should be lowercase with underscores",
                        line=line_num,
                        column=line.find(func_name),
                        severity="low",
                        rule="pep8-naming"
                    ))
            
            class_match = re.match(r'^\s*class\s+(\w+)', line)
            if class_match:
                class_name = class_match.group(1)
                if not re.match(r'^[A-Z][a-zA-Z0-9]*$', class_name):
                    issues.append(CodeIssue(
                        type="warning",
                        message=f"Class name '{class_name}' should use CapitalizedWords",
                        line=line_num,
                        column=line.find(class_name),
                        severity="low",
                        rule="pep8-naming"
                    ))
        
        return issues
    
    def get_complexity_metrics(self, code: str) -> Dict[str, Any]:
        """Calculate Python-specific complexity metrics."""
        base_metrics = super().get_complexity_metrics(code)
        
        try:
            tree = ast.parse(code)
            visitor = PythonComplexityVisitor()
            visitor.visit(tree)
            
            base_metrics.update({
                "cyclomatic_complexity": visitor.cyclomatic_complexity,
                "function_count": visitor.function_count,
                "class_count": visitor.class_count,
                "average_function_length": visitor.average_function_length,
                "max_function_complexity": visitor.max_function_complexity
            })
        except SyntaxError:
            pass
        
        return base_metrics
    
    def get_comment_prefix(self) -> str:
        """Return Python comment prefix."""
        return "#"
    
    def validate_syntax(self, code: str) -> List[CodeIssue]:
        """Validate Python syntax using AST."""
        issues = []
        
        try:
            ast.parse(code)
        except SyntaxError as e:
            issues.append(CodeIssue(
                type="error",
                message=f"Syntax error: {e.msg}",
                line=e.lineno or 1,
                column=e.offset or 0,
                severity="critical",
                rule="syntax-error"
            ))
        except Exception as e:
            issues.append(CodeIssue(
                type="error",
                message=f"Parse error: {str(e)}",
                line=1,
                column=0,
                severity="critical",
                rule="parse-error"
            ))
        
        return issues


class PythonSymbolVisitor(ast.NodeVisitor):
    """AST visitor for extracting Python symbols."""
    
    def __init__(self):
        self.symbols = []
        self.scope_stack = []
    
    def visit_FunctionDef(self, node):
        """Visit function definition."""
        # Extract parameters
        params = []
        for arg in node.args.args:
            params.append(arg.arg)
        
        # Extract return type
        return_type = None
        if node.returns:
            if isinstance(node.returns, ast.Name):
                return_type = node.returns.id
            elif isinstance(node.returns, ast.Constant):
                return_type = str(node.returns.value)
        
        # Extract docstring
        docstring = None
        if (node.body and isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            docstring = node.body[0].value.value
        
        # Determine scope
        scope = '.'.join(self.scope_stack) if self.scope_stack else 'module'
        
        symbol = Symbol(
            name=node.name,
            type="function",
            line=node.lineno,
            column=node.col_offset,
            end_line=node.end_lineno,
            end_column=node.end_col_offset,
            scope=scope,
            docstring=docstring,
            parameters=params,
            return_type=return_type,
            is_async=False
        )
        
        self.symbols.append(symbol)
        
        # Visit children with updated scope
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()
    
    def visit_AsyncFunctionDef(self, node):
        """Visit async function definition."""
        # Similar to FunctionDef but mark as async
        params = []
        for arg in node.args.args:
            params.append(arg.arg)
        
        return_type = None
        if node.returns:
            if isinstance(node.returns, ast.Name):
                return_type = node.returns.id
        
        docstring = None
        if (node.body and isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            docstring = node.body[0].value.value
        
        scope = '.'.join(self.scope_stack) if self.scope_stack else 'module'
        
        symbol = Symbol(
            name=node.name,
            type="function",
            line=node.lineno,
            column=node.col_offset,
            end_line=node.end_lineno,
            end_column=node.end_col_offset,
            scope=scope,
            docstring=docstring,
            parameters=params,
            return_type=return_type,
            is_async=True
        )
        
        self.symbols.append(symbol)
        
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()
    
    def visit_ClassDef(self, node):
        """Visit class definition."""
        # Extract base classes
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
        
        # Extract docstring
        docstring = None
        if (node.body and isinstance(node.body[0], ast.Expr) and 
            isinstance(node.body[0].value, ast.Constant) and
            isinstance(node.body[0].value.value, str)):
            docstring = node.body[0].value.value
        
        scope = '.'.join(self.scope_stack) if self.scope_stack else 'module'
        
        symbol = Symbol(
            name=node.name,
            type="class",
            line=node.lineno,
            column=node.col_offset,
            end_line=node.end_lineno,
            end_column=node.end_col_offset,
            scope=scope,
            docstring=docstring,
            parameters=bases  # Use parameters field for base classes
        )
        
        self.symbols.append(symbol)
        
        self.scope_stack.append(node.name)
        self.generic_visit(node)
        self.scope_stack.pop()
    
    def visit_Assign(self, node):
        """Visit variable assignments."""
        for target in node.targets:
            if isinstance(target, ast.Name):
                scope = '.'.join(self.scope_stack) if self.scope_stack else 'module'
                
                symbol = Symbol(
                    name=target.id,
                    type="variable",
                    line=node.lineno,
                    column=node.col_offset,
                    scope=scope
                )
                
                self.symbols.append(symbol)
        
        self.generic_visit(node)


class PythonImportVisitor(ast.NodeVisitor):
    """AST visitor for extracting Python imports."""
    
    def __init__(self):
        self.dependencies = []
    
    def visit_Import(self, node):
        """Visit import statement."""
        for alias in node.names:
            dependency = Dependency(
                name=alias.name,
                type="import",
                alias=alias.asname,
                line=node.lineno,
                is_relative=alias.name.startswith('.')
            )
            self.dependencies.append(dependency)
    
    def visit_ImportFrom(self, node):
        """Visit from...import statement."""
        module = node.module or ''
        
        for alias in node.names:
            dependency = Dependency(
                name=alias.name,
                type="from_import",
                source=module,
                alias=alias.asname,
                line=node.lineno,
                is_relative=module.startswith('.') or node.level > 0
            )
            self.dependencies.append(dependency)


class PythonComplexityVisitor(ast.NodeVisitor):
    """AST visitor for calculating complexity metrics."""
    
    def __init__(self):
        self.cyclomatic_complexity = 1  # Base complexity
        self.function_count = 0
        self.class_count = 0
        self.function_lengths = []
        self.function_complexities = []
        self.current_function_complexity = 0
    
    def visit_FunctionDef(self, node):
        """Visit function definition."""
        self.function_count += 1
        self.function_lengths.append(node.end_lineno - node.lineno + 1 if node.end_lineno else 1)
        
        # Calculate function complexity
        old_complexity = self.current_function_complexity
        self.current_function_complexity = 1  # Base complexity for function
        
        self.generic_visit(node)
        
        self.function_complexities.append(self.current_function_complexity)
        self.current_function_complexity = old_complexity
    
    def visit_AsyncFunctionDef(self, node):
        """Visit async function definition."""
        self.visit_FunctionDef(node)
    
    def visit_ClassDef(self, node):
        """Visit class definition."""
        self.class_count += 1
        self.generic_visit(node)
    
    def visit_If(self, node):
        """Visit if statement."""
        self.cyclomatic_complexity += 1
        self.current_function_complexity += 1
        self.generic_visit(node)
    
    def visit_For(self, node):
        """Visit for loop."""
        self.cyclomatic_complexity += 1
        self.current_function_complexity += 1
        self.generic_visit(node)
    
    def visit_While(self, node):
        """Visit while loop."""
        self.cyclomatic_complexity += 1
        self.current_function_complexity += 1
        self.generic_visit(node)
    
    def visit_Try(self, node):
        """Visit try statement."""
        self.cyclomatic_complexity += 1
        self.current_function_complexity += 1
        # Add complexity for each except handler
        for handler in node.handlers:
            self.cyclomatic_complexity += 1
            self.current_function_complexity += 1
        self.generic_visit(node)
    
    @property
    def average_function_length(self):
        """Calculate average function length."""
        if not self.function_lengths:
            return 0
        return sum(self.function_lengths) / len(self.function_lengths)
    
    @property
    def max_function_complexity(self):
        """Get maximum function complexity."""
        return max(self.function_complexities) if self.function_complexities else 0