"""File and directory utilities for Cursor Pro Model."""

import os
import asyncio
import aiofiles
import fnmatch
import mimetypes
from pathlib import Path
from typing import List, Optional, Set, Dict, AsyncGenerator
import logging

logger = logging.getLogger(__name__)


class FileUtils:
    """Utility class for file and directory operations."""
    
    # Common code file extensions
    CODE_EXTENSIONS = {
        '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.cxx', '.cc', 
        '.c', '.h', '.hpp', '.rs', '.go', '.rb', '.php', '.swift', '.kt',
        '.scala', '.cs', '.sh', '.bat', '.ps1', '.sql', '.html', '.css',
        '.scss', '.less', '.xml', '.json', '.yaml', '.yml', '.toml', '.ini',
        '.cfg', '.conf', '.md', '.rst', '.txt'
    }
    
    # Binary file extensions to skip
    BINARY_EXTENSIONS = {
        '.exe', '.dll', '.so', '.dylib', '.bin', '.img', '.iso', '.zip',
        '.tar', '.gz', '.rar', '.7z', '.pdf', '.doc', '.docx', '.xls',
        '.xlsx', '.ppt', '.pptx', '.jpg', '.jpeg', '.png', '.gif', '.bmp',
        '.tiff', '.mp3', '.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm'
    }
    
    # Directories to typically ignore
    IGNORE_DIRS = {
        '.git', '.svn', '.hg', '.bzr', '__pycache__', '.pytest_cache',
        'node_modules', '.npm', '.yarn', 'venv', '.venv', 'env', '.env',
        'build', 'dist', '.tox', '.coverage', '.nyc_output', 'coverage',
        '.idea', '.vscode', '.vs', 'target', 'bin', 'obj', '.gradle'
    }
    
    @staticmethod
    async def read_file_async(file_path: Path, encoding: str = 'utf-8') -> Optional[str]:
        """
        Read a file asynchronously.
        
        Args:
            file_path: Path to the file
            encoding: File encoding
            
        Returns:
            File content or None if error
        """
        try:
            async with aiofiles.open(file_path, 'r', encoding=encoding) as f:
                return await f.read()
        except UnicodeDecodeError:
            # Try with different encodings
            for enc in ['latin-1', 'cp1252', 'utf-16']:
                try:
                    async with aiofiles.open(file_path, 'r', encoding=enc) as f:
                        content = await f.read()
                        logger.warning(f"Read {file_path} with encoding {enc}")
                        return content
                except:
                    continue
            logger.error(f"Could not read {file_path} with any encoding")
            return None
        except Exception as e:
            logger.error(f"Error reading {file_path}: {e}")
            return None
    
    @staticmethod
    async def write_file_async(file_path: Path, content: str, encoding: str = 'utf-8') -> bool:
        """
        Write a file asynchronously.
        
        Args:
            file_path: Path to the file
            content: Content to write
            encoding: File encoding
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Create parent directories if they don't exist
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            async with aiofiles.open(file_path, 'w', encoding=encoding) as f:
                await f.write(content)
            return True
        except Exception as e:
            logger.error(f"Error writing {file_path}: {e}")
            return False
    
    @staticmethod
    def is_text_file(file_path: Path) -> bool:
        """
        Check if a file is a text file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if text file, False otherwise
        """
        # Check by extension first
        if file_path.suffix.lower() in FileUtils.CODE_EXTENSIONS:
            return True
        
        if file_path.suffix.lower() in FileUtils.BINARY_EXTENSIONS:
            return False
        
        # Check MIME type
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type and mime_type.startswith('text'):
            return True
        
        # Check file content (sample first few bytes)
        try:
            with open(file_path, 'rb') as f:
                sample = f.read(8192)  # Read first 8KB
                
            # Check for null bytes (common in binary files)
            if b'\x00' in sample:
                return False
            
            # Try to decode as UTF-8
            try:
                sample.decode('utf-8')
                return True
            except UnicodeDecodeError:
                # Try other encodings
                for encoding in ['latin-1', 'cp1252']:
                    try:
                        sample.decode(encoding)
                        return True
                    except UnicodeDecodeError:
                        continue
                return False
                
        except Exception:
            return False
    
    @staticmethod
    def should_ignore_file(file_path: Path, ignore_patterns: Optional[List[str]] = None) -> bool:
        """
        Check if a file should be ignored.
        
        Args:
            file_path: Path to the file
            ignore_patterns: Additional ignore patterns
            
        Returns:
            True if file should be ignored
        """
        # Check if in ignored directory
        for part in file_path.parts:
            if part in FileUtils.IGNORE_DIRS:
                return True
        
        # Check ignore patterns
        if ignore_patterns:
            for pattern in ignore_patterns:
                if fnmatch.fnmatch(str(file_path), pattern) or fnmatch.fnmatch(file_path.name, pattern):
                    return True
        
        # Check if binary file
        if file_path.suffix.lower() in FileUtils.BINARY_EXTENSIONS:
            return True
        
        # Check for hidden files (starting with .)
        if file_path.name.startswith('.') and file_path.name not in ['.gitignore', '.env', '.env.example']:
            return True
        
        return False
    
    @staticmethod
    async def discover_files(
        root_path: Path,
        max_files: int = 1000,
        max_file_size: int = 1024 * 1024,  # 1MB
        include_patterns: Optional[List[str]] = None,
        exclude_patterns: Optional[List[str]] = None
    ) -> List[Path]:
        """
        Discover files in a directory tree.
        
        Args:
            root_path: Root directory to search
            max_files: Maximum number of files to discover
            max_file_size: Maximum file size in bytes
            include_patterns: Patterns for files to include
            exclude_patterns: Patterns for files to exclude
            
        Returns:
            List of discovered file paths
        """
        files = []
        
        if not root_path.exists() or not root_path.is_dir():
            return files
        
        try:
            for file_path in root_path.rglob('*'):
                if len(files) >= max_files:
                    break
                
                if not file_path.is_file():
                    continue
                
                # Check file size
                try:
                    if file_path.stat().st_size > max_file_size:
                        continue
                except OSError:
                    continue
                
                # Check if should ignore
                if FileUtils.should_ignore_file(file_path, exclude_patterns):
                    continue
                
                # Check include patterns
                if include_patterns:
                    included = False
                    for pattern in include_patterns:
                        if fnmatch.fnmatch(str(file_path), pattern) or fnmatch.fnmatch(file_path.name, pattern):
                            included = True
                            break
                    if not included:
                        continue
                
                # Check if text file
                if not FileUtils.is_text_file(file_path):
                    continue
                
                files.append(file_path)
        
        except Exception as e:
            logger.error(f"Error discovering files in {root_path}: {e}")
        
        return files
    
    @staticmethod
    def get_file_language(file_path: Path) -> str:
        """
        Determine the programming language of a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Language name or 'unknown'
        """
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.jsx': 'javascript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.cxx': 'cpp',
            '.cc': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.rs': 'rust',
            '.go': 'go',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.cs': 'csharp',
            '.sh': 'bash',
            '.bat': 'batch',
            '.ps1': 'powershell',
            '.sql': 'sql',
            '.html': 'html',
            '.htm': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.less': 'less',
            '.xml': 'xml',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.toml': 'toml',
            '.ini': 'ini',
            '.cfg': 'config',
            '.conf': 'config',
            '.md': 'markdown',
            '.rst': 'restructuredtext',
            '.txt': 'text'
        }
        
        ext = file_path.suffix.lower()
        return extension_map.get(ext, 'unknown')
    
    @staticmethod
    async def get_directory_stats(root_path: Path) -> Dict:
        """
        Get statistics about a directory.
        
        Args:
            root_path: Root directory
            
        Returns:
            Dictionary with directory statistics
        """
        stats = {
            'total_files': 0,
            'total_size': 0,
            'languages': {},
            'file_types': {},
            'directories': 0
        }
        
        if not root_path.exists():
            return stats
        
        try:
            for item in root_path.rglob('*'):
                if item.is_file():
                    stats['total_files'] += 1
                    
                    # File size
                    try:
                        size = item.stat().st_size
                        stats['total_size'] += size
                    except OSError:
                        continue
                    
                    # Language detection
                    language = FileUtils.get_file_language(item)
                    stats['languages'][language] = stats['languages'].get(language, 0) + 1
                    
                    # File type
                    ext = item.suffix.lower() or 'no_extension'
                    stats['file_types'][ext] = stats['file_types'].get(ext, 0) + 1
                
                elif item.is_dir():
                    stats['directories'] += 1
        
        except Exception as e:
            logger.error(f"Error getting directory stats for {root_path}: {e}")
        
        return stats
    
    @staticmethod
    def normalize_path(path: str, root_path: Optional[Path] = None) -> Path:
        """
        Normalize a file path.
        
        Args:
            path: Path string to normalize
            root_path: Optional root path to resolve relative paths
            
        Returns:
            Normalized Path object
        """
        path_obj = Path(path)
        
        # Resolve relative paths
        if not path_obj.is_absolute() and root_path:
            path_obj = root_path / path_obj
        
        # Resolve to absolute path
        try:
            path_obj = path_obj.resolve()
        except Exception:
            # If resolution fails, just return the path as-is
            pass
        
        return path_obj
    
    @staticmethod
    async def watch_file_changes(
        file_path: Path,
        callback,
        check_interval: float = 1.0
    ) -> None:
        """
        Watch a file for changes and call callback when modified.
        
        Args:
            file_path: Path to watch
            callback: Function to call when file changes
            check_interval: Check interval in seconds
        """
        if not file_path.exists():
            return
        
        last_modified = file_path.stat().st_mtime
        
        while True:
            await asyncio.sleep(check_interval)
            
            try:
                current_modified = file_path.stat().st_mtime
                if current_modified != last_modified:
                    last_modified = current_modified
                    await callback(file_path)
            except FileNotFoundError:
                # File was deleted
                break
            except Exception as e:
                logger.error(f"Error watching file {file_path}: {e}")
                break
    
    @staticmethod
    def create_gitignore(directory: Path, patterns: List[str]) -> bool:
        """
        Create a .gitignore file with specified patterns.
        
        Args:
            directory: Directory to create .gitignore in
            patterns: List of patterns to ignore
            
        Returns:
            True if successful
        """
        try:
            gitignore_path = directory / '.gitignore'
            
            # Read existing patterns if file exists
            existing_patterns = set()
            if gitignore_path.exists():
                with open(gitignore_path, 'r') as f:
                    existing_patterns.update(line.strip() for line in f if line.strip() and not line.startswith('#'))
            
            # Add new patterns
            all_patterns = existing_patterns.union(set(patterns))
            
            # Write gitignore
            with open(gitignore_path, 'w') as f:
                f.write("# Auto-generated .gitignore\n\n")
                for pattern in sorted(all_patterns):
                    f.write(f"{pattern}\n")
            
            return True
        except Exception as e:
            logger.error(f"Error creating .gitignore: {e}")
            return False
    
    @staticmethod
    def safe_filename(filename: str) -> str:
        """
        Convert a string to a safe filename.
        
        Args:
            filename: Original filename
            
        Returns:
            Safe filename string
        """
        # Replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        
        # Remove leading/trailing whitespace and dots
        filename = filename.strip(' .')
        
        # Ensure not empty
        if not filename:
            filename = 'untitled'
        
        # Limit length
        if len(filename) > 255:
            filename = filename[:255]
        
        return filename