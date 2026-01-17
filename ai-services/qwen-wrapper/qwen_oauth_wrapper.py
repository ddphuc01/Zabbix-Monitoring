#!/usr/bin/env python3
"""
Qwen OAuth Wrapper - OpenAI-compatible API
Uses OAuth credentials from file for authentication with Qwen Cloud API
"""

import os
import json
import time
import logging
import httpx
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from tenacity import retry, stop_after_attempt, wait_exponential

# Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Qwen OAuth Wrapper API")

# Configuration from environment
QWEN_OAUTH_FILE = os.getenv("QWEN_OAUTH_FILE", "/root/.qwen/oauth_creds.json")
QWEN_API_BASE = os.getenv("QWEN_API_BASE", "https://dashscope.aliyuncs.com/api/v1")
QWEN_MODEL = os.getenv("QWEN_MODEL", "qwen-2.5-coder-32b-instruct")
RATE_LIMIT_PER_DAY = int(os.getenv("RATE_LIMIT_PER_DAY", "2000"))
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))

# Pydantic models
class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 2000

class QwenOAuthClient:
    """Handle OAuth authentication and API calls to Qwen"""
    
    def __init__(self, oauth_file: str):
        self.oauth_file = oauth_file
        self.access_token = None
        self.refresh_token = None
        self.token_expiry = None
        self.request_count_minute = 0
        self.request_count_day = 0
        self.minute_reset = time.time() + 60
        self.day_reset = time.time() + 86400
        
        self.load_credentials()
        logger.info("✅ QwenOAuthClient initialized")
    
    def load_credentials(self):
        """Load OAuth credentials from file"""
        try:
            with open(self.oauth_file, 'r') as f:
                creds = json.load(f)
            
            self.access_token = creds.get('access_token')
            self.refresh_token = creds.get('refresh_token')
            
            # Set expiry to 1 hour from now (typical OAuth access token lifetime)
            self.token_expiry = datetime.now() + timedelta(hours=1)
            
            logger.info(f"✅ OAuth credentials loaded from {self.oauth_file}")
            logger.info(f"🔑 Token expiry set to: {self.token_expiry.isoformat()}")
            
            if not self.access_token or not self.refresh_token:
                raise ValueError("Missing access_token or refresh_token in credentials file")
                
        except FileNotFoundError:
            logger.error(f"❌ OAuth credentials file not found: {self.oauth_file}")
            raise
        except json.JSONDecodeError as e:
            logger.error(f"❌ Invalid JSON in credentials file: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Error loading credentials: {e}")
            raise
    
    def save_credentials(self):
        """Save updated credentials back to file"""
        try:
            creds = {
                "access_token": self.access_token,
                "token_type": "Bearer",
                "refresh_token": self.refresh_token,
                "resource_url": "portal.qwen.ai"
            }
            
            with open(self.oauth_file, 'w') as f:
                json.dump(creds, f, indent=2)
            
            logger.info("✅ Credentials saved to file")
        except Exception as e:
            logger.error(f"❌ Error saving credentials: {e}")
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def refresh_access_token(self):
        """Refresh the access token using refresh token"""
        logger.info("⏰ Refreshing access token...")
        
        # Note: Qwen's actual refresh endpoint may vary - adjust URL as needed
        # This is a placeholder - check Qwen's OAuth documentation
        refresh_url = f"{QWEN_API_BASE}/oauth/token"
        
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.refresh_token
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(refresh_url, json=payload, timeout=10)
                response.raise_for_status()
                data = response.json()
            
            # Update tokens
            self.access_token = data.get('access_token')
            if 'refresh_token' in data:
                self.refresh_token = data['refresh_token']
            
            self.token_expiry = datetime.now() + timedelta(hours=1)
            
            # Save to file
            self.save_credentials()
            
            logger.info(f"✅ Token refreshed successfully, new expiry: {self.token_expiry.isoformat()}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Token refresh failed: {e}")
            # Try to reload from file in case of manual update
            try:
                self.load_credentials()
                logger.info("✅ Reloaded credentials from file as fallback")
                return True
            except:
                raise HTTPException(status_code=500, detail="Token refresh failed")
    
    async def ensure_token_valid(self):
        """Check token validity and refresh if needed"""
        if datetime.now() >= self.token_expiry - timedelta(minutes=5):
            # Refresh 5 minutes before expiry
            logger.info("🔄 Token expiring soon, refreshing...")
            await self.refresh_access_token()
    
    def check_rate_limits(self):
        """Check and enforce rate limits"""
        current_time = time.time()
        
        # Reset counters if time windows expired
        if current_time >= self.minute_reset:
            self.request_count_minute = 0
            self.minute_reset = current_time + 60
        
        if current_time >= self.day_reset:
            self.request_count_day = 0
            self.day_reset = current_time + 86400
        
        # Check limits
        if self.request_count_minute >= RATE_LIMIT_PER_MINUTE:
            raise HTTPException(status_code=429, detail="Rate limit exceeded: 60 requests/minute")
        
        if self.request_count_day >= RATE_LIMIT_PER_DAY:
            raise HTTPException(status_code=429, detail="Rate limit exceeded: 2000 requests/day")
        
        # Increment counters
        self.request_count_minute += 1
        self.request_count_day += 1
        
        logger.info(f"📊 Rate limits: {self.request_count_minute}/60 (min), {self.request_count_day}/2000 (day)")
    
    async def chat_completion(
        self, 
        messages: List[Dict[str, str]], 
        stream: bool = False,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> Any:
        """Call Qwen chat completion API"""
        
        # Ensure token is valid
        await self.ensure_token_valid()
        
        # Check rate limits
        self.check_rate_limits()
        
        # Prepare request
        url = f"{QWEN_API_BASE}/chat/completions"
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": QWEN_MODEL,
            "messages": messages,
            "stream": stream,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        logger.info(f"🤖 Calling Qwen API: {QWEN_MODEL}, stream={stream}, messages={len(messages)}")
        
        try:
            if stream:
                return await self._stream_chat(url, headers, payload)
            else:
                return await self._non_stream_chat(url, headers, payload)
        
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                # Token might be invalid, try refresh
                logger.warning("⚠️ 401 Unauthorized, attempting token refresh...")
                await self.refresh_access_token()
                # Retry request
                headers["Authorization"] = f"Bearer {self.access_token}"
                if stream:
                    return await self._stream_chat(url, headers, payload)
                else:
                    return await self._non_stream_chat(url, headers, payload)
            else:
                raise HTTPException(status_code=e.response.status_code, detail=str(e))
        
        except Exception as e:
            logger.error(f"❌ Qwen API error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def _non_stream_chat(self, url: str, headers: dict, payload: dict) -> dict:
        """Non-streaming chat completion"""
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            data = response.json()
        
        logger.info("✅ Qwen API response received")
        return data
    
    async def _stream_chat(self, url: str, headers: dict, payload: dict):
        """Streaming chat completion"""
        async with httpx.AsyncClient() as client:
            async with client.stream('POST', url, headers=headers, json=payload, timeout=60) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.strip():
                        # SSE format: data: {...}
                        if line.startswith('data: '):
                            yield line + '\n\n'
                        else:
                            yield f'data: {line}\n\n'

# Initialize Qwen client
try:
    qwen_client = QwenOAuthClient(QWEN_OAUTH_FILE)
except Exception as e:
    logger.error(f"❌ Failed to initialize Qwen client: {e}")
    qwen_client = None

# API Endpoints

@app.get("/health")
@app.get("/api/health")
def health():
    """Health check endpoint"""
    if not qwen_client:
        return {
            "status": "error",
            "backend": "qwen-oauth",
            "error": "OAuth client not initialized"
        }
    
    return {
        "status": "ok",
        "backend": "qwen-oauth",
        "model": QWEN_MODEL,
        "token_valid": qwen_client.access_token is not None,
        "token_expiry": qwen_client.token_expiry.isoformat() if qwen_client.token_expiry else None,
        "requests_today": qwen_client.request_count_day,
        "rate_limit_day": RATE_LIMIT_PER_DAY,
        "requests_this_minute": qwen_client.request_count_minute,
        "rate_limit_minute": RATE_LIMIT_PER_MINUTE
    }

@app.get("/api/token/status")
def token_status():
    """Check token status"""
    if not qwen_client:
        raise HTTPException(status_code=500, detail="OAuth client not initialized")
    
    return {
        "token_valid": qwen_client.access_token is not None,
        "expiry": qwen_client.token_expiry.isoformat() if qwen_client.token_expiry else None,
        "expires_in_seconds": (qwen_client.token_expiry - datetime.now()).total_seconds() if qwen_client.token_expiry else 0
    }

@app.get("/api/tags")
def list_models():
    """List available models (Ollama-compatible)"""
    return {
        "models": [
            {
                "name": QWEN_MODEL,
                "modified_at": datetime.now().isoformat(),
                "size": 0,
                "digest": "qwen-oauth-wrapper"
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
                "id": QWEN_MODEL,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "qwen-oauth-wrapper"
            }
        ]
    }

@app.post("/api/chat")
@app.post("/v1/chat/completions")
async def chat(request: ChatRequest):
    """
    Chat completion endpoint
    Compatible with both Ollama and OpenAI formats
    """
    if not qwen_client:
        raise HTTPException(status_code=500, detail="OAuth client not initialized")
    
    try:
        # Convert messages to dict format
        messages = [{"role": msg.role, "content": msg.content} for msg in request.messages]
        
        if request.stream:
            # Streaming response
            async def stream_wrapper():
                async for chunk in await qwen_client.chat_completion(
                    messages=messages,
                    stream=True,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens
                ):
                    yield chunk
            
            return StreamingResponse(stream_wrapper(), media_type="text/event-stream")
        
        else:
            # Non-streaming response
            response_data = await qwen_client.chat_completion(
                messages=messages,
                stream=False,
                temperature=request.temperature,
                max_tokens=request.max_tokens
            )
            
            # Return in OpenAI-compatible format
            return response_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/generate")
async def generate(request: dict):
    """
    Generate endpoint (Ollama format)
    """
    if not qwen_client:
        raise HTTPException(status_code=500, detail="OAuth client not initialized")
    
    try:
        prompt = request.get("prompt", "")
        
        # Convert prompt to messages format
        messages = [{"role": "user", "content": prompt}]
        
        response_data = await qwen_client.chat_completion(
            messages=messages,
            stream=False,
            temperature=request.get("temperature", 0.7),
            max_tokens=request.get("max_tokens", 2000)
        )
        
        # Extract content from OpenAI format
        content = response_data.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        return {
            "model": QWEN_MODEL,
            "created_at": datetime.now().isoformat(),
            "response": content,
            "done": True
        }
    
    except Exception as e:
        logger.error(f"❌ Generate error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/")
def root():
    """API info"""
    return {
        "name": "Qwen OAuth Wrapper",
        "version": "2.0.0",
        "backend": "qwen-cloud-oauth",
        "model": QWEN_MODEL,
        "api_compatibility": "Ollama + OpenAI",
        "endpoints": [
            "/health - Health check",
            "/api/token/status - Token status",
            "/api/tags - List models (Ollama)",
            "/v1/models - List models (OpenAI)",
            "/api/chat - Chat completion (Ollama)",
            "/v1/chat/completions - Chat completion (OpenAI)",
            "/api/generate - Generate (Ollama)"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=11434)
