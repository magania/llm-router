"""
Tests for OpenAIService functionality.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
from fastapi import HTTPException

from app.openai_service import OpenAIService
from app.models import ChatCompletionRequest, Message


@pytest.mark.unit
class TestOpenAIServiceInit:
    """Test OpenAIService initialization."""
    
    def test_init_with_all_params(self):
        """Test initialization with all parameters."""
        service = OpenAIService(
            backend_type="openai",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            timeout=30
        )
        
        assert service.backend_type == "openai"
        assert service.base_url == "https://api.openai.com/v1"
        assert service.api_key == "test-key"
        assert service.timeout == 30
        
    def test_init_without_api_key(self):
        """Test initialization without API key."""
        service = OpenAIService(
            backend_type="local-llama",
            base_url="http://localhost:11434/v1",
            api_key=None,
            timeout=30
        )
        
        assert service.api_key is None
        
    def test_get_headers_with_api_key(self):
        """Test getting headers with API key."""
        service = OpenAIService(
            backend_type="openai",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            timeout=30
        )
        
        headers = service._get_headers()
        assert headers["Authorization"] == "Bearer test-key"
        assert headers["Content-Type"] == "application/json"
        
    def test_get_headers_without_api_key(self):
        """Test getting headers without API key."""
        service = OpenAIService(
            backend_type="local-llama",
            base_url="http://localhost:11434/v1",
            api_key=None,
            timeout=30
        )
        
        headers = service._get_headers()
        assert "Authorization" not in headers
        assert headers["Content-Type"] == "application/json"


@pytest.mark.asyncio
@pytest.mark.unit
class TestChatCompletion:
    """Test chat completion functionality."""
    
    async def test_chat_completion_success(self, sample_chat_request):
        """Test successful chat completion."""
        service = OpenAIService(
            backend_type="openai",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            timeout=30
        )
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "chatcmpl-123",
            "object": "chat.completion",
            "created": 1234567890,
            "model": "llama3.1-8b",
            "choices": [
                {
                    "index": 0,
                    "message": {"role": "assistant", "content": "Test response"},
                    "finish_reason": "stop"
                }
            ],
            "usage": {
                "prompt_tokens": 10,
                "completion_tokens": 5,
                "total_tokens": 15
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            
            response = await service.chat_completion(sample_chat_request)
            
            assert response.id == "chatcmpl-123"
            assert response.model == "llama3.1-8b"
            assert len(response.choices) == 1
            assert response.choices[0].message.content == "Test response"
            
            # Verify the request was made correctly
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert call_args[0][0] == "https://api.openai.com/v1/chat/completions"
            
    async def test_chat_completion_http_error(self, sample_chat_request):
        """Test chat completion with HTTP error."""
        service = OpenAIService(
            backend_type="openai",
            base_url="https://api.openai.com/v1", 
            api_key="test-key",
            timeout=30
        )
        
        # Mock HTTP error response
        mock_response = MagicMock()
        mock_response.status_code = 429
        mock_response.json.return_value = {
            "error": {
                "message": "Rate limit exceeded",
                "type": "rate_limit_exceeded"
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.return_value = mock_response
            
            with pytest.raises(HTTPException) as exc_info:
                await service.chat_completion(sample_chat_request)
                
            assert exc_info.value.status_code == 429
            assert "Rate limit exceeded" in str(exc_info.value.detail)
            
    async def test_chat_completion_connection_error(self, sample_chat_request):
        """Test chat completion with connection error."""
        service = OpenAIService(
            backend_type="cerebras",
            base_url="https://api.cerebras.ai/v1",
            api_key="test-key", 
            timeout=30
        )
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.ConnectError("Connection failed")
            
            with pytest.raises(HTTPException) as exc_info:
                await service.chat_completion(sample_chat_request)
                
            assert exc_info.value.status_code == 502
            assert "Connection" in str(exc_info.value.detail)
            
    async def test_chat_completion_timeout_error(self, sample_chat_request):
        """Test chat completion with timeout error."""
        service = OpenAIService(
            backend_type="openai",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            timeout=30
        )
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.post.side_effect = httpx.TimeoutException("Request timeout")
            
            with pytest.raises(HTTPException) as exc_info:
                await service.chat_completion(sample_chat_request)
                
            assert exc_info.value.status_code == 504
            assert "timeout" in str(exc_info.value.detail).lower()
            
    async def test_chat_completion_no_api_key_when_required(self, sample_chat_request):
        """Test that service raises error during initialization without API key when required."""
        with pytest.raises(ValueError, match="openai backend requires an API key"):
            OpenAIService(
                backend_type="openai",  # Requires API key
                base_url="https://api.openai.com/v1",
                api_key=None,  # No API key provided
                timeout=30
            )


@pytest.mark.asyncio
@pytest.mark.unit  
class TestListModels:
    """Test list models functionality."""
    
    async def test_list_models_success(self):
        """Test successful model listing."""
        service = OpenAIService(
            backend_type="openai",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            timeout=30
        )
        
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "object": "list",
            "data": [
                {
                    "id": "gpt-4",
                    "object": "model",
                    "created": 1234567890,
                    "owned_by": "openai"
                },
                {
                    "id": "gpt-4-turbo",
                    "object": "model", 
                    "created": 1234567890,
                    "owned_by": "openai"
                },
                {
                    "id": "gpt-3.5-turbo",
                    "object": "model", 
                    "created": 1234567890,
                    "owned_by": "openai"
                }
            ]
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            
            response = await service.list_models()
            
            assert response["object"] == "list"
            assert len(response["data"]) == 3
            assert response["data"][0]["id"] == "gpt-4"
            assert response["data"][2]["id"] == "gpt-3.5-turbo"
            
            # Verify the request was made correctly
            mock_client.get.assert_called_once()
            call_args = mock_client.get.call_args
            assert call_args[0][0] == "https://api.openai.com/v1/models"
            
    async def test_list_models_http_error(self):
        """Test list models with HTTP error."""
        service = OpenAIService(
            backend_type="openai",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            timeout=30
        )
        
        # Mock HTTP error response
        mock_response = MagicMock()
        mock_response.status_code = 403
        mock_response.json.return_value = {
            "error": {
                "message": "Forbidden",
                "type": "forbidden"
            }
        }
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.return_value = mock_response
            
            # Should return fallback models instead of raising exception
            response = await service.list_models()
            
            assert response["object"] == "list"
            assert len(response["data"]) > 0
            
    async def test_list_models_connection_error(self):
        """Test list models with connection error returns fallback."""
        service = OpenAIService(
            backend_type="cerebras",
            base_url="https://api.cerebras.ai/v1",
            api_key="test-key",
            timeout=30
        )
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            mock_client.get.side_effect = httpx.ConnectError("Connection failed")
            
            # Should return fallback models instead of raising exception
            response = await service.list_models()
            
            assert response["object"] == "list"
            assert len(response["data"]) > 0
            
    async def test_list_models_fallback_on_error(self):
        """Test fallback models when service fails."""
        service = OpenAIService(
            backend_type="cerebras",
            base_url="https://api.cerebras.ai/v1",
            api_key="test-key",
            timeout=30
        )
        
        with patch('httpx.AsyncClient') as mock_client_class:
            mock_client = AsyncMock()
            mock_client_class.return_value.__aenter__.return_value = mock_client
            # Simulate a connection error that triggers fallback
            mock_client.get.side_effect = httpx.ConnectError("Connection failed")
            
            # Should not raise exception, should return fallback
            response = await service.list_models()
            
            assert response["object"] == "list"
            assert len(response["data"]) > 0  # Should have fallback models


@pytest.mark.unit
class TestFallbackModels:
    """Test fallback model functionality."""
    
    def test_get_fallback_models_cerebras(self):
        """Test getting fallback models for Cerebras."""
        service = OpenAIService(
            backend_type="cerebras",
            base_url="https://api.cerebras.ai/v1",
            api_key="test-key",
            timeout=30
        )
        
        models = service._get_fallback_models()
        
        assert models["object"] == "list"
        assert len(models["data"]) > 0
        
        # Check that some expected Cerebras models are included
        model_ids = [model["id"] for model in models["data"]]
        assert "llama3.1-8b" in model_ids
        assert "llama3.1-70b" in model_ids
        
    def test_get_fallback_models_openai(self):
        """Test getting fallback models for OpenAI."""
        service = OpenAIService(
            backend_type="openai",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            timeout=30
        )
        
        models = service._get_fallback_models()
        
        assert models["object"] == "list"
        assert len(models["data"]) > 0
        
        # Check that some expected OpenAI models are included
        model_ids = [model["id"] for model in models["data"]]
        assert "gpt-4" in model_ids
        assert "gpt-3.5-turbo" in model_ids
        
    def test_get_fallback_models_ollama(self):
        """Test getting fallback models for Ollama (custom backend fallback)."""
        service = OpenAIService(
            backend_type="ollama",
            base_url="http://localhost:11434/v1",
            api_key=None,
            timeout=30
        )
        
        models = service._get_fallback_models()
        
        assert models["object"] == "list"
        assert len(models["data"]) > 0
        
        # Ollama backend uses custom fallback with default model
        model_ids = [model["id"] for model in models["data"]]
        assert "default" in model_ids
        
    def test_get_fallback_models_custom(self):
        """Test getting fallback models for custom backend."""
        service = OpenAIService(
            backend_type="custom",
            base_url="https://custom-api.example.com/v1",
            api_key="custom-key",
            timeout=30
        )
        
        models = service._get_fallback_models()
        
        assert models["object"] == "list"
        assert len(models["data"]) > 0
        
        # Should return some generic models
        model_ids = [model["id"] for model in models["data"]]
        assert len(model_ids) > 0


@pytest.mark.unit
class TestServiceValidation:
    """Test service validation and error handling."""
    
    def test_openai_backend_requires_api_key(self):
        """Test that openai backend raises error without API key."""
        with pytest.raises(ValueError, match="openai backend requires an API key"):
            OpenAIService(
                backend_type="openai",
                base_url="https://api.openai.com/v1",
                api_key=None,
                timeout=30
            )
        
    def test_ollama_no_api_key_required(self):
        """Test that ollama doesn't require API key."""
        # Should not raise exception
        service = OpenAIService(
            backend_type="ollama",
            base_url="http://localhost:11434/v1",
            api_key=None,
            timeout=30
        )
        
        assert service.api_key is None
        
    def test_custom_backend_no_api_key(self):
        """Test custom backend without API key."""
        # Should not raise exception for custom backend
        service = OpenAIService(
            backend_type="custom",
            base_url="https://custom-api.example.com/v1",
            api_key=None,
            timeout=30
        )
        
        assert service.api_key is None
