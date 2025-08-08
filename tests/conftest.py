"""Pytest configuration and shared fixtures."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock

from cursor_pro.core.config import Config


@pytest.fixture(scope="session")
def temp_workspace():
    """Create a temporary workspace for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    
    # Create some sample files
    (temp_dir / "main.py").write_text("""
def main():
    print("Hello, World!")

if __name__ == "__main__":
    main()
""")
    
    (temp_dir / "utils.py").write_text("""
from typing import List

def process_items(items: List[str]) -> List[str]:
    return [item.upper() for item in items]

class DataProcessor:
    def __init__(self):
        self.data = []
    
    def add_item(self, item: str):
        self.data.append(item)
""")
    
    (temp_dir / "test_file.js").write_text("""
function greet(name) {
    return `Hello, ${name}!`;
}

class Calculator {
    add(a, b) {
        return a + b;
    }
}
""")
    
    (temp_dir / "README.md").write_text("""
# Test Project

This is a test project for Cursor Pro.
""")
    
    # Create subdirectory
    sub_dir = temp_dir / "subdir"
    sub_dir.mkdir()
    (sub_dir / "module.py").write_text("""
def helper_function():
    return "helper"
""")
    
    yield temp_dir
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_python_code():
    """Sample Python code for testing."""
    return """
import os
import sys
from pathlib import Path
from typing import List, Dict, Optional

class Calculator:
    '''A simple calculator class.'''
    
    def __init__(self):
        self.history = []
    
    def add(self, a: float, b: float) -> float:
        '''Add two numbers.'''
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
    
    def divide(self, a: float, b: float) -> float:
        '''Divide two numbers.'''
        if b == 0:
            raise ValueError("Cannot divide by zero")
        result = a / b
        self.history.append(f"{a} / {b} = {result}")
        return result

def main():
    calc = Calculator()
    result = calc.add(5, 3)
    print(f"Result: {result}")

if __name__ == "__main__":
    main()
"""


@pytest.fixture
def sample_javascript_code():
    """Sample JavaScript code for testing."""
    return """
const fs = require('fs');
const path = require('path');

class FileManager {
    constructor() {
        this.files = [];
    }
    
    async readFile(filename) {
        try {
            const content = await fs.promises.readFile(filename, 'utf8');
            this.files.push({ name: filename, content });
            return content;
        } catch (error) {
            console.error(`Error reading file: ${error.message}`);
            throw error;
        }
    }
    
    getFileCount() {
        return this.files.length;
    }
}

function processData(data) {
    return data.map(item => item.toUpperCase());
}

module.exports = { FileManager, processData };
"""


@pytest.fixture
def test_config():
    """Test configuration with minimal settings."""
    return Config(
        model=Config.ModelConfig(
            name="test-model",
            cache_dir="./test_cache",
            max_tokens=256,
            temperature=0.5,
            device="cpu",
            gpu_enabled=False
        ),
        code_analysis=Config.CodeAnalysisConfig(
            supported_languages=["python", "javascript"],
            max_file_size=1024 * 1024,  # 1MB
            max_context_files=20
        ),
        api=Config.APIConfig(
            host="localhost",
            port=8000,
            api_key_required=False
        )
    )


@pytest.fixture
def mock_tokenizer():
    """Mock tokenizer for testing."""
    tokenizer = Mock()
    tokenizer.encode.return_value = Mock()
    tokenizer.encode.return_value.to.return_value = "encoded_input"
    tokenizer.decode.return_value = "decoded_output"
    tokenizer.pad_token = "<pad>"
    tokenizer.eos_token = "<eos>"
    tokenizer.pad_token_id = 0
    tokenizer.eos_token_id = 1
    return tokenizer


@pytest.fixture
def mock_ai_model():
    """Mock AI model for testing."""
    model = Mock()
    model.to.return_value = model
    
    # Mock generation output
    mock_output = Mock()
    mock_output.sequences = [["input_tokens", "output_tokens"]]
    model.generate.return_value = mock_output
    
    return model


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Add unit marker to all tests by default
        if not any(marker.name in ["integration", "slow"] for marker in item.iter_markers()):
            item.add_marker(pytest.mark.unit)


# Test data for parametrized tests
SAMPLE_CODE_SNIPPETS = [
    ("python", "def hello(): return 'Hello, World!'"),
    ("javascript", "function hello() { return 'Hello, World!'; }"),
    ("python", "class Test: pass"),
    ("javascript", "class Test {}"),
]

SAMPLE_IMPORT_STATEMENTS = [
    ("python", "import os", ["os"]),
    ("python", "from sys import path", ["path"]),
    ("javascript", "const fs = require('fs');", ["fs"]),
    ("javascript", "import { readFile } from 'fs';", ["readFile"]),
]


@pytest.fixture(params=SAMPLE_CODE_SNIPPETS)
def code_snippet(request):
    """Parametrized fixture for code snippets."""
    language, code = request.param
    return {"language": language, "code": code}


@pytest.fixture(params=SAMPLE_IMPORT_STATEMENTS)
def import_statement(request):
    """Parametrized fixture for import statements."""
    language, code, expected = request.param
    return {"language": language, "code": code, "expected": expected}