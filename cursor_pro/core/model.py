"""Main Cursor Pro Model implementation."""

import asyncio
import logging
import torch
from typing import Dict, List, Optional, Tuple, Union, AsyncGenerator
from pathlib import Path
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    GenerationConfig,
    pipeline,
    TextStreamer
)
from .config import Config, ModelConfig
from .context import ContextManager
from .tokenizer import CodeTokenizer

logger = logging.getLogger(__name__)


class CursorProModel:
    """
    Main Cursor Pro Model class for AI-powered coding assistance.
    
    This class handles:
    - Model loading and initialization
    - Code understanding and analysis
    - Code generation and completion
    - Context management
    - Multi-turn conversations
    """
    
    def __init__(self, config: Config):
        """Initialize the Cursor Pro Model."""
        self.config = config
        self.model_config = config.model
        
        # Model components
        self.tokenizer: Optional[AutoTokenizer] = None
        self.model: Optional[AutoModelForCausalLM] = None
        self.generation_config: Optional[GenerationConfig] = None
        
        # Supporting components
        self.context_manager = ContextManager(config)
        self.code_tokenizer = CodeTokenizer(config)
        
        # State
        self._is_loaded = False
        self._device = self._get_device()
        
        logger.info(f"Initialized CursorProModel with device: {self._device}")
    
    def _get_device(self) -> str:
        """Determine the best device to use."""
        if self.model_config.gpu_enabled and torch.cuda.is_available():
            return "cuda"
        elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
            return "mps"
        else:
            return "cpu"
    
    async def load_model(self) -> None:
        """Load the AI model and tokenizer."""
        if self._is_loaded:
            logger.warning("Model already loaded")
            return
            
        logger.info(f"Loading model: {self.model_config.name}")
        
        try:
            # Load tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(
                self.model_config.name,
                cache_dir=self.model_config.cache_dir,
                trust_remote_code=True
            )
            
            # Set pad token if not present
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token
            
            # Load model
            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_config.name,
                cache_dir=self.model_config.cache_dir,
                torch_dtype=torch.float16 if self._device != "cpu" else torch.float32,
                device_map="auto" if self._device == "cuda" else None,
                trust_remote_code=True
            )
            
            # Move to device if not using device_map
            if self._device != "cuda":
                self.model = self.model.to(self._device)
            
            # Setup generation config
            self.generation_config = GenerationConfig(
                max_new_tokens=self.model_config.max_tokens,
                temperature=self.model_config.temperature,
                top_p=self.model_config.top_p,
                do_sample=True,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id,
            )
            
            self._is_loaded = True
            logger.info("Model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise
    
    async def unload_model(self) -> None:
        """Unload the model to free memory."""
        if not self._is_loaded:
            return
            
        if self.model is not None:
            del self.model
            self.model = None
            
        if self.tokenizer is not None:
            del self.tokenizer
            self.tokenizer = None
            
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            
        self._is_loaded = False
        logger.info("Model unloaded")
    
    def _ensure_loaded(self) -> None:
        """Ensure the model is loaded."""
        if not self._is_loaded:
            raise RuntimeError("Model not loaded. Call load_model() first.")
    
    async def generate_code(
        self,
        prompt: str,
        language: str = "python",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        context_files: Optional[List[str]] = None
    ) -> str:
        """
        Generate code based on a prompt.
        
        Args:
            prompt: The code generation prompt
            language: Programming language
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            context_files: Additional context files
            
        Returns:
            Generated code string
        """
        self._ensure_loaded()
        
        # Build context
        context = await self.context_manager.build_context(
            prompt=prompt,
            language=language,
            files=context_files or []
        )
        
        # Prepare input
        input_text = self._format_prompt(prompt, context, language)
        inputs = self.tokenizer.encode(input_text, return_tensors="pt").to(self._device)
        
        # Generate
        generation_config = GenerationConfig(
            max_new_tokens=max_tokens or self.model_config.max_tokens,
            temperature=temperature or self.model_config.temperature,
            top_p=self.model_config.top_p,
            do_sample=True,
            pad_token_id=self.tokenizer.pad_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
        )
        
        with torch.no_grad():
            outputs = self.model.generate(
                inputs,
                generation_config=generation_config,
                return_dict_in_generate=True,
                output_scores=True
            )
        
        # Decode response
        generated_tokens = outputs.sequences[0][inputs.shape[1]:]
        generated_text = self.tokenizer.decode(generated_tokens, skip_special_tokens=True)
        
        return self._extract_code(generated_text, language)
    
    async def stream_generate_code(
        self,
        prompt: str,
        language: str = "python",
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        context_files: Optional[List[str]] = None
    ) -> AsyncGenerator[str, None]:
        """
        Stream code generation for real-time updates.
        
        Args:
            prompt: The code generation prompt
            language: Programming language
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            context_files: Additional context files
            
        Yields:
            Generated code chunks
        """
        self._ensure_loaded()
        
        # Build context
        context = await self.context_manager.build_context(
            prompt=prompt,
            language=language,
            files=context_files or []
        )
        
        # Prepare input
        input_text = self._format_prompt(prompt, context, language)
        inputs = self.tokenizer.encode(input_text, return_tensors="pt").to(self._device)
        
        # Setup streaming
        class AsyncTextStreamer:
            def __init__(self, tokenizer, skip_prompt=True):
                self.tokenizer = tokenizer
                self.skip_prompt = skip_prompt
                self.buffer = []
                
            def put(self, value):
                if self.skip_prompt and len(self.buffer) == 0:
                    # Skip the prompt tokens
                    return
                self.buffer.append(value.item())
                
            def end(self):
                pass
                
            def get_buffer(self):
                return self.buffer
        
        streamer = AsyncTextStreamer(self.tokenizer)
        
        # Generate with streaming
        generation_config = GenerationConfig(
            max_new_tokens=max_tokens or self.model_config.max_tokens,
            temperature=temperature or self.model_config.temperature,
            top_p=self.model_config.top_p,
            do_sample=True,
            pad_token_id=self.tokenizer.pad_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
        )
        
        # Run generation in thread
        def generate():
            with torch.no_grad():
                self.model.generate(
                    inputs,
                    generation_config=generation_config,
                    streamer=streamer
                )
        
        # Start generation
        generation_task = asyncio.create_task(
            asyncio.get_event_loop().run_in_executor(None, generate)
        )
        
        # Stream tokens as they're generated
        last_length = 0
        while not generation_task.done():
            await asyncio.sleep(0.01)  # Small delay
            buffer = streamer.get_buffer()
            if len(buffer) > last_length:
                new_tokens = buffer[last_length:]
                chunk = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
                if chunk:
                    yield chunk
                last_length = len(buffer)
        
        # Final check for any remaining tokens
        await generation_task
        buffer = streamer.get_buffer()
        if len(buffer) > last_length:
            new_tokens = buffer[last_length:]
            chunk = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
            if chunk:
                yield chunk
    
    async def complete_code(
        self,
        code: str,
        cursor_position: int,
        language: str = "python",
        context_files: Optional[List[str]] = None
    ) -> List[str]:
        """
        Provide code completions at cursor position.
        
        Args:
            code: Current code content
            cursor_position: Cursor position in the code
            language: Programming language
            context_files: Additional context files
            
        Returns:
            List of completion suggestions
        """
        self._ensure_loaded()
        
        # Extract context around cursor
        before_cursor = code[:cursor_position]
        after_cursor = code[cursor_position:]
        
        # Build completion prompt
        prompt = f"Complete the following {language} code:\n\n{before_cursor}<CURSOR>{after_cursor}"
        
        # Generate completions
        generated = await self.generate_code(
            prompt=prompt,
            language=language,
            max_tokens=min(512, self.model_config.max_tokens),
            context_files=context_files
        )
        
        # Extract and format completions
        completions = self._extract_completions(generated, before_cursor)
        return completions[:5]  # Return top 5 completions
    
    async def explain_code(
        self,
        code: str,
        language: str = "python",
        context_files: Optional[List[str]] = None
    ) -> str:
        """
        Generate an explanation for the given code.
        
        Args:
            code: Code to explain
            language: Programming language
            context_files: Additional context files
            
        Returns:
            Code explanation
        """
        self._ensure_loaded()
        
        prompt = f"Explain the following {language} code in detail:\n\n```{language}\n{code}\n```"
        
        explanation = await self.generate_code(
            prompt=prompt,
            language="markdown",  # Generate explanation in markdown
            max_tokens=min(1024, self.model_config.max_tokens),
            context_files=context_files
        )
        
        return explanation
    
    def _format_prompt(self, prompt: str, context: Dict, language: str) -> str:
        """Format the prompt with context and language information."""
        formatted_prompt = f"""<system>
You are Cursor Pro, an AI coding assistant. You help developers write, understand, and debug code.
Language: {language}
Context files: {len(context.get('files', []))}
</system>

<context>
{context.get('summary', '')}
</context>

<user>
{prompt}
</user>

<assistant>
"""
        return formatted_prompt
    
    def _extract_code(self, generated_text: str, language: str) -> str:
        """Extract code from generated text."""
        # Remove common prefixes and clean up
        text = generated_text.strip()
        
        # Look for code blocks
        if f"```{language}" in text:
            start = text.find(f"```{language}") + len(f"```{language}")
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()
        
        # Look for generic code blocks
        if "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end != -1:
                return text[start:end].strip()
        
        return text
    
    def _extract_completions(self, generated_text: str, prefix: str) -> List[str]:
        """Extract completion suggestions from generated text."""
        # Simple implementation - can be enhanced
        lines = generated_text.split('\n')
        completions = []
        
        for line in lines[:5]:  # Take first 5 lines
            line = line.strip()
            if line and not line.startswith('#'):  # Skip comments
                completions.append(line)
        
        return completions
    
    async def health_check(self) -> Dict[str, Union[str, bool, int]]:
        """Check model health and status."""
        return {
            "status": "healthy" if self._is_loaded else "not_loaded",
            "model_loaded": self._is_loaded,
            "model_name": self.model_config.name,
            "device": self._device,
            "gpu_available": torch.cuda.is_available(),
            "memory_usage": torch.cuda.memory_allocated() if torch.cuda.is_available() else 0,
        }