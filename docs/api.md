# API Documentation

This document provides comprehensive information about the Cursor Pro Model REST API.

## Base URL

```
http://localhost:8000
```

## Authentication

Authentication is optional and can be enabled via configuration. When enabled, include the API key in the Authorization header:

```bash
Authorization: Bearer your-api-key
```

## Rate Limiting

- **Default**: 100 requests per hour per IP
- **Configurable**: Set via `RATE_LIMIT_REQUESTS` and `RATE_LIMIT_PERIOD`
- **Headers**: Rate limit info included in response headers

## Content Type

All requests should use `Content-Type: application/json`

## Response Format

All responses follow this structure:

```json
{
  "data": {},
  "error": null,
  "meta": {
    "request_id": "req-123",
    "timestamp": "2024-01-15T10:30:00Z",
    "version": "0.1.0"
  }
}
```

## Endpoints

### Health Check

Check the health and status of the service.

#### `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_name": "microsoft/DialoGPT-medium",
  "device": "cpu",
  "gpu_available": false,
  "memory_usage": 2048576,
  "uptime": 3600.5
}
```

**Status Codes:**
- `200`: Service is healthy
- `503`: Service is unhealthy

---

### Code Generation

Generate code from natural language descriptions.

#### `POST /generate`

**Request Body:**
```json
{
  "prompt": "Create a function that calculates fibonacci numbers",
  "language": "python",
  "max_tokens": 500,
  "temperature": 0.7,
  "context_files": ["utils.py", "math_helpers.py"],
  "style_preferences": {
    "indentation": "spaces",
    "line_length": 88
  }
}
```

**Parameters:**
- `prompt` (required): Description of the code to generate
- `language` (optional): Programming language (default: "python")
- `max_tokens` (optional): Maximum tokens to generate (default: 4096)
- `temperature` (optional): Sampling temperature 0.0-2.0 (default: 0.7)
- `context_files` (optional): Array of file paths for context
- `style_preferences` (optional): Code style preferences

**Response:**
```json
{
  "generated_code": "def fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
  "explanation": "This function calculates fibonacci numbers recursively",
  "suggestions": ["Consider adding memoization for better performance"],
  "language": "python",
  "metadata": {
    "tokens_generated": 45,
    "generation_time": 2.3
  }
}
```

**Status Codes:**
- `200`: Success
- `400`: Invalid request parameters
- `422`: Validation error
- `500`: Internal server error

---

### Streaming Code Generation

Generate code with real-time streaming responses.

#### `POST /generate/stream`

**Request Body:** Same as `/generate`

**Response:** Server-Sent Events (SSE) stream

```
data: {"chunk_id": 0, "content": "def fibonacci", "is_final": false}
data: {"chunk_id": 1, "content": "(n):", "is_final": false}
data: {"chunk_id": 2, "content": "", "is_final": true}
```

**Headers:**
- `Content-Type: text/event-stream`
- `Cache-Control: no-cache`

---

### Code Completion

Get code completion suggestions at a specific cursor position.

#### `POST /complete`

**Request Body:**
```json
{
  "code": "def calculate_area(radius):",
  "cursor_position": 25,
  "language": "python",
  "context_files": ["geometry.py"],
  "max_suggestions": 5
}
```

**Parameters:**
- `code` (required): Current code content
- `cursor_position` (required): Cursor position in the code
- `language` (optional): Programming language (default: "python")
- `context_files` (optional): Array of file paths for context
- `max_suggestions` (optional): Maximum suggestions (1-10, default: 5)

**Response:**
```json
{
  "suggestions": [
    "return math.pi * radius ** 2",
    "area = math.pi * radius * radius\n    return area",
    "import math\n    return math.pi * radius ** 2"
  ],
  "context_info": {
    "cursor_position": 25,
    "surrounding_context": "def calculate_area(radius):"
  },
  "metadata": {
    "suggestion_count": 3,
    "generation_time": 0.8
  }
}
```

---

### Code Explanation

Get natural language explanations of code functionality.

#### `POST /explain`

**Request Body:**
```json
{
  "code": "def quicksort(arr):\n    if len(arr) <= 1:\n        return arr\n    pivot = arr[len(arr) // 2]\n    left = [x for x in arr if x < pivot]\n    middle = [x for x in arr if x == pivot]\n    right = [x for x in arr if x > pivot]\n    return quicksort(left) + middle + quicksort(right)",
  "language": "python",
  "context_files": ["sorting.py"],
  "detail_level": "medium"
}
```

**Parameters:**
- `code` (required): Code to explain
- `language` (optional): Programming language (default: "python")
- `context_files` (optional): Array of file paths for context
- `detail_level` (optional): "basic", "medium", or "detailed" (default: "medium")

**Response:**
```json
{
  "explanation": "This function implements the quicksort algorithm, a divide-and-conquer sorting method...",
  "key_concepts": ["recursion", "divide-and-conquer", "sorting", "list comprehension"],
  "complexity_analysis": {
    "time_complexity": "O(n log n) average, O(n²) worst case",
    "space_complexity": "O(log n)"
  },
  "suggestions": [
    "Consider adding input validation",
    "Add type hints for better code documentation"
  ]
}
```

---

### Code Refactoring

Refactor code to improve quality, performance, or readability.

#### `POST /refactor`

**Request Body:**
```json
{
  "code": "def bad_function(x, y, z):\n    result = x + y\n    result = result * z\n    return result",
  "language": "python",
  "refactor_type": "optimize",
  "context_files": ["utils.py"]
}
```

**Parameters:**
- `code` (required): Code to refactor
- `language` (optional): Programming language (default: "python")
- `refactor_type` (required): Type of refactoring ("optimize", "simplify", "extract_function", "rename", "modernize")
- `context_files` (optional): Array of file paths for context

**Response:**
```json
{
  "refactored_code": "def calculate_result(x: float, y: float, z: float) -> float:\n    \"\"\"Calculate (x + y) * z.\"\"\"\n    return (x + y) * z",
  "changes_made": [
    "Added type hints",
    "Added docstring",
    "Simplified expression",
    "Improved function name"
  ],
  "improvement_metrics": {
    "readability": "+25%",
    "maintainability": "+30%",
    "performance": "+10%"
  },
  "explanation": "Refactored to improve readability and add proper documentation"
}
```

---

### Code Review

Perform automated code review and provide feedback.

#### `POST /review`

**Request Body:**
```json
{
  "code": "def process_data(data):\n    results = []\n    for item in data:\n        if item > 0:\n            results.append(item * 2)\n    return results",
  "language": "python",
  "context_files": ["data_processing.py"],
  "focus_areas": ["performance", "readability", "security"]
}
```

**Parameters:**
- `code` (required): Code to review
- `language` (optional): Programming language (default: "python")
- `context_files` (optional): Array of file paths for context
- `focus_areas` (optional): Array of review focus areas

**Response:**
```json
{
  "overall_score": 7.5,
  "issues": [
    {
      "type": "performance",
      "message": "Consider using list comprehension for better performance",
      "line": 3,
      "severity": "medium",
      "rule": "list-comprehension"
    }
  ],
  "suggestions": [
    "Use list comprehension: [item * 2 for item in data if item > 0]",
    "Add type hints for better documentation",
    "Consider adding input validation"
  ],
  "strengths": [
    "Clear variable names",
    "Simple and readable logic",
    "Proper return value"
  ],
  "summary": "Good basic implementation with room for optimization"
}
```

---

### Bug Fixing

Identify and fix bugs in code.

#### `POST /fix-bug`

**Request Body:**
```json
{
  "code": "def divide_numbers(a, b):\n    return a / b",
  "error_message": "ZeroDivisionError: division by zero",
  "language": "python",
  "context_files": ["math_utils.py"],
  "description": "Function crashes when b is zero"
}
```

**Parameters:**
- `code` (required): Code with bug
- `error_message` (optional): Error message if available
- `language` (optional): Programming language (default: "python")
- `context_files` (optional): Array of file paths for context
- `description` (optional): Description of the bug

**Response:**
```json
{
  "fixed_code": "def divide_numbers(a, b):\n    if b == 0:\n        raise ValueError(\"Cannot divide by zero\")\n    return a / b",
  "bug_description": "Function does not handle division by zero",
  "fix_explanation": "Added explicit check for zero divisor with informative error message",
  "prevention_tips": [
    "Always validate inputs that could cause errors",
    "Use proper exception handling",
    "Add unit tests for edge cases",
    "Consider using type hints"
  ]
}
```

---

### Test Generation

Generate unit tests for code.

#### `POST /generate-tests`

**Request Body:**
```json
{
  "code": "def calculate_bmi(weight, height):\n    return weight / (height ** 2)",
  "language": "python",
  "test_framework": "pytest",
  "context_files": ["health.py"],
  "coverage_type": "unit"
}
```

**Parameters:**
- `code` (required): Code to generate tests for
- `language` (optional): Programming language (default: "python")
- `test_framework` (optional): Testing framework (default: "pytest" for Python)
- `context_files` (optional): Array of file paths for context
- `coverage_type` (optional): "unit", "integration", or "both" (default: "unit")

**Response:**
```json
{
  "test_code": "import pytest\n\ndef test_calculate_bmi_normal():\n    assert abs(calculate_bmi(70, 1.75) - 22.86) < 0.01\n\ndef test_calculate_bmi_zero_height():\n    with pytest.raises(ZeroDivisionError):\n        calculate_bmi(70, 0)",
  "test_cases": [
    {"name": "test_calculate_bmi_normal", "description": "Tests normal BMI calculation"},
    {"name": "test_calculate_bmi_zero_height", "description": "Tests zero height edge case"}
  ],
  "coverage_info": {
    "estimated_coverage": "85%",
    "framework": "pytest"
  },
  "setup_instructions": "Install pytest and run: pytest test_file.py"
}
```

---

### Documentation Generation

Generate documentation for code.

#### `POST /generate-docs`

**Request Body:**
```json
{
  "code": "class DataProcessor:\n    def __init__(self, data_source):\n        self.data_source = data_source\n\n    def process(self, filters=None):\n        pass",
  "language": "python",
  "doc_type": "docstring",
  "context_files": ["processors.py"],
  "format": "markdown"
}
```

**Parameters:**
- `code` (required): Code to document
- `language` (optional): Programming language (default: "python")
- `doc_type` (required): "docstring", "readme", "api", or "comments"
- `context_files` (optional): Array of file paths for context
- `format` (optional): "markdown", "rst", or "plain" (default: "markdown")

**Response:**
```json
{
  "documentation": "# DataProcessor\n\nA class for processing data from various sources.\n\n## Methods\n\n### `__init__(data_source)`\nInitialize the processor with a data source.\n\n### `process(filters=None)`\nProcess the data with optional filters.",
  "format": "markdown",
  "sections": ["Overview", "Constructor", "Methods", "Examples"],
  "metadata": {
    "doc_type": "api",
    "language": "python",
    "word_count": 45
  }
}
```

---

### Chat Interface

Conversational interface for coding assistance.

#### `POST /chat`

**Request Body:**
```json
{
  "message": "How do I implement a binary search algorithm in Python?",
  "conversation_id": "conv-123",
  "context_files": ["search_algorithms.py"],
  "workspace_path": "/path/to/project",
  "task_type": "code_generation"
}
```

**Parameters:**
- `message` (required): User message
- `conversation_id` (optional): Conversation ID for context
- `context_files` (optional): Array of file paths for context
- `workspace_path` (optional): Path to workspace for context
- `task_type` (optional): Specific task type hint

**Response:**
```json
{
  "response": "Here's how to implement binary search in Python:\n\n```python\ndef binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    \n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    \n    return -1\n```\n\nThis algorithm works by...",
  "conversation_id": "conv-123",
  "suggestions": [
    "Would you like me to explain the time complexity?",
    "Should I show you how to test this function?",
    "Do you need a recursive version?"
  ],
  "code_blocks": [
    {
      "language": "python",
      "code": "def binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    \n    while left <= right:\n        mid = (left + right) // 2\n        if arr[mid] == target:\n            return mid\n        elif arr[mid] < target:\n            left = mid + 1\n        else:\n            right = mid - 1\n    \n    return -1"
    }
  ],
  "metadata": {
    "response_time": 1.5,
    "tokens_used": 245
  }
}
```

---

## File Operations

### Get File Content

#### `GET /api/v1/file/content?path=/path/to/file.py`

**Response:**
```json
{
  "path": "/path/to/file.py",
  "content": "def hello():\n    print('Hello, World!')",
  "language": "python",
  "size": 35
}
```

### Save File Content

#### `POST /api/v1/file/save`

**Request Body:**
```json
{
  "path": "/path/to/file.py",
  "content": "def hello():\n    print('Hello, World!')"
}
```

### Analyze File

#### `POST /api/v1/file/analyze`

**Request Body:**
```json
{
  "path": "/path/to/file.py"
}
```

**Response:**
```json
{
  "file_path": "/path/to/file.py",
  "language": "python",
  "symbols": [
    {
      "name": "hello",
      "type": "function",
      "line": 1,
      "column": 0
    }
  ],
  "dependencies": [],
  "issues": [],
  "metrics": {
    "total_lines": 2,
    "code_lines": 2,
    "comment_lines": 0
  }
}
```

---

## Workspace Operations

### Get Workspace Info

#### `GET /api/v1/workspace/info?path=/path/to/workspace`

**Response:**
```json
{
  "path": "/path/to/workspace",
  "files_count": 25,
  "languages": ["python", "javascript", "markdown"],
  "total_size": 524288,
  "last_modified": "2024-01-15T10:30:00Z"
}
```

### List Workspace Files

#### `GET /api/v1/workspace/files?path=/path/to/workspace&max_files=100`

**Response:**
```json
[
  {
    "path": "/path/to/workspace/main.py",
    "language": "python",
    "size": 1024,
    "last_modified": "2024-01-15T10:30:00Z"
  }
]
```

---

## System Information

### Get Supported Languages

#### `GET /api/v1/languages`

**Response:**
```json
{
  "languages": ["python", "javascript", "typescript", "java", "cpp", "rust", "go"],
  "parsers": ["python", "py"]
}
```

### Get Supported Tasks

#### `GET /api/v1/tasks`

**Response:**
```json
{
  "tasks": [
    "code_generation",
    "code_completion",
    "code_explanation",
    "code_refactor",
    "code_review",
    "bug_fix",
    "test_generation",
    "documentation"
  ]
}
```

---

## Error Responses

All error responses follow this format:

```json
{
  "error": "validation_error",
  "message": "Invalid parameter value",
  "details": {
    "field": "temperature",
    "value": 3.0,
    "constraint": "must be between 0.0 and 2.0"
  },
  "code": 422
}
```

### Common Error Codes

- `400`: Bad Request - Invalid request format
- `401`: Unauthorized - Authentication required
- `403`: Forbidden - Insufficient permissions
- `404`: Not Found - Resource not found
- `422`: Validation Error - Invalid parameter values
- `429`: Too Many Requests - Rate limit exceeded
- `500`: Internal Server Error - Server error
- `503`: Service Unavailable - Service temporarily unavailable

---

## Rate Limiting

Rate limit information is included in response headers:

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1642248600
```

## Versioning

The API uses URL versioning:
- Current version: `v1`
- Base path: `/api/v1/`
- Future versions will be available at `/api/v2/`, etc.

## SDKs and Client Libraries

- **Python**: `pip install cursor-pro-client`
- **JavaScript**: `npm install cursor-pro-client`
- **Go**: Available on GitHub
- **Rust**: Available on crates.io

## Examples

### Python Client Example

```python
from cursor_pro_client import CursorProClient

client = CursorProClient("http://localhost:8000")

# Generate code
result = client.generate_code(
    prompt="Create a REST API endpoint",
    language="python"
)

print(result.generated_code)
```

### JavaScript Client Example

```javascript
import { CursorProClient } from 'cursor-pro-client';

const client = new CursorProClient('http://localhost:8000');

// Generate code
const result = await client.generateCode({
  prompt: 'Create a React component',
  language: 'javascript'
});

console.log(result.generatedCode);
```

### cURL Examples

```bash
# Generate code
curl -X POST "http://localhost:8000/generate" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Create a sorting function", "language": "python"}'

# Complete code
curl -X POST "http://localhost:8000/complete" \
  -H "Content-Type: application/json" \
  -d '{"code": "def sort_array(", "cursor_position": 15, "language": "python"}'

# Chat
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I optimize this code?"}'
```