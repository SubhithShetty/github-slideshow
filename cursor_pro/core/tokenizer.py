"""Code tokenization utilities for Cursor Pro Model."""

import logging
import re
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass
from .config import Config

logger = logging.getLogger(__name__)


@dataclass
class TokenInfo:
    """Information about a token."""
    text: str
    type: str  # identifier, keyword, string, number, operator, etc.
    start_pos: int
    end_pos: int
    line: int
    column: int


@dataclass
class CodeStructure:
    """Structured representation of code."""
    tokens: List[TokenInfo]
    functions: List[Dict]
    classes: List[Dict]
    imports: List[Dict]
    comments: List[Dict]
    strings: List[Dict]


class CodeTokenizer:
    """
    Specialized tokenizer for code understanding and analysis.
    
    This class provides:
    - Language-aware tokenization
    - Code structure extraction
    - Syntax highlighting support
    - Context-aware parsing
    """
    
    def __init__(self, config: Config):
        """Initialize the code tokenizer."""
        self.config = config
        self.supported_languages = config.code_analysis.supported_languages
        
        # Language-specific patterns
        self._patterns = self._init_patterns()
        
        logger.info(f"Initialized CodeTokenizer for languages: {self.supported_languages}")
    
    def _init_patterns(self) -> Dict[str, Dict[str, str]]:
        """Initialize regex patterns for different languages."""
        patterns = {
            "python": {
                "function": r'def\s+(\w+)\s*\(',
                "class": r'class\s+(\w+)(?:\s*\([^)]*\))?\s*:',
                "import": r'(?:from\s+\S+\s+)?import\s+\S+',
                "comment": r'#.*$',
                "string": r'(?:""".*?"""|\'\'\'.*?\'\'\'|".*?"|\'.*?\')',
                "keyword": r'\b(?:def|class|if|else|elif|for|while|try|except|finally|with|as|import|from|return|yield|break|continue|pass|global|nonlocal|lambda|and|or|not|in|is|True|False|None)\b',
                "identifier": r'\b[a-zA-Z_][a-zA-Z0-9_]*\b',
                "number": r'\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b',
                "operator": r'[+\-*/%=<>!&|^~]',
            },
            "javascript": {
                "function": r'(?:function\s+(\w+)|const\s+(\w+)\s*=\s*(?:async\s+)?\s*(?:\([^)]*\)\s*=>|\([^)]*\)\s*=>\s*{))',
                "class": r'class\s+(\w+)(?:\s+extends\s+\w+)?\s*{',
                "import": r'import\s+.*\s+from\s+["\'][^"\']+["\']|const\s+.*\s*=\s*require\s*\(["\'][^"\']+["\']\)',
                "comment": r'//.*$|/\*.*?\*/',
                "string": r'(?:`.*?`|".*?"|\'.*?\')',
                "keyword": r'\b(?:const|let|var|function|class|if|else|for|while|do|switch|case|default|try|catch|finally|throw|return|break|continue|import|export|from|as|async|await|new|this|super|extends|instanceof|typeof|in|of|true|false|null|undefined)\b',
                "identifier": r'\b[a-zA-Z_$][a-zA-Z0-9_$]*\b',
                "number": r'\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b',
                "operator": r'[+\-*/%=<>!&|^~]',
            },
            "typescript": {
                "function": r'(?:function\s+(\w+)|const\s+(\w+)\s*:\s*\([^)]*\)\s*=>|(\w+)\s*\([^)]*\)\s*:\s*\w+\s*{)',
                "class": r'(?:class|interface)\s+(\w+)(?:\s+extends\s+\w+)?\s*{',
                "import": r'import\s+.*\s+from\s+["\'][^"\']+["\']',
                "comment": r'//.*$|/\*.*?\*/',
                "string": r'(?:`.*?`|".*?"|\'.*?\')',
                "keyword": r'\b(?:const|let|var|function|class|interface|type|enum|namespace|if|else|for|while|do|switch|case|default|try|catch|finally|throw|return|break|continue|import|export|from|as|async|await|new|this|super|extends|implements|instanceof|typeof|in|of|true|false|null|undefined|any|string|number|boolean|void|never|unknown|object)\b',
                "identifier": r'\b[a-zA-Z_$][a-zA-Z0-9_$]*\b',
                "number": r'\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?\b',
                "operator": r'[+\-*/%=<>!&|^~]',
            },
            "java": {
                "function": r'(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\(',
                "class": r'(?:public|private|protected)?\s*(?:abstract|final)?\s*class\s+(\w+)(?:\s+extends\s+\w+)?(?:\s+implements\s+[\w,\s]+)?\s*{',
                "import": r'import\s+[\w.]+;',
                "comment": r'//.*$|/\*.*?\*/',
                "string": r'".*?"',
                "keyword": r'\b(?:public|private|protected|static|final|abstract|class|interface|enum|extends|implements|import|package|if|else|for|while|do|switch|case|default|try|catch|finally|throw|throws|return|break|continue|new|this|super|instanceof|true|false|null|void|int|long|short|byte|char|float|double|boolean|String)\b',
                "identifier": r'\b[a-zA-Z_][a-zA-Z0-9_]*\b',
                "number": r'\b\d+(?:\.\d+)?(?:[eE][+-]?\d+)?[fFdD]?\b',
                "operator": r'[+\-*/%=<>!&|^~]',
            }
        }
        
        # Add more languages as needed
        patterns["cpp"] = patterns["java"]  # Similar patterns
        patterns["rust"] = patterns["java"]  # Similar patterns
        patterns["go"] = patterns["java"]    # Similar patterns
        
        return patterns
    
    def tokenize(self, code: str, language: str = "python") -> List[TokenInfo]:
        """
        Tokenize code into structured tokens.
        
        Args:
            code: Source code to tokenize
            language: Programming language
            
        Returns:
            List of token information
        """
        if language not in self._patterns:
            logger.warning(f"Language {language} not supported, using generic tokenization")
            return self._generic_tokenize(code)
        
        tokens = []
        patterns = self._patterns[language]
        lines = code.split('\n')
        
        for line_idx, line in enumerate(lines):
            tokens.extend(self._tokenize_line(line, line_idx, patterns))
        
        return tokens
    
    def _tokenize_line(self, line: str, line_idx: int, patterns: Dict[str, str]) -> List[TokenInfo]:
        """Tokenize a single line of code."""
        tokens = []
        remaining = line
        col_offset = 0
        
        while remaining.strip():
            # Skip whitespace
            whitespace_match = re.match(r'\s+', remaining)
            if whitespace_match:
                space_len = whitespace_match.end()
                remaining = remaining[space_len:]
                col_offset += space_len
                continue
            
            # Try to match each token type
            matched = False
            for token_type, pattern in patterns.items():
                match = re.match(pattern, remaining)
                if match:
                    token_text = match.group(0)
                    token = TokenInfo(
                        text=token_text,
                        type=token_type,
                        start_pos=col_offset,
                        end_pos=col_offset + len(token_text),
                        line=line_idx,
                        column=col_offset
                    )
                    tokens.append(token)
                    
                    remaining = remaining[len(token_text):]
                    col_offset += len(token_text)
                    matched = True
                    break
            
            if not matched:
                # Take one character if no pattern matches
                if remaining:
                    char = remaining[0]
                    token = TokenInfo(
                        text=char,
                        type="unknown",
                        start_pos=col_offset,
                        end_pos=col_offset + 1,
                        line=line_idx,
                        column=col_offset
                    )
                    tokens.append(token)
                    remaining = remaining[1:]
                    col_offset += 1
        
        return tokens
    
    def _generic_tokenize(self, code: str) -> List[TokenInfo]:
        """Generic tokenization for unsupported languages."""
        tokens = []
        lines = code.split('\n')
        
        for line_idx, line in enumerate(lines):
            # Simple word-based tokenization
            words = re.findall(r'\S+', line)
            col_offset = 0
            
            for word in words:
                # Find position in line
                pos = line.find(word, col_offset)
                if pos != -1:
                    token = TokenInfo(
                        text=word,
                        type="identifier",
                        start_pos=pos,
                        end_pos=pos + len(word),
                        line=line_idx,
                        column=pos
                    )
                    tokens.append(token)
                    col_offset = pos + len(word)
        
        return tokens
    
    def extract_structure(self, code: str, language: str = "python") -> CodeStructure:
        """
        Extract structural information from code.
        
        Args:
            code: Source code to analyze
            language: Programming language
            
        Returns:
            Code structure information
        """
        # Tokenize first
        tokens = self.tokenize(code, language)
        
        # Extract different elements
        functions = self._extract_functions(code, language)
        classes = self._extract_classes(code, language)
        imports = self._extract_imports(code, language)
        comments = self._extract_comments(code, language)
        strings = self._extract_strings(code, language)
        
        return CodeStructure(
            tokens=tokens,
            functions=functions,
            classes=classes,
            imports=imports,
            comments=comments,
            strings=strings
        )
    
    def _extract_functions(self, code: str, language: str) -> List[Dict]:
        """Extract function definitions."""
        functions = []
        
        if language not in self._patterns:
            return functions
        
        pattern = self._patterns[language]["function"]
        lines = code.split('\n')
        
        for line_idx, line in enumerate(lines):
            match = re.search(pattern, line)
            if match:
                # Extract function name (could be in different groups)
                name = None
                for group in match.groups():
                    if group:
                        name = group
                        break
                
                if name:
                    functions.append({
                        "name": name,
                        "line": line_idx,
                        "full_match": match.group(0),
                        "start_pos": match.start(),
                        "end_pos": match.end()
                    })
        
        return functions
    
    def _extract_classes(self, code: str, language: str) -> List[Dict]:
        """Extract class definitions."""
        classes = []
        
        if language not in self._patterns:
            return classes
        
        pattern = self._patterns[language]["class"]
        lines = code.split('\n')
        
        for line_idx, line in enumerate(lines):
            match = re.search(pattern, line)
            if match:
                name = match.group(1) if match.groups() else None
                if name:
                    classes.append({
                        "name": name,
                        "line": line_idx,
                        "full_match": match.group(0),
                        "start_pos": match.start(),
                        "end_pos": match.end()
                    })
        
        return classes
    
    def _extract_imports(self, code: str, language: str) -> List[Dict]:
        """Extract import statements."""
        imports = []
        
        if language not in self._patterns:
            return imports
        
        pattern = self._patterns[language]["import"]
        lines = code.split('\n')
        
        for line_idx, line in enumerate(lines):
            matches = re.finditer(pattern, line)
            for match in matches:
                imports.append({
                    "statement": match.group(0),
                    "line": line_idx,
                    "start_pos": match.start(),
                    "end_pos": match.end()
                })
        
        return imports
    
    def _extract_comments(self, code: str, language: str) -> List[Dict]:
        """Extract comments."""
        comments = []
        
        if language not in self._patterns:
            return comments
        
        pattern = self._patterns[language]["comment"]
        lines = code.split('\n')
        
        for line_idx, line in enumerate(lines):
            matches = re.finditer(pattern, line, re.MULTILINE | re.DOTALL)
            for match in matches:
                comments.append({
                    "text": match.group(0),
                    "line": line_idx,
                    "start_pos": match.start(),
                    "end_pos": match.end()
                })
        
        return comments
    
    def _extract_strings(self, code: str, language: str) -> List[Dict]:
        """Extract string literals."""
        strings = []
        
        if language not in self._patterns:
            return strings
        
        pattern = self._patterns[language]["string"]
        lines = code.split('\n')
        
        for line_idx, line in enumerate(lines):
            matches = re.finditer(pattern, line, re.MULTILINE | re.DOTALL)
            for match in matches:
                strings.append({
                    "text": match.group(0),
                    "line": line_idx,
                    "start_pos": match.start(),
                    "end_pos": match.end()
                })
        
        return strings
    
    def highlight_syntax(self, code: str, language: str = "python") -> str:
        """
        Add syntax highlighting markup to code.
        
        Args:
            code: Source code to highlight
            language: Programming language
            
        Returns:
            Code with syntax highlighting markup
        """
        if language not in self._patterns:
            return code
        
        lines = code.split('\n')
        highlighted_lines = []
        
        for line in lines:
            highlighted_line = self._highlight_line(line, language)
            highlighted_lines.append(highlighted_line)
        
        return '\n'.join(highlighted_lines)
    
    def _highlight_line(self, line: str, language: str) -> str:
        """Highlight a single line of code."""
        patterns = self._patterns[language]
        highlighted = line
        
        # Apply highlighting in order of precedence
        for token_type in ["string", "comment", "keyword", "function", "class"]:
            if token_type in patterns:
                pattern = patterns[token_type]
                highlighted = re.sub(
                    pattern,
                    lambda m: f'<span class="{token_type}">{m.group(0)}</span>',
                    highlighted
                )
        
        return highlighted
    
    def get_token_at_position(
        self,
        code: str,
        line: int,
        column: int,
        language: str = "python"
    ) -> Optional[TokenInfo]:
        """
        Get the token at a specific position in the code.
        
        Args:
            code: Source code
            line: Line number (0-indexed)
            column: Column number (0-indexed)
            language: Programming language
            
        Returns:
            Token at the specified position, if any
        """
        tokens = self.tokenize(code, language)
        
        for token in tokens:
            if (token.line == line and 
                token.start_pos <= column < token.end_pos):
                return token
        
        return None
    
    def find_matching_bracket(
        self,
        code: str,
        line: int,
        column: int,
        language: str = "python"
    ) -> Optional[Tuple[int, int]]:
        """
        Find the matching bracket for a bracket at the given position.
        
        Args:
            code: Source code
            line: Line number of the bracket
            column: Column number of the bracket
            language: Programming language
            
        Returns:
            (line, column) of matching bracket, if found
        """
        lines = code.split('\n')
        if line >= len(lines) or column >= len(lines[line]):
            return None
        
        char = lines[line][column]
        if char not in "()[]{}":
            return None
        
        # Define bracket pairs
        opening = "([{"
        closing = ")]}"
        pairs = dict(zip(opening, closing))
        reverse_pairs = dict(zip(closing, opening))
        
        if char in opening:
            # Find closing bracket
            target = pairs[char]
            stack = [char]
            
            # Search forward
            for l in range(line, len(lines)):
                start_col = column + 1 if l == line else 0
                for c in range(start_col, len(lines[l])):
                    ch = lines[l][c]
                    if ch in opening:
                        stack.append(ch)
                    elif ch in closing:
                        if stack and pairs.get(stack[-1]) == ch:
                            stack.pop()
                            if not stack:
                                return (l, c)
        
        elif char in closing:
            # Find opening bracket
            target = reverse_pairs[char]
            stack = [char]
            
            # Search backward
            for l in range(line, -1, -1):
                end_col = column - 1 if l == line else len(lines[l]) - 1
                for c in range(end_col, -1, -1):
                    ch = lines[l][c]
                    if ch in closing:
                        stack.append(ch)
                    elif ch in opening:
                        if stack and pairs.get(ch) == stack[-1]:
                            stack.pop()
                            if not stack:
                                return (l, c)
        
        return None