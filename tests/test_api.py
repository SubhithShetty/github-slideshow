"""Tests for API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch, AsyncMock

from cursor_pro.api.server import create_app
from cursor_pro.api.models import *


@pytest.fixture
def test_app():
    """Create test FastAPI application."""
    return create_app()


@pytest.fixture
def client(test_app):
    """Create test client."""
    return TestClient(test_app)


@pytest.fixture
def mock_api_instance():
    """Mock API instance for testing."""
    mock_api = Mock()
    mock_model = Mock()
    
    # Mock model methods
    mock_model.generate_code = AsyncMock(return_value="Generated code here")
    mock_model.complete_code = AsyncMock(return_value=["suggestion1", "suggestion2"])
    mock_model.explain_code = AsyncMock(return_value="This code does something")
    mock_model.health_check = AsyncMock(return_value={
        "status": "healthy",
        "model_loaded": True,
        "model_name": "test-model",
        "device": "cpu",
        "gpu_available": False,
        "memory_usage": 1024
    })
    
    mock_api.get_model.return_value = mock_model
    mock_api.get_uptime.return_value = 123.45
    mock_api.create_conversation_id.return_value = "test-conversation-123"
    mock_api.get_conversation.return_value = {"messages": []}
    mock_api.update_conversation = Mock()
    
    return mock_api


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    @patch('cursor_pro.api.server.get_api')
    def test_health_check_healthy(self, mock_get_api, client, mock_api_instance):
        """Test health check when service is healthy."""
        mock_get_api.return_value = mock_api_instance
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["model_loaded"] is True
        assert data["model_name"] == "test-model"
        assert data["device"] == "cpu"
        assert "uptime" in data
    
    @patch('cursor_pro.api.server.get_api')
    def test_health_check_unhealthy(self, mock_get_api, client, mock_api_instance):
        """Test health check when service is unhealthy."""
        mock_api_instance.get_model.side_effect = Exception("Model error")
        mock_get_api.return_value = mock_api_instance
        
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "unhealthy"


class TestCodeGenerationEndpoint:
    """Test code generation endpoint."""
    
    @patch('cursor_pro.api.server.get_api')
    def test_generate_code_success(self, mock_get_api, client, mock_api_instance):
        """Test successful code generation."""
        mock_get_api.return_value = mock_api_instance
        
        request_data = {
            "prompt": "Create a hello world function",
            "language": "python",
            "max_tokens": 100
        }
        
        response = client.post("/generate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "generated_code" in data
        assert "language" in data
        assert data["language"] == "python"
        
        # Verify model was called correctly
        mock_api_instance.get_model().generate_code.assert_called_once_with(
            prompt="Create a hello world function",
            language="python",
            max_tokens=100,
            temperature=None,
            context_files=None
        )
    
    @patch('cursor_pro.api.server.get_api')
    def test_generate_code_with_context(self, mock_get_api, client, mock_api_instance):
        """Test code generation with context files."""
        mock_get_api.return_value = mock_api_instance
        
        request_data = {
            "prompt": "Create a function",
            "language": "python",
            "context_files": ["file1.py", "file2.py"],
            "temperature": 0.8
        }
        
        response = client.post("/generate", json=request_data)
        
        assert response.status_code == 200
        mock_api_instance.get_model().generate_code.assert_called_once_with(
            prompt="Create a function",
            language="python",
            max_tokens=None,
            temperature=0.8,
            context_files=["file1.py", "file2.py"]
        )
    
    @patch('cursor_pro.api.server.get_api')
    def test_generate_code_model_error(self, mock_get_api, client, mock_api_instance):
        """Test code generation with model error."""
        mock_api_instance.get_model().generate_code.side_effect = Exception("Model error")
        mock_get_api.return_value = mock_api_instance
        
        request_data = {
            "prompt": "Create a function",
            "language": "python"
        }
        
        response = client.post("/generate", json=request_data)
        
        assert response.status_code == 500
        assert "Model error" in response.json()["detail"]


class TestCodeCompletionEndpoint:
    """Test code completion endpoint."""
    
    @patch('cursor_pro.api.server.get_api')
    def test_complete_code_success(self, mock_get_api, client, mock_api_instance):
        """Test successful code completion."""
        mock_get_api.return_value = mock_api_instance
        
        request_data = {
            "code": "def hello_world():",
            "cursor_position": 18,
            "language": "python",
            "max_suggestions": 3
        }
        
        response = client.post("/complete", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "suggestions" in data
        assert len(data["suggestions"]) <= 3
        assert "context_info" in data
    
    @patch('cursor_pro.api.server.get_api')
    def test_complete_code_with_defaults(self, mock_get_api, client, mock_api_instance):
        """Test code completion with default values."""
        mock_get_api.return_value = mock_api_instance
        
        request_data = {
            "code": "def test():",
            "cursor_position": 10
        }
        
        response = client.post("/complete", json=request_data)
        
        assert response.status_code == 200
        # Should use default max_suggestions of 5
        assert len(response.json()["suggestions"]) <= 5


class TestCodeExplanationEndpoint:
    """Test code explanation endpoint."""
    
    @patch('cursor_pro.api.server.get_api')
    def test_explain_code_success(self, mock_get_api, client, mock_api_instance):
        """Test successful code explanation."""
        mock_get_api.return_value = mock_api_instance
        
        request_data = {
            "code": "def add(a, b): return a + b",
            "language": "python"
        }
        
        response = client.post("/explain", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "explanation" in data
        assert "key_concepts" in data
        assert "suggestions" in data


class TestChatEndpoint:
    """Test chat endpoint."""
    
    @patch('cursor_pro.api.server.get_api')
    def test_chat_new_conversation(self, mock_get_api, client, mock_api_instance):
        """Test chat with new conversation."""
        mock_get_api.return_value = mock_api_instance
        
        request_data = {
            "message": "How do I create a function in Python?"
        }
        
        response = client.post("/chat", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "conversation_id" in data
        assert "suggestions" in data
        
        # Should create new conversation ID
        mock_api_instance.create_conversation_id.assert_called_once()
    
    @patch('cursor_pro.api.server.get_api')
    def test_chat_existing_conversation(self, mock_get_api, client, mock_api_instance):
        """Test chat with existing conversation."""
        mock_get_api.return_value = mock_api_instance
        mock_api_instance.get_conversation.return_value = {
            "messages": [
                {"role": "user", "content": "Previous message"},
                {"role": "assistant", "content": "Previous response"}
            ]
        }
        
        request_data = {
            "message": "Follow up question",
            "conversation_id": "existing-123"
        }
        
        response = client.post("/chat", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["conversation_id"] == "existing-123"
        
        # Should not create new conversation ID
        mock_api_instance.create_conversation_id.assert_not_called()


class TestRequestValidation:
    """Test request validation."""
    
    def test_generate_code_invalid_temperature(self, client):
        """Test validation of temperature parameter."""
        request_data = {
            "prompt": "Test",
            "temperature": 3.0  # Invalid: > 2.0
        }
        
        response = client.post("/generate", json=request_data)
        assert response.status_code == 422  # Validation error
    
    def test_generate_code_missing_prompt(self, client):
        """Test validation of required prompt field."""
        request_data = {
            "language": "python"
            # Missing required "prompt" field
        }
        
        response = client.post("/generate", json=request_data)
        assert response.status_code == 422  # Validation error
    
    def test_complete_code_invalid_max_suggestions(self, client):
        """Test validation of max_suggestions parameter."""
        request_data = {
            "code": "test",
            "cursor_position": 0,
            "max_suggestions": 15  # Invalid: > 10
        }
        
        response = client.post("/complete", json=request_data)
        assert response.status_code == 422  # Validation error


class TestStreamingEndpoint:
    """Test streaming code generation endpoint."""
    
    @patch('cursor_pro.api.server.get_api')
    def test_stream_generate_code(self, mock_get_api, client, mock_api_instance):
        """Test streaming code generation."""
        # Mock async generator
        async def mock_stream():
            yield "chunk1"
            yield "chunk2"
            yield "chunk3"
        
        mock_api_instance.get_model().stream_generate_code.return_value = mock_stream()
        mock_get_api.return_value = mock_api_instance
        
        request_data = {
            "prompt": "Create a function",
            "language": "python"
        }
        
        response = client.post("/generate/stream", json=request_data)
        
        assert response.status_code == 200
        assert response.headers["content-type"] == "text/plain; charset=utf-8"
        
        # Check that streaming response contains data
        content = response.content.decode()
        assert "chunk_id" in content
        assert "content" in content


@pytest.mark.parametrize("endpoint,method,data", [
    ("/generate", "POST", {"prompt": "test", "language": "python"}),
    ("/complete", "POST", {"code": "test", "cursor_position": 0}),
    ("/explain", "POST", {"code": "test", "language": "python"}),
    ("/chat", "POST", {"message": "test"}),
])
def test_endpoints_require_model(client, endpoint, method, data):
    """Test that endpoints handle missing model gracefully."""
    # Without mocking get_api, should get service unavailable
    if method == "POST":
        response = client.post(endpoint, json=data)
    else:
        response = client.get(endpoint)
    
    # Should handle the error gracefully, not crash
    assert response.status_code in [500, 503]  # Internal server error or service unavailable


class TestAuthenticationFlow:
    """Test authentication when enabled."""
    
    # Note: These tests would need to be implemented when 
    # authentication is properly configured
    
    def test_no_auth_required_by_default(self, client):
        """Test that authentication is not required by default."""
        # Health check should work without auth
        response = client.get("/health")
        # Should not get 401 Unauthorized
        assert response.status_code != 401