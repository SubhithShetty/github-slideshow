"""Tests for the core CursorProModel functionality."""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path

from cursor_pro.core.config import Config
from cursor_pro.core.model import CursorProModel


@pytest.fixture
def test_config():
    """Create a test configuration."""
    return Config(
        model=Config.ModelConfig(
            name="microsoft/DialoGPT-medium",
            cache_dir="./test_models",
            max_tokens=512,
            temperature=0.7,
            device="cpu",
            gpu_enabled=False
        ),
        code_analysis=Config.CodeAnalysisConfig(
            supported_languages=["python", "javascript"],
            max_file_size=1024,
            max_context_files=10
        )
    )


@pytest.fixture
def mock_model(test_config):
    """Create a mock model instance."""
    return CursorProModel(test_config)


class TestCursorProModel:
    """Test cases for CursorProModel."""
    
    def test_model_initialization(self, test_config):
        """Test model initialization."""
        model = CursorProModel(test_config)
        
        assert model.config == test_config
        assert model.model_config == test_config.model
        assert not model._is_loaded
        assert model._device in ["cpu", "cuda", "mps"]
    
    @pytest.mark.asyncio
    async def test_model_device_selection(self, mock_model):
        """Test device selection logic."""
        device = mock_model._get_device()
        assert device in ["cpu", "cuda", "mps"]
    
    @pytest.mark.asyncio
    @patch('cursor_pro.core.model.AutoTokenizer')
    @patch('cursor_pro.core.model.AutoModelForCausalLM')
    async def test_model_loading(self, mock_model_class, mock_tokenizer_class, mock_model):
        """Test model loading process."""
        # Mock the tokenizer and model
        mock_tokenizer = Mock()
        mock_tokenizer.pad_token = None
        mock_tokenizer.eos_token = "<eos>"
        mock_tokenizer.pad_token_id = 0
        mock_tokenizer.eos_token_id = 1
        
        mock_ai_model = Mock()
        mock_ai_model.to = Mock(return_value=mock_ai_model)
        
        mock_tokenizer_class.from_pretrained.return_value = mock_tokenizer
        mock_model_class.from_pretrained.return_value = mock_ai_model
        
        # Test loading
        await mock_model.load_model()
        
        assert mock_model._is_loaded
        assert mock_model.tokenizer == mock_tokenizer
        assert mock_model.model == mock_ai_model
        assert mock_tokenizer.pad_token == "<eos>"
    
    @pytest.mark.asyncio
    async def test_model_unloading(self, mock_model):
        """Test model unloading."""
        # Simulate loaded state
        mock_model._is_loaded = True
        mock_model.model = Mock()
        mock_model.tokenizer = Mock()
        
        await mock_model.unload_model()
        
        assert not mock_model._is_loaded
        assert mock_model.model is None
        assert mock_model.tokenizer is None
    
    def test_ensure_loaded_when_not_loaded(self, mock_model):
        """Test ensure_loaded raises error when model not loaded."""
        with pytest.raises(RuntimeError, match="Model not loaded"):
            mock_model._ensure_loaded()
    
    def test_ensure_loaded_when_loaded(self, mock_model):
        """Test ensure_loaded passes when model is loaded."""
        mock_model._is_loaded = True
        # Should not raise
        mock_model._ensure_loaded()
    
    @pytest.mark.asyncio
    @patch('cursor_pro.core.model.CursorProModel._ensure_loaded')
    async def test_generate_code(self, mock_ensure_loaded, mock_model):
        """Test code generation."""
        # Mock dependencies
        mock_model._is_loaded = True
        mock_model.context_manager = AsyncMock()
        mock_model.context_manager.build_context.return_value = {
            "summary": "Test context",
            "files": []
        }
        
        mock_tokenizer = Mock()
        mock_tokenizer.encode.return_value = Mock()
        mock_tokenizer.encode.return_value.to.return_value = "encoded_input"
        mock_tokenizer.decode.return_value = "Generated code here"
        
        mock_ai_model = Mock()
        mock_outputs = Mock()
        mock_outputs.sequences = [["input_tokens", "generated_tokens"]]
        mock_ai_model.generate.return_value = mock_outputs
        
        mock_model.tokenizer = mock_tokenizer
        mock_model.model = mock_ai_model
        mock_model._device = "cpu"
        
        # Test generation
        result = await mock_model.generate_code(
            prompt="Create a hello world function",
            language="python"
        )
        
        assert isinstance(result, str)
        mock_model.context_manager.build_context.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_health_check(self, mock_model):
        """Test health check functionality."""
        mock_model._is_loaded = True
        mock_model.model_config.name = "test-model"
        mock_model._device = "cpu"
        
        health = await mock_model.health_check()
        
        assert health["status"] == "healthy"
        assert health["model_loaded"] is True
        assert health["model_name"] == "test-model"
        assert health["device"] == "cpu"
        assert "gpu_available" in health
        assert "memory_usage" in health
    
    def test_format_prompt(self, mock_model):
        """Test prompt formatting."""
        context = {
            "summary": "Test summary",
            "files": [{"name": "test.py"}]
        }
        
        formatted = mock_model._format_prompt("Test prompt", context, "python")
        
        assert "Test prompt" in formatted
        assert "python" in formatted
        assert "Test summary" in formatted
        assert "<system>" in formatted
        assert "<user>" in formatted
    
    def test_extract_code_with_code_blocks(self, mock_model):
        """Test code extraction from formatted text."""
        text_with_code = """
        Here's the code:
        ```python
        def hello():
            print("Hello, World!")
        ```
        """
        
        result = mock_model._extract_code(text_with_code, "python")
        assert "def hello():" in result
        assert "print(\"Hello, World!\")" in result
    
    def test_extract_code_without_blocks(self, mock_model):
        """Test code extraction from plain text."""
        plain_text = "def hello(): print('Hello')"
        
        result = mock_model._extract_code(plain_text, "python")
        assert result == plain_text
    
    def test_extract_completions(self, mock_model):
        """Test completion extraction."""
        generated_text = """
        suggestion1()
        suggestion2()
        # This is a comment
        suggestion3()
        """
        
        completions = mock_model._extract_completions(generated_text, "prefix")
        
        assert len(completions) >= 2
        assert "suggestion1()" in completions
        assert "suggestion2()" in completions
        # Comments should be filtered out
        assert not any("comment" in comp.lower() for comp in completions)


@pytest.mark.integration
class TestCursorProModelIntegration:
    """Integration tests for CursorProModel."""
    
    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_full_model_workflow(self, test_config):
        """Test complete model workflow (requires actual model)."""
        # Skip if running in CI or if models not available
        pytest.skip("Integration test - requires actual model files")
        
        model = CursorProModel(test_config)
        
        try:
            await model.load_model()
            
            # Test generation
            result = await model.generate_code(
                prompt="Create a simple function that adds two numbers",
                language="python",
                max_tokens=100
            )
            
            assert isinstance(result, str)
            assert len(result) > 0
            
            # Test completion
            completions = await model.complete_code(
                code="def add_numbers(a, b):",
                cursor_position=20,
                language="python"
            )
            
            assert isinstance(completions, list)
            
            # Test explanation
            explanation = await model.explain_code(
                code="def add(x, y): return x + y",
                language="python"
            )
            
            assert isinstance(explanation, str)
            assert len(explanation) > 0
            
        finally:
            await model.unload_model()


class TestModelErrorHandling:
    """Test error handling in CursorProModel."""
    
    @pytest.mark.asyncio
    async def test_load_model_failure(self, mock_model):
        """Test handling of model loading failures."""
        with patch('cursor_pro.core.model.AutoTokenizer') as mock_tokenizer:
            mock_tokenizer.from_pretrained.side_effect = Exception("Loading failed")
            
            with pytest.raises(Exception, match="Loading failed"):
                await mock_model.load_model()
            
            assert not mock_model._is_loaded
    
    @pytest.mark.asyncio
    async def test_generate_code_without_loaded_model(self, mock_model):
        """Test code generation without loaded model."""
        with pytest.raises(RuntimeError, match="Model not loaded"):
            await mock_model.generate_code("test prompt")
    
    @pytest.mark.asyncio
    async def test_context_build_failure(self, mock_model):
        """Test handling of context building failures."""
        mock_model._is_loaded = True
        mock_model.context_manager = AsyncMock()
        mock_model.context_manager.build_context.side_effect = Exception("Context failed")
        
        with pytest.raises(Exception, match="Context failed"):
            await mock_model.generate_code("test prompt")


@pytest.mark.parametrize("device,expected", [
    ("cpu", "cpu"),
    ("cuda", "cuda"),  # Will fall back to cpu if CUDA not available
    ("mps", "mps"),    # Will fall back to cpu if MPS not available
])
def test_device_configuration(test_config, device, expected):
    """Test device configuration scenarios."""
    test_config.model.device = device
    model = CursorProModel(test_config)
    
    # Device selection logic should handle unavailable devices gracefully
    selected_device = model._get_device()
    assert selected_device in ["cpu", "cuda", "mps"]


def test_model_config_validation():
    """Test model configuration validation."""
    # Test invalid temperature
    with pytest.raises(ValueError, match="Temperature must be between 0 and 2"):
        Config.ModelConfig(temperature=-1)
    
    with pytest.raises(ValueError, match="Temperature must be between 0 and 2"):
        Config.ModelConfig(temperature=3)
    
    # Test invalid top_p
    with pytest.raises(ValueError, match="Top-p must be between 0 and 1"):
        Config.ModelConfig(top_p=-0.1)
    
    with pytest.raises(ValueError, match="Top-p must be between 0 and 1"):
        Config.ModelConfig(top_p=1.1)