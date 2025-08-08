"""API data models for Cursor Pro Model."""

from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, Field
from enum import Enum


class TaskType(str, Enum):
    """Types of tasks the model can perform."""
    CODE_GENERATION = "code_generation"
    CODE_COMPLETION = "code_completion" 
    CODE_EXPLANATION = "code_explanation"
    CODE_REFACTOR = "code_refactor"
    CODE_REVIEW = "code_review"
    BUG_FIX = "bug_fix"
    TEST_GENERATION = "test_generation"
    DOCUMENTATION = "documentation"


class Language(str, Enum):
    """Supported programming languages."""
    PYTHON = "python"
    JAVASCRIPT = "javascript"
    TYPESCRIPT = "typescript"
    JAVA = "java"
    CPP = "cpp"
    RUST = "rust"
    GO = "go"
    HTML = "html"
    CSS = "css"
    SQL = "sql"
    MARKDOWN = "markdown"


class CodeGenerationRequest(BaseModel):
    """Request for code generation."""
    prompt: str = Field(..., description="Description of the code to generate")
    language: Language = Field(default=Language.PYTHON, description="Programming language")
    context_files: Optional[List[str]] = Field(default=None, description="Additional context files")
    max_tokens: Optional[int] = Field(default=None, description="Maximum tokens to generate")
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0, description="Sampling temperature")
    style_preferences: Optional[Dict[str, Any]] = Field(default=None, description="Code style preferences")


class CodeCompletionRequest(BaseModel):
    """Request for code completion."""
    code: str = Field(..., description="Current code content")
    cursor_position: int = Field(..., description="Cursor position in the code")
    language: Language = Field(default=Language.PYTHON, description="Programming language")
    context_files: Optional[List[str]] = Field(default=None, description="Additional context files")
    max_suggestions: Optional[int] = Field(default=5, ge=1, le=10, description="Maximum number of suggestions")


class CodeExplanationRequest(BaseModel):
    """Request for code explanation."""
    code: str = Field(..., description="Code to explain")
    language: Language = Field(default=Language.PYTHON, description="Programming language")
    context_files: Optional[List[str]] = Field(default=None, description="Additional context files")
    detail_level: Optional[str] = Field(default="medium", description="Detail level: basic, medium, detailed")


class CodeRefactorRequest(BaseModel):
    """Request for code refactoring."""
    code: str = Field(..., description="Code to refactor")
    language: Language = Field(default=Language.PYTHON, description="Programming language")
    refactor_type: str = Field(..., description="Type of refactoring: optimize, simplify, extract_function, etc.")
    context_files: Optional[List[str]] = Field(default=None, description="Additional context files")


class CodeReviewRequest(BaseModel):
    """Request for code review."""
    code: str = Field(..., description="Code to review")
    language: Language = Field(default=Language.PYTHON, description="Programming language")
    context_files: Optional[List[str]] = Field(default=None, description="Additional context files")
    focus_areas: Optional[List[str]] = Field(default=None, description="Specific areas to focus on")


class BugFixRequest(BaseModel):
    """Request for bug fixing."""
    code: str = Field(..., description="Code with bug")
    error_message: Optional[str] = Field(default=None, description="Error message if available")
    language: Language = Field(default=Language.PYTHON, description="Programming language")
    context_files: Optional[List[str]] = Field(default=None, description="Additional context files")
    description: Optional[str] = Field(default=None, description="Description of the bug")


class TestGenerationRequest(BaseModel):
    """Request for test generation."""
    code: str = Field(..., description="Code to generate tests for")
    language: Language = Field(default=Language.PYTHON, description="Programming language")
    test_framework: Optional[str] = Field(default=None, description="Preferred test framework")
    context_files: Optional[List[str]] = Field(default=None, description="Additional context files")
    coverage_type: Optional[str] = Field(default="unit", description="Type of tests: unit, integration, etc.")


class DocumentationRequest(BaseModel):
    """Request for documentation generation."""
    code: str = Field(..., description="Code to document")
    language: Language = Field(default=Language.PYTHON, description="Programming language")
    doc_type: str = Field(default="docstring", description="Type of documentation: docstring, readme, api, etc.")
    context_files: Optional[List[str]] = Field(default=None, description="Additional context files")
    format: Optional[str] = Field(default="markdown", description="Documentation format")


class CodeGenerationResponse(BaseModel):
    """Response for code generation."""
    generated_code: str = Field(..., description="Generated code")
    explanation: Optional[str] = Field(default=None, description="Explanation of the generated code")
    suggestions: Optional[List[str]] = Field(default=None, description="Additional suggestions")
    language: str = Field(..., description="Programming language used")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class CodeCompletionResponse(BaseModel):
    """Response for code completion."""
    suggestions: List[str] = Field(..., description="List of completion suggestions")
    context_info: Optional[Dict[str, Any]] = Field(default=None, description="Context information")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class CodeExplanationResponse(BaseModel):
    """Response for code explanation."""
    explanation: str = Field(..., description="Detailed explanation of the code")
    key_concepts: Optional[List[str]] = Field(default=None, description="Key concepts identified")
    complexity_analysis: Optional[Dict[str, Any]] = Field(default=None, description="Complexity analysis")
    suggestions: Optional[List[str]] = Field(default=None, description="Improvement suggestions")


class CodeRefactorResponse(BaseModel):
    """Response for code refactoring."""
    refactored_code: str = Field(..., description="Refactored code")
    changes_made: List[str] = Field(..., description="List of changes made")
    improvement_metrics: Optional[Dict[str, Any]] = Field(default=None, description="Improvement metrics")
    explanation: Optional[str] = Field(default=None, description="Explanation of refactoring")


class CodeReviewResponse(BaseModel):
    """Response for code review."""
    overall_score: Optional[float] = Field(default=None, ge=0.0, le=10.0, description="Overall code quality score")
    issues: List[Dict[str, Any]] = Field(default=[], description="List of identified issues")
    suggestions: List[str] = Field(default=[], description="Improvement suggestions")
    strengths: List[str] = Field(default=[], description="Code strengths")
    summary: str = Field(..., description="Review summary")


class BugFixResponse(BaseModel):
    """Response for bug fixing."""
    fixed_code: str = Field(..., description="Fixed code")
    bug_description: str = Field(..., description="Description of the bug found")
    fix_explanation: str = Field(..., description="Explanation of the fix")
    prevention_tips: Optional[List[str]] = Field(default=None, description="Tips to prevent similar bugs")


class TestGenerationResponse(BaseModel):
    """Response for test generation."""
    test_code: str = Field(..., description="Generated test code")
    test_cases: List[Dict[str, Any]] = Field(..., description="List of test cases")
    coverage_info: Optional[Dict[str, Any]] = Field(default=None, description="Coverage information")
    setup_instructions: Optional[str] = Field(default=None, description="Setup instructions")


class DocumentationResponse(BaseModel):
    """Response for documentation generation."""
    documentation: str = Field(..., description="Generated documentation")
    format: str = Field(..., description="Documentation format")
    sections: Optional[List[str]] = Field(default=None, description="Documentation sections")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str = Field(..., description="Service status")
    model_loaded: bool = Field(..., description="Whether the model is loaded")
    model_name: str = Field(..., description="Name of the loaded model")
    device: str = Field(..., description="Device being used")
    gpu_available: bool = Field(..., description="Whether GPU is available")
    memory_usage: int = Field(..., description="Current memory usage")
    uptime: Optional[float] = Field(default=None, description="Service uptime in seconds")


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Error message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    code: Optional[int] = Field(default=None, description="Error code")


class StreamingResponse(BaseModel):
    """Streaming response chunk."""
    chunk_id: int = Field(..., description="Chunk sequence number")
    content: str = Field(..., description="Content chunk")
    is_final: bool = Field(default=False, description="Whether this is the final chunk")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Chunk metadata")


class WorkspaceInfo(BaseModel):
    """Workspace information."""
    path: str = Field(..., description="Workspace path")
    files_count: int = Field(..., description="Number of files")
    languages: List[str] = Field(..., description="Programming languages detected")
    total_size: int = Field(..., description="Total size in bytes")
    last_modified: Optional[str] = Field(default=None, description="Last modification time")


class FileInfo(BaseModel):
    """File information."""
    path: str = Field(..., description="File path")
    language: str = Field(..., description="Programming language")
    size: int = Field(..., description="File size in bytes")
    last_modified: Optional[str] = Field(default=None, description="Last modification time")
    encoding: Optional[str] = Field(default=None, description="File encoding")


class AnalysisResult(BaseModel):
    """Code analysis result."""
    file_path: str = Field(..., description="Path of analyzed file")
    language: str = Field(..., description="Programming language")
    symbols: List[Dict[str, Any]] = Field(default=[], description="Extracted symbols")
    dependencies: List[Dict[str, Any]] = Field(default=[], description="Dependencies")
    issues: List[Dict[str, Any]] = Field(default=[], description="Code issues")
    metrics: Dict[str, Any] = Field(default={}, description="Code metrics")
    complexity: Optional[Dict[str, Any]] = Field(default=None, description="Complexity analysis")


class ChatRequest(BaseModel):
    """Chat request for conversational interface."""
    message: str = Field(..., description="User message")
    conversation_id: Optional[str] = Field(default=None, description="Conversation ID")
    context_files: Optional[List[str]] = Field(default=None, description="Context files")
    workspace_path: Optional[str] = Field(default=None, description="Workspace path")
    task_type: Optional[TaskType] = Field(default=None, description="Specific task type")


class ChatResponse(BaseModel):
    """Chat response."""
    response: str = Field(..., description="Assistant response")
    conversation_id: str = Field(..., description="Conversation ID")
    suggestions: Optional[List[str]] = Field(default=None, description="Follow-up suggestions")
    code_blocks: Optional[List[Dict[str, Any]]] = Field(default=None, description="Code blocks in response")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Additional metadata")


# Request/Response union types for generic handling
AnyRequest = Union[
    CodeGenerationRequest,
    CodeCompletionRequest,
    CodeExplanationRequest,
    CodeRefactorRequest,
    CodeReviewRequest,
    BugFixRequest,
    TestGenerationRequest,
    DocumentationRequest,
    ChatRequest
]

AnyResponse = Union[
    CodeGenerationResponse,
    CodeCompletionResponse,
    CodeExplanationResponse,
    CodeRefactorResponse,
    CodeReviewResponse,
    BugFixResponse,
    TestGenerationResponse,
    DocumentationResponse,
    ChatResponse,
    HealthCheckResponse,
    ErrorResponse
]