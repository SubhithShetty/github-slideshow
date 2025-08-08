"""Context management for Cursor Pro Model."""

import asyncio
import logging
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
import fnmatch
from dataclasses import dataclass
from .config import Config

logger = logging.getLogger(__name__)


@dataclass
class FileContext:
    """Context information for a single file."""
    path: str
    content: str
    language: str
    size: int
    summary: str = ""
    imports: List[str] = None
    functions: List[str] = None
    classes: List[str] = None
    
    def __post_init__(self):
        if self.imports is None:
            self.imports = []
        if self.functions is None:
            self.functions = []
        if self.classes is None:
            self.classes = []


@dataclass 
class ProjectContext:
    """Context information for the entire project."""
    root_path: str
    files: List[FileContext]
    summary: str = ""
    dependencies: List[str] = None
    structure: Dict = None
    
    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.structure is None:
            self.structure = {}


class ContextManager:
    """
    Manages context for code understanding and generation.
    
    This class handles:
    - File discovery and analysis
    - Context building for prompts
    - Relevant file selection
    - Code structure analysis
    """
    
    def __init__(self, config: Config):
        """Initialize the context manager."""
        self.config = config
        self.code_config = config.code_analysis
        
        # Cache for analyzed files
        self._file_cache: Dict[str, FileContext] = {}
        self._project_cache: Optional[ProjectContext] = None
        
        logger.info("Initialized ContextManager")
    
    async def build_context(
        self,
        prompt: str,
        language: str,
        files: List[str],
        workspace_path: Optional[str] = None
    ) -> Dict:
        """
        Build context for a given prompt and language.
        
        Args:
            prompt: The user prompt
            language: Programming language
            files: List of file paths to include
            workspace_path: Root workspace path
            
        Returns:
            Context dictionary with relevant information
        """
        context = {
            "prompt": prompt,
            "language": language,
            "files": [],
            "summary": "",
            "project_info": {}
        }
        
        # Process explicit files
        if files:
            file_contexts = await self._analyze_files(files)
            context["files"] = [fc.__dict__ for fc in file_contexts]
        
        # Add workspace context if available
        if workspace_path:
            project_context = await self._analyze_project(workspace_path, language)
            if project_context:
                context["project_info"] = {
                    "structure": project_context.structure,
                    "dependencies": project_context.dependencies,
                    "summary": project_context.summary
                }
                
                # Find relevant files based on prompt
                relevant_files = await self._find_relevant_files(
                    prompt, language, project_context
                )
                if relevant_files:
                    context["files"].extend([fc.__dict__ for fc in relevant_files])
        
        # Generate summary
        context["summary"] = self._generate_context_summary(context)
        
        return context
    
    async def _analyze_files(self, file_paths: List[str]) -> List[FileContext]:
        """Analyze a list of files and return their contexts."""
        file_contexts = []
        
        for file_path in file_paths:
            try:
                # Check cache first
                if file_path in self._file_cache:
                    file_contexts.append(self._file_cache[file_path])
                    continue
                
                # Read and analyze file
                path = Path(file_path)
                if not path.exists() or path.stat().st_size > self.code_config.max_file_size:
                    continue
                
                content = await self._read_file_async(path)
                language = self._detect_language(path)
                
                file_context = FileContext(
                    path=str(path),
                    content=content,
                    language=language,
                    size=len(content)
                )
                
                # Analyze content
                await self._analyze_file_content(file_context)
                
                # Cache result
                self._file_cache[file_path] = file_context
                file_contexts.append(file_context)
                
            except Exception as e:
                logger.warning(f"Failed to analyze file {file_path}: {e}")
                continue
        
        return file_contexts
    
    async def _analyze_project(self, workspace_path: str, language: str) -> Optional[ProjectContext]:
        """Analyze the entire project structure."""
        try:
            workspace = Path(workspace_path)
            if not workspace.exists():
                return None
            
            # Check cache
            if self._project_cache and self._project_cache.root_path == str(workspace):
                return self._project_cache
            
            # Discover files
            files = await self._discover_files(workspace, language)
            
            # Analyze discovered files
            file_contexts = await self._analyze_files([str(f) for f in files])
            
            # Build project structure
            structure = await self._build_project_structure(workspace, file_contexts)
            
            # Extract dependencies
            dependencies = self._extract_dependencies(file_contexts)
            
            # Generate summary
            summary = self._generate_project_summary(file_contexts, structure)
            
            project_context = ProjectContext(
                root_path=str(workspace),
                files=file_contexts,
                summary=summary,
                dependencies=dependencies,
                structure=structure
            )
            
            # Cache result
            self._project_cache = project_context
            
            return project_context
            
        except Exception as e:
            logger.error(f"Failed to analyze project {workspace_path}: {e}")
            return None
    
    async def _discover_files(self, workspace: Path, language: str) -> List[Path]:
        """Discover relevant files in the workspace."""
        files = []
        
        def should_include(path: Path) -> bool:
            """Check if file should be included."""
            # Check size limit
            try:
                if path.stat().st_size > self.code_config.max_file_size:
                    return False
            except OSError:
                return False
            
            # Check include patterns
            for pattern in self.code_config.include_patterns:
                if fnmatch.fnmatch(path.name, pattern):
                    break
            else:
                return False
            
            # Check exclude patterns
            for pattern in self.code_config.exclude_patterns:
                if fnmatch.fnmatch(str(path), pattern):
                    return False
            
            return True
        
        # Walk through directory
        for path in workspace.rglob("*"):
            if path.is_file() and should_include(path):
                files.append(path)
                
                # Limit number of files
                if len(files) >= self.code_config.max_context_files:
                    break
        
        return files
    
    async def _find_relevant_files(
        self,
        prompt: str,
        language: str,
        project_context: ProjectContext
    ) -> List[FileContext]:
        """Find files relevant to the prompt."""
        relevant_files = []
        prompt_lower = prompt.lower()
        
        # Score files based on relevance
        scored_files = []
        for file_context in project_context.files:
            score = 0
            
            # Language match
            if file_context.language == language:
                score += 10
            
            # Content relevance
            content_lower = file_context.content.lower()
            for word in prompt_lower.split():
                if len(word) > 3:  # Skip short words
                    score += content_lower.count(word) * 2
            
            # Function/class name relevance
            for func in file_context.functions:
                if any(word in func.lower() for word in prompt_lower.split()):
                    score += 5
            
            for cls in file_context.classes:
                if any(word in cls.lower() for word in prompt_lower.split()):
                    score += 5
            
            if score > 0:
                scored_files.append((score, file_context))
        
        # Sort by score and take top files
        scored_files.sort(key=lambda x: x[0], reverse=True)
        relevant_files = [fc for _, fc in scored_files[:10]]  # Top 10 relevant files
        
        return relevant_files
    
    async def _analyze_file_content(self, file_context: FileContext) -> None:
        """Analyze file content to extract metadata."""
        content = file_context.content
        language = file_context.language
        
        # Extract imports (basic implementation)
        if language == "python":
            file_context.imports = self._extract_python_imports(content)
            file_context.functions = self._extract_python_functions(content)
            file_context.classes = self._extract_python_classes(content)
        elif language in ["javascript", "typescript"]:
            file_context.imports = self._extract_js_imports(content)
            file_context.functions = self._extract_js_functions(content)
            file_context.classes = self._extract_js_classes(content)
        
        # Generate summary
        file_context.summary = self._generate_file_summary(file_context)
    
    def _extract_python_imports(self, content: str) -> List[str]:
        """Extract Python imports from content."""
        imports = []
        for line in content.split('\n'):
            line = line.strip()
            if line.startswith('import ') or line.startswith('from '):
                imports.append(line)
        return imports
    
    def _extract_python_functions(self, content: str) -> List[str]:
        """Extract Python function names."""
        import re
        functions = []
        pattern = r'def\s+(\w+)\s*\('
        for match in re.finditer(pattern, content):
            functions.append(match.group(1))
        return functions
    
    def _extract_python_classes(self, content: str) -> List[str]:
        """Extract Python class names."""
        import re
        classes = []
        pattern = r'class\s+(\w+)(?:\s*\([^)]*\))?\s*:'
        for match in re.finditer(pattern, content):
            classes.append(match.group(1))
        return classes
    
    def _extract_js_imports(self, content: str) -> List[str]:
        """Extract JavaScript/TypeScript imports."""
        import re
        imports = []
        patterns = [
            r'import\s+.*\s+from\s+["\'][^"\']+["\']',
            r'const\s+.*\s*=\s*require\s*\(["\'][^"\']+["\']\)',
            r'import\s*\(["\'][^"\']+["\']\)'
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                imports.append(match.group(0))
        return imports
    
    def _extract_js_functions(self, content: str) -> List[str]:
        """Extract JavaScript/TypeScript function names."""
        import re
        functions = []
        patterns = [
            r'function\s+(\w+)\s*\(',
            r'const\s+(\w+)\s*=\s*(?:async\s+)?(?:\([^)]*\)\s*=>\s*{|\([^)]*\)\s*=>)',
            r'(\w+)\s*:\s*(?:async\s+)?function\s*\(',
            r'(\w+)\s*\([^)]*\)\s*{'
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                functions.append(match.group(1))
        return functions
    
    def _extract_js_classes(self, content: str) -> List[str]:
        """Extract JavaScript/TypeScript class names."""
        import re
        classes = []
        pattern = r'class\s+(\w+)(?:\s+extends\s+\w+)?\s*{'
        for match in re.finditer(pattern, content):
            classes.append(match.group(1))
        return classes
    
    def _detect_language(self, path: Path) -> str:
        """Detect programming language from file extension."""
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
            '.md': 'markdown',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.xml': 'xml',
            '.html': 'html',
            '.css': 'css',
            '.scss': 'scss',
            '.less': 'less'
        }
        
        return extension_map.get(path.suffix.lower(), 'text')
    
    async def _read_file_async(self, path: Path) -> str:
        """Read file content asynchronously."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with different encoding
            try:
                with open(path, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception:
                return ""
        except Exception:
            return ""
    
    async def _build_project_structure(
        self,
        workspace: Path,
        file_contexts: List[FileContext]
    ) -> Dict:
        """Build project structure representation."""
        structure = {
            "directories": {},
            "files_by_type": {},
            "total_files": len(file_contexts),
            "languages": set()
        }
        
        for file_context in file_contexts:
            path = Path(file_context.path)
            relative_path = path.relative_to(workspace)
            
            # Track language
            structure["languages"].add(file_context.language)
            
            # Group by file type
            lang = file_context.language
            if lang not in structure["files_by_type"]:
                structure["files_by_type"][lang] = []
            structure["files_by_type"][lang].append(str(relative_path))
            
            # Build directory structure
            parts = relative_path.parts[:-1]  # Exclude filename
            current = structure["directories"]
            for part in parts:
                if part not in current:
                    current[part] = {}
                current = current[part]
        
        # Convert set to list for JSON serialization
        structure["languages"] = list(structure["languages"])
        
        return structure
    
    def _extract_dependencies(self, file_contexts: List[FileContext]) -> List[str]:
        """Extract project dependencies from files."""
        dependencies = set()
        
        for file_context in file_contexts:
            for import_stmt in file_context.imports:
                # Extract package names from imports
                if file_context.language == "python":
                    # Extract from "import package" or "from package import ..."
                    import re
                    if import_stmt.startswith("import "):
                        pkg = import_stmt.replace("import ", "").split(".")[0].split(" as ")[0]
                        dependencies.add(pkg)
                    elif import_stmt.startswith("from "):
                        pkg = import_stmt.split(" ")[1].split(".")[0]
                        dependencies.add(pkg)
                
                elif file_context.language in ["javascript", "typescript"]:
                    # Extract from require() or import statements
                    import re
                    match = re.search(r'["\']([^"\']+)["\']', import_stmt)
                    if match:
                        pkg = match.group(1)
                        if not pkg.startswith('./') and not pkg.startswith('../'):
                            dependencies.add(pkg.split('/')[0])
        
        return list(dependencies)
    
    def _generate_file_summary(self, file_context: FileContext) -> str:
        """Generate a summary for a file."""
        summary_parts = []
        
        summary_parts.append(f"{file_context.language.title()} file with {len(file_context.content.split())} words")
        
        if file_context.classes:
            summary_parts.append(f"Contains classes: {', '.join(file_context.classes[:3])}")
        
        if file_context.functions:
            summary_parts.append(f"Contains functions: {', '.join(file_context.functions[:5])}")
        
        if file_context.imports:
            summary_parts.append(f"Imports {len(file_context.imports)} modules")
        
        return ". ".join(summary_parts) + "."
    
    def _generate_project_summary(
        self,
        file_contexts: List[FileContext],
        structure: Dict
    ) -> str:
        """Generate a summary for the entire project."""
        total_files = len(file_contexts)
        languages = structure.get("languages", [])
        
        summary = f"Project with {total_files} files using {', '.join(languages[:3])}"
        
        if len(languages) > 3:
            summary += f" and {len(languages) - 3} other languages"
        
        return summary + "."
    
    def _generate_context_summary(self, context: Dict) -> str:
        """Generate a summary of the current context."""
        summary_parts = []
        
        if context.get("files"):
            summary_parts.append(f"Analyzing {len(context['files'])} files")
        
        if context.get("project_info", {}).get("languages"):
            langs = context["project_info"]["languages"]
            summary_parts.append(f"Project uses {', '.join(langs[:2])}")
        
        summary_parts.append(f"Working with {context['language']}")
        
        return ". ".join(summary_parts) + "."
    
    def clear_cache(self) -> None:
        """Clear all caches."""
        self._file_cache.clear()
        self._project_cache = None
        logger.info("Cleared context cache")