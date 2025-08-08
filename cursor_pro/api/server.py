"""FastAPI server for Cursor Pro Model."""

import asyncio
import logging
import time
import uuid
from contextlib import asynccontextmanager
from typing import Dict, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse as FastAPIStreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from ..core.config import Config
from ..core.model import CursorProModel
from .models import *
from .routes import router

logger = logging.getLogger(__name__)


class CursorProAPI:
    """Main API service class."""
    
    def __init__(self, config: Config):
        """Initialize the API service."""
        self.config = config
        self.model: Optional[CursorProModel] = None
        self.start_time = time.time()
        self.conversations: Dict[str, Dict] = {}
        
    async def initialize(self):
        """Initialize the model and services."""
        logger.info("Initializing Cursor Pro API...")
        
        # Initialize the model
        self.model = CursorProModel(self.config)
        await self.model.load_model()
        
        logger.info("Cursor Pro API initialized successfully")
    
    async def shutdown(self):
        """Shutdown the API service."""
        logger.info("Shutting down Cursor Pro API...")
        
        if self.model:
            await self.model.unload_model()
        
        logger.info("Cursor Pro API shutdown complete")
    
    def get_model(self) -> CursorProModel:
        """Get the model instance."""
        if not self.model:
            raise HTTPException(status_code=503, detail="Model not initialized")
        return self.model
    
    def get_uptime(self) -> float:
        """Get service uptime in seconds."""
        return time.time() - self.start_time
    
    def create_conversation_id(self) -> str:
        """Create a new conversation ID."""
        return str(uuid.uuid4())
    
    def get_conversation(self, conversation_id: str) -> Dict:
        """Get conversation history."""
        return self.conversations.get(conversation_id, {"messages": []})
    
    def update_conversation(self, conversation_id: str, message: str, response: str):
        """Update conversation history."""
        if conversation_id not in self.conversations:
            self.conversations[conversation_id] = {"messages": []}
        
        self.conversations[conversation_id]["messages"].extend([
            {"role": "user", "content": message, "timestamp": time.time()},
            {"role": "assistant", "content": response, "timestamp": time.time()}
        ])
        
        # Limit conversation history
        max_messages = 50
        if len(self.conversations[conversation_id]["messages"]) > max_messages:
            self.conversations[conversation_id]["messages"] = \
                self.conversations[conversation_id]["messages"][-max_messages:]


# Global API instance
api_instance: Optional[CursorProAPI] = None


def get_api() -> CursorProAPI:
    """Dependency to get the API instance."""
    if api_instance is None:
        raise HTTPException(status_code=503, detail="API not initialized")
    return api_instance


# Optional authentication
security = HTTPBearer(auto_error=False)


async def get_auth(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)) -> Optional[str]:
    """Authentication dependency."""
    config = Config.from_env()
    
    if not config.api.api_key_required:
        return None
    
    if not credentials:
        raise HTTPException(status_code=401, detail="Authentication required")
    
    # Simple token validation - in production, use proper JWT validation
    if credentials.credentials != "your-api-key":  # Replace with actual validation
        raise HTTPException(status_code=401, detail="Invalid authentication credentials")
    
    return credentials.credentials


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global api_instance
    
    # Startup
    config = Config.from_env()
    api_instance = CursorProAPI(config)
    await api_instance.initialize()
    
    yield
    
    # Shutdown
    if api_instance:
        await api_instance.shutdown()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    config = Config.from_env()
    
    app = FastAPI(
        title="Cursor Pro Model API",
        description="AI-powered coding assistant API",
        version="0.1.0",
        lifespan=lifespan
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.api.allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Health check endpoint
    @app.get("/health", response_model=HealthCheckResponse)
    async def health_check(api: CursorProAPI = Depends(get_api)):
        """Health check endpoint."""
        try:
            model = api.get_model()
            health_info = await model.health_check()
            
            return HealthCheckResponse(
                status="healthy",
                model_loaded=health_info["model_loaded"],
                model_name=health_info["model_name"],
                device=health_info["device"],
                gpu_available=health_info["gpu_available"],
                memory_usage=health_info["memory_usage"],
                uptime=api.get_uptime()
            )
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return HealthCheckResponse(
                status="unhealthy",
                model_loaded=False,
                model_name="unknown",
                device="unknown",
                gpu_available=False,
                memory_usage=0,
                uptime=api.get_uptime()
            )
    
    # Code generation endpoint
    @app.post("/generate", response_model=CodeGenerationResponse)
    async def generate_code(
        request: CodeGenerationRequest,
        api: CursorProAPI = Depends(get_api),
        auth: Optional[str] = Depends(get_auth)
    ):
        """Generate code based on a prompt."""
        try:
            model = api.get_model()
            
            generated_code = await model.generate_code(
                prompt=request.prompt,
                language=request.language.value,
                max_tokens=request.max_tokens,
                temperature=request.temperature,
                context_files=request.context_files
            )
            
            return CodeGenerationResponse(
                generated_code=generated_code,
                language=request.language.value,
                explanation=f"Generated {request.language.value} code based on the prompt: {request.prompt[:100]}..."
            )
            
        except Exception as e:
            logger.error(f"Code generation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Code completion endpoint
    @app.post("/complete", response_model=CodeCompletionResponse)
    async def complete_code(
        request: CodeCompletionRequest,
        api: CursorProAPI = Depends(get_api),
        auth: Optional[str] = Depends(get_auth)
    ):
        """Provide code completions."""
        try:
            model = api.get_model()
            
            suggestions = await model.complete_code(
                code=request.code,
                cursor_position=request.cursor_position,
                language=request.language.value,
                context_files=request.context_files
            )
            
            return CodeCompletionResponse(
                suggestions=suggestions[:request.max_suggestions],
                context_info={"cursor_position": request.cursor_position}
            )
            
        except Exception as e:
            logger.error(f"Code completion failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Code explanation endpoint
    @app.post("/explain", response_model=CodeExplanationResponse)
    async def explain_code(
        request: CodeExplanationRequest,
        api: CursorProAPI = Depends(get_api),
        auth: Optional[str] = Depends(get_auth)
    ):
        """Explain code functionality."""
        try:
            model = api.get_model()
            
            explanation = await model.explain_code(
                code=request.code,
                language=request.language.value,
                context_files=request.context_files
            )
            
            return CodeExplanationResponse(
                explanation=explanation,
                key_concepts=["function", "variable", "loop"],  # TODO: Extract from analysis
                suggestions=["Consider adding comments", "Break down complex functions"]
            )
            
        except Exception as e:
            logger.error(f"Code explanation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Streaming generation endpoint
    @app.post("/generate/stream")
    async def stream_generate_code(
        request: CodeGenerationRequest,
        api: CursorProAPI = Depends(get_api),
        auth: Optional[str] = Depends(get_auth)
    ):
        """Stream code generation for real-time updates."""
        try:
            model = api.get_model()
            
            async def generate_stream():
                chunk_id = 0
                async for chunk in model.stream_generate_code(
                    prompt=request.prompt,
                    language=request.language.value,
                    max_tokens=request.max_tokens,
                    temperature=request.temperature,
                    context_files=request.context_files
                ):
                    response = StreamingResponse(
                        chunk_id=chunk_id,
                        content=chunk,
                        is_final=False
                    )
                    yield f"data: {response.json()}\n\n"
                    chunk_id += 1
                
                # Send final chunk
                final_response = StreamingResponse(
                    chunk_id=chunk_id,
                    content="",
                    is_final=True
                )
                yield f"data: {final_response.json()}\n\n"
            
            return FastAPIStreamingResponse(
                generate_stream(),
                media_type="text/plain",
                headers={"Cache-Control": "no-cache"}
            )
            
        except Exception as e:
            logger.error(f"Streaming generation failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Chat endpoint
    @app.post("/chat", response_model=ChatResponse)
    async def chat(
        request: ChatRequest,
        api: CursorProAPI = Depends(get_api),
        auth: Optional[str] = Depends(get_auth)
    ):
        """Chat interface for conversational coding assistance."""
        try:
            model = api.get_model()
            
            # Get or create conversation ID
            conversation_id = request.conversation_id or api.create_conversation_id()
            
            # Get conversation history
            conversation = api.get_conversation(conversation_id)
            
            # Build context with conversation history
            context_prompt = request.message
            if conversation["messages"]:
                history = "\n".join([
                    f"{msg['role']}: {msg['content']}" 
                    for msg in conversation["messages"][-10:]  # Last 10 messages
                ])
                context_prompt = f"Previous conversation:\n{history}\n\nUser: {request.message}"
            
            # Generate response
            response = await model.generate_code(
                prompt=context_prompt,
                language="markdown",  # Use markdown for chat responses
                max_tokens=1024,
                context_files=request.context_files
            )
            
            # Update conversation history
            api.update_conversation(conversation_id, request.message, response)
            
            return ChatResponse(
                response=response,
                conversation_id=conversation_id,
                suggestions=["Ask for code examples", "Request explanations", "Get refactoring help"]
            )
            
        except Exception as e:
            logger.error(f"Chat failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    # Include additional routes
    app.include_router(router, prefix="/api/v1")
    
    return app


# Create the app instance
app = create_app()