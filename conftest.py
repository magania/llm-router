"""
Pytest configuration and shared fixtures for LLM Router tests.
"""
import pytest
import asyncio
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch
import time

from app.config import ServiceConfig, Settings
from app.openai_service import OpenAIService
from app.router_service import RouterService
from app.models import ChatCompletionRequest, ChatCompletionResponse, Choice, Message, Usage


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = MagicMock(spec=Settings)
    settings.request_timeout = 30
    settings.cerebras_api_key = "test-cerebras-key"
    settings.cerebras_base_url = "https://api.cerebras.ai/v1"
    settings.openai_api_key = "test-openai-key"
    settings.openai_base_url = "https://api.openai.com/v1"
    settings.local_llama_base_url = "http://localhost:11434/v1"
    return settings


@pytest.fixture
def sample_service_configs():
    """Sample service configurations for testing."""
    return [
        ServiceConfig(
            name="cerebras",
            backend_type="cerebras",
            base_url="https://api.cerebras.ai/v1",
            api_key="test-cerebras-key",
            timeout=30,
            priority=0,
            rate_limit_requests=10,
            rate_limit_window=60
        ),
        ServiceConfig(
            name="openai",
            backend_type="openai",
            base_url="https://api.openai.com/v1",
            api_key="test-openai-key",
            timeout=30,
            priority=1,
            rate_limit_requests=20,
            rate_limit_window=60
        ),
        ServiceConfig(
            name="ollama",
            backend_type="ollama",
            base_url="http://localhost:11434/v1",
            api_key=None,
            timeout=30,
            priority=2
        )
    ]


@pytest.fixture
def mock_chat_completion_response():
    """Mock chat completion response."""
    return ChatCompletionResponse(
        id="chatcmpl-123",
        object="chat.completion",
        created=int(time.time()),
        model="llama3.1-8b",
        choices=[
            Choice(
                index=0,
                message=Message(role="assistant", content="Hello! How can I help you today?"),
                finish_reason="stop"
            )
        ],
        usage=Usage(
            prompt_tokens=10,
            completion_tokens=12,
            total_tokens=22
        )
    )


@pytest.fixture
def mock_models_response():
    """Mock models list response."""
    return {
        "object": "list",
        "data": [
            {
                "id": "llama3.1-8b",
                "object": "model",
                "created": 1234567890,
                "owned_by": "Meta"
            },
            {
                "id": "gemma3:4b",
                "object": "model", 
                "created": 1234567890,
                "owned_by": "Google"
            }
        ]
    }


@pytest.fixture
def sample_chat_request():
    """Sample chat completion request."""
    return ChatCompletionRequest(
        model="llama3.1-8b",
        messages=[
            Message(role="user", content="Hello, how are you?")
        ],
        max_tokens=100,
        temperature=0.7
    )


@pytest.fixture
def sample_fallback_chat_request():
    """Sample chat completion request with fallback models."""
    return ChatCompletionRequest(
        model="qwen3|gemma3|llama3.1-8b",
        messages=[
            Message(role="user", content="Hello, how are you?")
        ],
        max_tokens=100,
        temperature=0.7
    )


@pytest.fixture
def mock_openai_service():
    """Mock OpenAI service."""
    service = AsyncMock(spec=OpenAIService)
    service.backend_type = "cerebras"
    service.base_url = "https://api.cerebras.ai/v1"
    service.timeout = 30
    return service


@pytest.fixture
def mock_httpx_client():
    """Mock HTTPX client for API calls."""
    client = AsyncMock()
    return client


@pytest.fixture
def mock_successful_http_response():
    """Mock successful HTTP response."""
    response = MagicMock()
    response.status_code = 200
    response.is_error = False
    response.json.return_value = {
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": int(time.time()),
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
    return response


@pytest.fixture
def mock_error_http_response():
    """Mock error HTTP response."""
    response = MagicMock()
    response.status_code = 429
    response.is_error = True
    response.json.return_value = {
        "error": {
            "message": "Rate limit exceeded",
            "type": "rate_limit_exceeded"
        }
    }
    return response


@pytest.fixture
def router_service(sample_service_configs):
    """Create a RouterService instance for testing."""
    with patch('app.router_service.OpenAIService') as mock_service_class:
        # Create mock service instances
        mock_services = []
        for config in sample_service_configs:
            mock_service = AsyncMock(spec=OpenAIService)
            mock_service.backend_type = config.backend_type
            mock_service.base_url = config.base_url
            mock_service.timeout = config.timeout
            mock_services.append(mock_service)
        
        mock_service_class.side_effect = mock_services
        
        router = RouterService(sample_service_configs)
        router._mock_services = mock_services  # Store references for test access
        return router


@pytest.fixture
def cerebras_models_response():
    """Mock Cerebras models response."""
    return {
        "object": "list",
        "data": [
            {
                "id": "llama3.1-8b",
                "object": "model",
                "created": 1234567890,
                "owned_by": "Meta"
            },
            {
                "id": "llama3.1-70b",
                "object": "model",
                "created": 1234567890,
                "owned_by": "Meta"
            }
        ]
    }


@pytest.fixture
def openai_models_response():
    """Mock OpenAI models response."""
    return {
        "object": "list",
        "data": [
            {
                "id": "gpt-4o",
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


@pytest.fixture
def ollama_models_response():
    """Mock Ollama models response."""
    return {
        "object": "list",
        "data": [
            {
                "id": "gemma3:4b",
                "object": "model",
                "created": 1234567890,
                "owned_by": "Google"
            },
            {
                "id": "qwen3:7b",
                "object": "model",
                "created": 1234567890,
                "owned_by": "Alibaba"
            }
        ]
    }


@pytest.fixture
def auth_headers():
    """Valid authentication headers for testing."""
    return {"Authorization": "Bearer test-api-key"}


@pytest.fixture
def invalid_auth_headers():
    """Invalid authentication headers for testing."""
    return {"Authorization": "Bearer invalid-key"}


@pytest.fixture(autouse=True)
def mock_auth_service():
    """Mock authentication service for all tests."""
    with patch('app.app.get_auth_service') as mock_get_auth, \
         patch('app.app._auth_service', None):
        
        mock_auth = MagicMock()
        mock_auth.get_valid_keys_count.return_value = 1
        mock_auth.is_valid_key.return_value = True  # Default to valid key
        mock_auth.record_request.return_value = None
        mock_auth.get_metrics.return_value = {
            "valid_keys_count": 1,
            "total_requests": 10,
            "total_success": 9,
            "total_errors": 1,
            "success_rate": 90.0,
            "keys_metrics": {},
            "active_keys": 1
        }
        
        mock_get_auth.return_value = mock_auth
        yield mock_auth


@pytest.fixture
def disable_auth():
    """Fixture to disable authentication for testing."""
    with patch('app.app.settings') as mock_settings:
        mock_settings.enable_auth = False
        mock_settings.get_router_services.return_value = []
        yield mock_settings
