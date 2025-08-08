"""Text processing utilities for Cursor Pro Model."""

import re
from typing import List, Dict, Tuple, Optional


class TextUtils:
    """Utility class for text processing operations."""
    
    @staticmethod
    def clean_text(text: str) -> str:
        """
        Clean and normalize text.
        
        Args:
            text: Input text to clean
            
        Returns:
            Cleaned text
        """
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove leading/trailing whitespace
        text = text.strip()
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        return text
    
    @staticmethod
    def extract_code_blocks(text: str) -> List[Dict[str, str]]:
        """
        Extract code blocks from markdown-style text.
        
        Args:
            text: Input text containing code blocks
            
        Returns:
            List of dictionaries with 'language' and 'code' keys
        """
        code_blocks = []
        
        # Pattern for fenced code blocks
        pattern = r'```(\w*)\n(.*?)\n```'
        
        for match in re.finditer(pattern, text, re.DOTALL):
            language = match.group(1) or 'text'
            code = match.group(2)
            
            code_blocks.append({
                'language': language,
                'code': code.strip()
            })
        
        return code_blocks
    
    @staticmethod
    def split_into_sentences(text: str) -> List[str]:
        """
        Split text into sentences.
        
        Args:
            text: Input text
            
        Returns:
            List of sentences
        """
        # Simple sentence splitting (can be improved)
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
    
    @staticmethod
    def extract_keywords(text: str, min_length: int = 3) -> List[str]:
        """
        Extract keywords from text.
        
        Args:
            text: Input text
            min_length: Minimum keyword length
            
        Returns:
            List of keywords
        """
        # Convert to lowercase and extract words
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        
        # Filter by length and remove common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have',
            'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we',
            'they', 'me', 'him', 'her', 'us', 'them'
        }
        
        keywords = [
            word for word in words 
            if len(word) >= min_length and word not in stop_words
        ]
        
        # Remove duplicates while preserving order
        seen = set()
        unique_keywords = []
        for keyword in keywords:
            if keyword not in seen:
                seen.add(keyword)
                unique_keywords.append(keyword)
        
        return unique_keywords
    
    @staticmethod
    def calculate_similarity(text1: str, text2: str) -> float:
        """
        Calculate similarity between two texts using Jaccard similarity.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0 and 1
        """
        # Extract words
        words1 = set(re.findall(r'\b\w+\b', text1.lower()))
        words2 = set(re.findall(r'\b\w+\b', text2.lower()))
        
        # Calculate Jaccard similarity
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        
        if not union:
            return 0.0
        
        return len(intersection) / len(union)
    
    @staticmethod
    def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
        """
        Truncate text to maximum length.
        
        Args:
            text: Input text
            max_length: Maximum length including suffix
            suffix: Suffix to add when truncating
            
        Returns:
            Truncated text
        """
        if len(text) <= max_length:
            return text
        
        truncated_length = max_length - len(suffix)
        if truncated_length <= 0:
            return suffix[:max_length]
        
        return text[:truncated_length] + suffix
    
    @staticmethod
    def format_code_snippet(code: str, language: str = "python", line_numbers: bool = False) -> str:
        """
        Format code snippet with markdown.
        
        Args:
            code: Code to format
            language: Programming language
            line_numbers: Whether to add line numbers
            
        Returns:
            Formatted code snippet
        """
        if line_numbers:
            lines = code.split('\n')
            numbered_lines = []
            for i, line in enumerate(lines, 1):
                numbered_lines.append(f"{i:3d} | {line}")
            code = '\n'.join(numbered_lines)
        
        return f"```{language}\n{code}\n```"
    
    @staticmethod
    def parse_function_signature(signature: str) -> Dict[str, str]:
        """
        Parse function signature into components.
        
        Args:
            signature: Function signature string
            
        Returns:
            Dictionary with function components
        """
        # Simple parsing - can be enhanced for complex signatures
        result = {
            'name': '',
            'parameters': [],
            'return_type': ''
        }
        
        # Extract function name
        name_match = re.search(r'(\w+)\s*\(', signature)
        if name_match:
            result['name'] = name_match.group(1)
        
        # Extract parameters
        params_match = re.search(r'\((.*?)\)', signature)
        if params_match:
            params_str = params_match.group(1)
            if params_str.strip():
                result['parameters'] = [p.strip() for p in params_str.split(',')]
        
        # Extract return type (for typed languages)
        return_match = re.search(r'->\s*(\w+)', signature)
        if return_match:
            result['return_type'] = return_match.group(1)
        
        return result
    
    @staticmethod
    def indent_text(text: str, indent: str = "    ") -> str:
        """
        Indent all lines in text.
        
        Args:
            text: Input text
            indent: Indentation string
            
        Returns:
            Indented text
        """
        lines = text.split('\n')
        return '\n'.join(indent + line for line in lines)
    
    @staticmethod
    def dedent_text(text: str) -> str:
        """
        Remove common leading whitespace from text.
        
        Args:
            text: Input text
            
        Returns:
            Dedented text
        """
        import textwrap
        return textwrap.dedent(text)
    
    @staticmethod
    def word_count(text: str) -> Dict[str, int]:
        """
        Count various text metrics.
        
        Args:
            text: Input text
            
        Returns:
            Dictionary with text metrics
        """
        lines = text.split('\n')
        words = re.findall(r'\b\w+\b', text)
        characters = len(text)
        characters_no_spaces = len(re.sub(r'\s', '', text))
        
        return {
            'lines': len(lines),
            'words': len(words),
            'characters': characters,
            'characters_no_spaces': characters_no_spaces,
            'paragraphs': len([p for p in text.split('\n\n') if p.strip()])
        }
    
    @staticmethod
    def highlight_differences(text1: str, text2: str) -> Tuple[str, str]:
        """
        Highlight differences between two texts.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Tuple of highlighted texts
        """
        import difflib
        
        lines1 = text1.splitlines()
        lines2 = text2.splitlines()
        
        differ = difflib.unified_diff(lines1, lines2, lineterm='')
        diff_lines = list(differ)
        
        # Simple highlighting (can be enhanced with HTML/markdown)
        highlighted1 = []
        highlighted2 = []
        
        for line in diff_lines:
            if line.startswith('-'):
                highlighted1.append(f"[-] {line[1:]}")
            elif line.startswith('+'):
                highlighted2.append(f"[+] {line[1:]}")
            elif not line.startswith('@@') and not line.startswith('---') and not line.startswith('+++'):
                highlighted1.append(f"    {line}")
                highlighted2.append(f"    {line}")
        
        return '\n'.join(highlighted1), '\n'.join(highlighted2)
    
    @staticmethod
    def generate_summary(text: str, max_sentences: int = 3) -> str:
        """
        Generate a simple summary of text.
        
        Args:
            text: Input text
            max_sentences: Maximum sentences in summary
            
        Returns:
            Text summary
        """
        sentences = TextUtils.split_into_sentences(text)
        
        if len(sentences) <= max_sentences:
            return text
        
        # Simple approach: take first and last sentences, plus one from middle
        if max_sentences == 1:
            return sentences[0]
        elif max_sentences == 2:
            return f"{sentences[0]} {sentences[-1]}"
        else:
            middle_idx = len(sentences) // 2
            selected = [sentences[0], sentences[middle_idx], sentences[-1]]
            return ' '.join(selected[:max_sentences])
    
    @staticmethod
    def escape_markdown(text: str) -> str:
        """
        Escape markdown special characters.
        
        Args:
            text: Input text
            
        Returns:
            Escaped text
        """
        special_chars = ['*', '_', '`', '[', ']', '(', ')', '#', '+', '-', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text
    
    @staticmethod
    def unescape_markdown(text: str) -> str:
        """
        Unescape markdown special characters.
        
        Args:
            text: Input text
            
        Returns:
            Unescaped text
        """
        special_chars = ['*', '_', '`', '[', ']', '(', ')', '#', '+', '-', '.', '!']
        for char in special_chars:
            text = text.replace(f'\\{char}', char)
        return text