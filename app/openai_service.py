# LLM Router - OpenAI API compatible router for multiple LLM backends
# Copyright (C) 2025
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""
Service for forwarding requests to OpenAI-compatible APIs.
Supports multiple backends: OpenAI, Cerebras, DeepInfra, Local Llama, etc.
"""
import time
import uuid
from typing import Dict, Any, Optional, Literal
import httpx
from fastapi import HTTPException

from .models import ChatCompletionRequest, ChatCompletionResponse, Usage, Choice, Message


BackendType = Literal["openai", "cerebras", "deepinfra", "ollama", "custom"]


class OpenAIService:
    """Service for interacting with OpenAI-compatible APIs."""
    
    def __init__(
        self, 
        backend_type: BackendType,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 60
    ):
        """
        Initialize the OpenAI-compatible service.
        
        Args:
            backend_type: Type of backend (openai, cerebras, deepinfra, ollama, custom)
            base_url: Base URL for the API
            api_key: API key (not required for local servers)
            timeout: Request timeout in seconds
        """
        self.backend_type = backend_type
        self.base_url = base_url.rstrip('/')  # Remove trailing slash
        self.api_key = api_key
        self.timeout = timeout
        
        # Validate required configurations
        if backend_type in ["openai", "cerebras", "deepinfra"] and not api_key:
            raise ValueError(f"{backend_type} backend requires an API key")
    
    def _get_headers(self) -> Dict[str, str]:
        """Get headers for API requests."""
        headers = {
            "Content-Type": "application/json",
            "User-Agent": f"LLM-Router/1.0.0 ({self.backend_type})"
        }
        
        # Add authentication header if API key is provided
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
            
        return headers
    
    def _get_endpoint_url(self, endpoint: str) -> str:
        """Get the full URL for an endpoint."""
        endpoint = endpoint.lstrip('/')  # Remove leading slash
        return f"{self.base_url}/{endpoint}"
    
    async def chat_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """Forward chat completion request to the backend API."""
        
        # Prepare the request payload
        payload = request.model_dump(exclude_unset=True)
        
        # Backend-specific payload adjustments
        if self.backend_type == "ollama":
            # Some local servers might not support all OpenAI parameters
            # Remove unsupported parameters that might cause errors
            payload.pop("logit_bias", None)
            payload.pop("user", None)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                url = self._get_endpoint_url("chat/completions")
                response = await client.post(
                    url,
                    json=payload,
                    headers=self._get_headers()
                )
                
                if response.status_code != 200:
                    error_detail = "Unknown error"
                    try:
                        error_data = response.json()
                        error_detail = error_data.get("error", {}).get("message", error_detail)
                        if not error_detail:
                            error_detail = error_data.get("message", error_detail)
                    except Exception:
                        error_detail = f"HTTP {response.status_code}: {response.text}"
                    
                    raise HTTPException(
                        status_code=response.status_code,
                        detail={
                            "error": {
                                "message": f"[{self.backend_type}] {error_detail}",
                                "type": "api_error",
                                "backend": self.backend_type
                            }
                        }
                    )
                
                # Parse the response
                api_response = response.json()
                
                # Transform response to match OpenAI format
                return self._transform_response(api_response, request.model)
                
            except httpx.TimeoutException:
                raise HTTPException(
                    status_code=504,
                    detail={
                        "error": {
                            "message": f"Request to {self.backend_type} timed out",
                            "type": "timeout_error",
                            "backend": self.backend_type
                        }
                    }
                )
            except httpx.RequestError as e:
                raise HTTPException(
                    status_code=502,
                    detail={
                        "error": {
                            "message": f"Connection error to {self.backend_type}: {str(e)}",
                            "type": "connection_error",
                            "backend": self.backend_type
                        }
                    }
                )
    
    def _transform_response(self, api_response: Dict[str, Any], model: str) -> ChatCompletionResponse:
        """Transform API response to OpenAI format."""
        
        # Extract choices
        choices = []
        for i, choice in enumerate(api_response.get("choices", [])):
            # Handle different response formats
            message_data = choice.get("message", {})
            if not message_data and "text" in choice:
                # Some APIs return 'text' instead of 'message'
                message_data = {"role": "assistant", "content": choice.get("text", "")}
            
            transformed_choice = Choice(
                index=i,
                message=Message(
                    role=message_data.get("role", "assistant"),
                    content=message_data.get("content", "")
                ),
                finish_reason=choice.get("finish_reason", choice.get("stop_reason"))
            )
            choices.append(transformed_choice)
        
        # Extract usage information
        usage_data = api_response.get("usage", {})
        usage = Usage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0)
        )
        
        # Create response
        return ChatCompletionResponse(
            id=api_response.get("id", f"chatcmpl-{uuid.uuid4().hex}"),
            object="chat.completion",
            created=api_response.get("created", int(time.time())),
            model=model,
            choices=choices,
            usage=usage
        )
    
    async def list_models(self) -> Dict[str, Any]:
        """Get available models from the backend API."""
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                url = self._get_endpoint_url("models")
                response = await client.get(
                    url,
                    headers=self._get_headers()
                )
                
                if response.status_code == 200:
                    return response.json()
                
            except (httpx.TimeoutException, httpx.RequestError):
                pass
        
        # Fallback to default models based on backend type
        return self._get_fallback_models()
    
    def _get_fallback_models(self) -> Dict[str, Any]:
        """Get fallback models when the models endpoint is not available."""
        current_time = int(time.time())
        
        if self.backend_type == "openai":
            models = [
                {"id": "gpt-4", "object": "model", "created": current_time, "owned_by": "openai"},
                {"id": "gpt-4-turbo", "object": "model", "created": current_time, "owned_by": "openai"},
                {"id": "gpt-3.5-turbo", "object": "model", "created": current_time, "owned_by": "openai"},
            ]
        elif self.backend_type == "cerebras":
            models = [
                {"id": "llama3.1-8b", "object": "model", "created": current_time, "owned_by": "cerebras"},
                {"id": "llama3.1-70b", "object": "model", "created": current_time, "owned_by": "cerebras"},
            ]
        elif self.backend_type == "deepinfra":
            models = [
                {"id": "Qwen/Qwen3-Coder-480B-A35B-Instruct-Turbo", "object": "model", "created": current_time, "owned_by": "deepinfra"},
                {"id": "Qwen/Qwen3-Coder-480B-A35B-Instruct", "object": "model", "created": current_time, "owned_by": "deepinfra"},
                {"id": "Qwen/Qwen3-30B-A3B", "object": "model", "created": current_time, "owned_by": "deepinfra"},
                {"id": "Qwen/Qwen3-235B-A22B-Thinking-2507", "object": "model", "created": current_time, "owned_by": "deepinfra"},
            ]
        elif self.backend_type == "ollama":
            models = [
                {"id": "llama-2-7b-chat", "object": "model", "created": current_time, "owned_by": "local"},
                {"id": "llama-2-13b-chat", "object": "model", "created": current_time, "owned_by": "local"},
                {"id": "mistral-7b-instruct", "object": "model", "created": current_time, "owned_by": "local"},
            ]
        else:  # custom
            models = [
                {"id": "default", "object": "model", "created": current_time, "owned_by": "custom"},
            ]
        
        return {
            "object": "list",
            "data": models
        }
    
    def get_info(self) -> Dict[str, Any]:
        """Get service information."""
        return {
            "backend_type": self.backend_type,
            "base_url": self.base_url,
            "has_api_key": bool(self.api_key),
            "timeout": self.timeout
        }
