"""Configuration management for Cursor Pro Model."""

import os
from typing import Dict, List, Optional, Union
from pathlib import Path
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class ModelConfig(BaseModel):
    """Configuration for the AI model."""
    
    name: str = Field(default="microsoft/DialoGPT-medium", description="Model name or path")
    cache_dir: str = Field(default="./models", description="Model cache directory")
    max_tokens: int = Field(default=4096, description="Maximum tokens per generation")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0, description="Sampling temperature")
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Top-p sampling")
    device: str = Field(default="cpu", description="Device to run model on")
    gpu_enabled: bool = Field(default=False, description="Enable GPU acceleration")
    batch_size: int = Field(default=8, gt=0, description="Batch size for processing")


class CodeAnalysisConfig(BaseModel):
    """Configuration for code analysis."""
    
    supported_languages: List[str] = Field(
        default=["python", "javascript", "typescript", "java", "cpp", "rust", "go"],
        description="Supported programming languages"
    )
    max_file_size: int = Field(default=1048576, description="Maximum file size in bytes")
    max_context_files: int = Field(default=50, description="Maximum files in context")
    include_patterns: List[str] = Field(
        default=["*.py", "*.js", "*.ts", "*.java", "*.cpp", "*.rs", "*.go"],
        description="File patterns to include"
    )
    exclude_patterns: List[str] = Field(
        default=["node_modules/*", "*.pyc", "__pycache__/*", "*.git/*"],
        description="File patterns to exclude"
    )


class APIConfig(BaseModel):
    """Configuration for the API server."""
    
    host: str = Field(default="localhost", description="API host")
    port: int = Field(default=8000, ge=1, le=65535, description="API port")
    workers: int = Field(default=1, gt=0, description="Number of workers")
    api_key_required: bool = Field(default=False, description="Require API key")
    allowed_origins: List[str] = Field(default=["*"], description="Allowed CORS origins")
    max_request_size: int = Field(default=16777216, description="Max request size in bytes")


class LoggingConfig(BaseModel):
    """Configuration for logging."""
    
    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="json", description="Log format")
    file: Optional[str] = Field(default=None, description="Log file path")
    max_size: int = Field(default=10485760, description="Max log file size")
    backup_count: int = Field(default=5, description="Number of backup files")


class Config(BaseModel):
    """Main configuration class for Cursor Pro Model."""
    
    model: ModelConfig = Field(default_factory=ModelConfig)
    code_analysis: CodeAnalysisConfig = Field(default_factory=CodeAnalysisConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    debug: bool = Field(default=False, description="Enable debug mode")
    
    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        return cls(
            model=ModelConfig(
                name=os.getenv("MODEL_NAME", "microsoft/DialoGPT-medium"),
                cache_dir=os.getenv("MODEL_CACHE_DIR", "./models"),
                max_tokens=int(os.getenv("MAX_TOKENS", "4096")),
                temperature=float(os.getenv("TEMPERATURE", "0.7")),
                top_p=float(os.getenv("TOP_P", "0.9")),
                device=os.getenv("DEVICE", "cpu"),
                gpu_enabled=os.getenv("GPU_ENABLED", "false").lower() == "true",
                batch_size=int(os.getenv("BATCH_SIZE", "8")),
            ),
            code_analysis=CodeAnalysisConfig(
                supported_languages=os.getenv("SUPPORTED_LANGUAGES", "python,javascript,typescript,java,cpp,rust,go").split(","),
                max_file_size=int(os.getenv("MAX_FILE_SIZE", "1048576")),
                max_context_files=int(os.getenv("MAX_CONTEXT_FILES", "50")),
            ),
            api=APIConfig(
                host=os.getenv("API_HOST", "localhost"),
                port=int(os.getenv("API_PORT", "8000")),
                workers=int(os.getenv("API_WORKERS", "1")),
                api_key_required=os.getenv("API_KEY_REQUIRED", "false").lower() == "true",
                allowed_origins=os.getenv("ALLOWED_ORIGINS", "*").split(","),
            ),
            logging=LoggingConfig(
                level=os.getenv("LOG_LEVEL", "INFO"),
                format=os.getenv("LOG_FORMAT", "json"),
            ),
            debug=os.getenv("DEBUG", "false").lower() == "true"
        )
    
    @validator("model")
    def validate_model_config(cls, v):
        """Validate model configuration."""
        if v.temperature < 0 or v.temperature > 2:
            raise ValueError("Temperature must be between 0 and 2")
        if v.top_p < 0 or v.top_p > 1:
            raise ValueError("Top-p must be between 0 and 1")
        return v
    
    def save(self, path: Union[str, Path]) -> None:
        """Save configuration to file."""
        path = Path(path)
        with open(path, "w") as f:
            f.write(self.json(indent=2))
    
    @classmethod
    def load(cls, path: Union[str, Path]) -> "Config":
        """Load configuration from file."""
        path = Path(path)
        with open(path, "r") as f:
            return cls.parse_raw(f.read())


# Global configuration instance
config = Config.from_env()