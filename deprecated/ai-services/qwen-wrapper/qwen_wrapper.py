"""
Qwen CLI Wrapper - Ollama-compatible API
Exposes qwen CLI as REST API compatible with Open WebUI
"""

import subprocess
import json
import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Qwen Wrapper API")

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2000

class ModelInfo(BaseModel):
    name: str
    size: str = "Unknown"
    modified_at: str = "2024-01-01"

# Read qwen binary path from environment variable
QWEN_BIN = os.getenv("QWEN_BIN", "/usr/local/bin/qwen")

def call_qwen(prompt: str, temperature: float = 0.7, max_tokens: int = 2000) -> str:
    """Call qwen CLI and return response"""
    try:
        # Qwen CLI only accepts prompt as positional argument
        # Temperature and max_tokens are ignored (not supported by CLI)
        cmd = [QWEN_BIN, prompt]
        
        logger.info(f"Calling qwen with prompt length: {len(prompt)} chars")
        
        # Run from /tmp as qwen needs a valid workspace directory
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd="/tmp"
        )
        
        if result.returncode != 0:
            logger.error(f"Qwen failed with code {result.returncode}: {result.stderr}")
            raise Exception(f"Qwen CLI error: {result.stderr}")
        
        return result.stdout.strip()
    
    except subprocess.TimeoutExpired:
        raise Exception("Qwen CLI timeout after 60s")
    except Exception as e:
        logger.error(f"Error calling qwen: {str(e)}")
        raise

@app.get("/api/health")
@app.get("/health")
def health():
    """Health check"""
    return {"status": "ok", "backend": "qwen", "version": "0.5.2"}

@app.get("/api/tags")
def list_models():
    """List available models (Ollama-compatible)"""
    return {
        "models": [
            {
                "name": "qwen:latest",
                "modified_at": "2024-01-01T00:00:00Z",
                "size": 0,
                "digest": "qwen-cli-wrapper"
            }
        ]
    }

@app.get("/v1/models")
def list_models_openai():
    """List models in OpenAI format"""
    return {
        "object": "list",
        "data": [
            {
                "id": "qwen",
                "object": "model",
                "created": 1704067200,
                "owned_by": "qwen-wrapper"
            }
        ]
    }

@app.get("/api/version")
def get_version():
    """Return Ollama API version"""
    return {
        "version": "0.1.0"
    }

@app.get("/api/ps")
def list_running():
    """List running models"""
    return {
        "models": []
    }

@app.post("/api/chat")
@app.post("/v1/chat/completions")
async def chat(request: ChatRequest):
    """
    Chat completion endpoint
    Compatible with both Ollama and OpenAI formats
    """
    try:
        # Convert messages to single prompt
        prompt_parts = []
        for msg in request.messages:
            if msg.role == "system":
                prompt_parts.append(f"System: {msg.content}")
            elif msg.role == "user":
                prompt_parts.append(f"User: {msg.content}")
            elif msg.role == "assistant":
                prompt_parts.append(f"Assistant: {msg.content}")
        
        prompt = "\n".join(prompt_parts)
        
        # Use streaming for better UX
        if request.stream:
            return StreamingResponse(
                stream_qwen_response(prompt),
                media_type="text/event-stream"
            )
        else:
            # Non-streaming: collect full response
            response_text = await get_qwen_response(prompt)
            return {
                "model": "qwen",
                "created_at": "2024-01-01T00:00:00Z",
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "done": True
            }
    
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

async def get_qwen_response(prompt: str) -> str:
    """Get complete response from qwen (non-streaming)"""
    cmd = [QWEN_BIN, "-o", "stream-json", prompt]
    
    logger.info(f"Calling qwen non-streaming, prompt length: {len(prompt)} chars")
    
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=60,
        cwd="/tmp"
    )
    
    if result.returncode != 0:
        logger.error(f"Qwen failed: {result.stderr}")
        raise Exception(f"Qwen CLI error: {result.stderr}")
    
    # Parse stream-json output
    for line in result.stdout.strip().split('\n'):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            # Extract assistant message
            if data.get("type") == "assistant" and "message" in data:
                content = data["message"].get("content", [])
                if content and len(content) > 0:
                    return content[0].get("text", "")
        except json.JSONDecodeError:
            continue
    
    return "No response generated"

async def stream_qwen_response(prompt: str):
    """Stream qwen response in real-time"""
    cmd = [QWEN_BIN, "-o", "stream-json", prompt]
    
    logger.info(f"Calling qwen streaming, prompt length: {len(prompt)} chars")
    
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd="/tmp"
        )
        
        # Read output line by line
        for line in process.stdout:
            if not line.strip():
                continue
                
            try:
                data = json.loads(line)
                
                # Yield assistant messages as they come
                if data.get("type") == "assistant" and "message" in data:
                    content = data["message"].get("content", [])
                    if content and len(content) > 0:
                        text = content[0].get("text", "")
                        # Yield in OpenAI SSE format
                        chunk = json.dumps({
                            "model": "qwen",
                            "created_at": "2024-01-01T00:00:00Z",
                            "message": {
                                "role": "assistant",
                                "content": text
                            },
                            "done": False
                        })
                        yield f"data: {chunk}\n\n"
                
                # Final result message
                elif data.get("type") == "result":
                    chunk = json.dumps({
                        "model": "qwen",
                        "created_at": "2024-01-01T00:00:00Z",
                        "message": {
                            "role": "assistant",
                            "content": ""
                        },
                        "done": True
                    })
                    yield f"data: {chunk}\n\n"
                    yield "data: [DONE]\n\n"
                    
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON line: {line[:100]}")
                continue
        
        process.wait(timeout=60)
        
    except Exception as e:
        logger.error(f"Streaming error: {str(e)}")
        yield f"data: {json.dumps({'model': 'qwen', 'error': str(e), 'done': True})}\n\n"
        yield "data: [DONE]\n\n"

@app.post("/api/generate")
async def generate(request: dict):
    """
    Generate endpoint (Ollama format)
    """
    try:
        prompt = request.get("prompt", "")
        
        response_text = call_qwen(
            prompt,
            temperature=request.get("temperature", 0.7),
            max_tokens=request.get("max_tokens", 2000)
        )
        
        return {
            "model": "qwen",
            "created_at": "2024-01-01T00:00:00Z",
            "response": response_text,
            "done": True
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    """API info"""
    return {
        "name": "Qwen CLI Wrapper",
        "version": "1.0.0",
        "backend": "qwen-cli 0.5.2",
        "api_compatibility": "Ollama + OpenAI",
        "endpoints": [
            "/api/health",
            "/api/tags",
            "/api/chat",
            "/api/generate",
            "/api/version",
            "/api/ps",
            "/v1/models",
            "/v1/chat/completions"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=11434)
