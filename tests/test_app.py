"""
Tests for FastAPI application endpoints.
"""
import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import HTTPException

from app.app import app
from app.models import ChatCompletionRequest, Message


@pytest.fixture(autouse=True)
def reset_router_instance():
    """Reset the global router instance before each test."""
    import app.app
    app.app._router_instance = None
    yield
    app.app._router_instance = None

@pytest.fixture
def client():
    """Test client for FastAPI app."""
    return TestClient(app)


@pytest.fixture
def mock_router_service():
    """Mock router service for testing."""
    router = AsyncMock()
    router.get_stats.return_value = {
        "request_count": 10,
        "failover_count": 2,
        "rate_limit_skips": 1,
        "services": {
            "cerebras": {"requests": 8, "failures": 1, "rate_limited": 0},
            "openai": {"requests": 2, "failures": 0, "rate_limited": 1}
        }
    }
    router.get_health.return_value = {
        "status": "healthy",
        "total_services": 2,
        "services": {
            "cerebras": {"status": "healthy", "backend_type": "cerebras"},
            "openai": {"status": "healthy", "backend_type": "openai"}
        }
    }
    return router


@pytest.mark.unit
class TestHealthEndpoints:
    """Test health and status endpoints."""
    
    def test_root_endpoint(self, client):
        """Test root endpoint returns basic info."""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "LLM Router" in data["message"]
        
    def test_health_endpoint(self, client):
        """Test health endpoint."""
        with patch('app.app.get_router_service') as mock_get_router, \
             patch('app.app._router_instance', None):
            mock_router = MagicMock()
            mock_router.get_health.return_value = {
                "overall_status": "healthy",
                "services": {"service1": {"status": "healthy"}}
            }
            mock_get_router.return_value = mock_router
            
            response = client.get("/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"
            assert "details" in data


# @pytest.mark.unit 
# class TestChatCompletionEndpoint:
#     """Test chat completion endpoint."""
    
#     def test_chat_completion_success(self, client, mock_chat_completion_response):
#         """Test successful chat completion."""
#         with patch('app.app.get_router_service') as mock_get_router, \
#              patch('app.app._router_instance', None), \
#              patch('app.app.settings') as mock_settings:
#             # Mock settings
#             from app.config import ServiceConfig
#             mock_services = [
#                 ServiceConfig(name="test", backend_type="openai", base_url="http://test", api_key="test")
#             ]
#             mock_settings.get_router_services.return_value = mock_services
            
#             mock_router = MagicMock()
            
#             # Create async mock for chat_completion
#             async def mock_chat_completion(request):
#                 return mock_chat_completion_response
            
#             mock_router.chat_completion = AsyncMock(side_effect=mock_chat_completion)
#             mock_get_router.return_value = mock_router
            
#             request_data = {
#                 "model": "llama3.1-8b",
#                 "messages": [
#                     {"role": "user", "content": "Hello, how are you?"}
#                 ],
#                 "max_tokens": 100,
#                 "temperature": 0.7
#             }
            
#             response = client.post("/v1/chat/completions", json=request_data)
            
#             assert response.status_code == 200
#             data = response.json()
#             assert data["id"] == "chatcmpl-123"
#             assert data["model"] == "llama3.1-8b"
#             assert len(data["choices"]) == 1
#             assert data["choices"][0]["message"]["content"] == "Hello! How can I help you today?"
            
#             # Verify router was called
#             mock_router.chat_completion.assert_called_once()
            
#     def test_chat_completion_with_fallback_model(self, client, mock_chat_completion_response):
#         """Test chat completion with fallback model syntax."""
#         # Modify response to show fallback was used
#         mock_chat_completion_response.router = {
#             "service": "cerebras",
#             "requested_model": "qwen3|gemma3|llama3.1-8b",
#             "actual_model": "gemma3",
#             "model_options": ["qwen3", "gemma3", "llama3.1-8b"]
#         }
        
#         with patch('app.app.get_router_service') as mock_get_router, \
#              patch('app.app._router_instance', None):
#             mock_router = MagicMock()
            
#             # Create async mock for chat_completion
#             async def mock_chat_completion(request):
#                 return mock_chat_completion_response
            
#             mock_router.chat_completion = AsyncMock(side_effect=mock_chat_completion)
#             mock_get_router.return_value = mock_router
            
#             request_data = {
#                 "model": "qwen3|gemma3|llama3.1-8b",
#                 "messages": [
#                     {"role": "user", "content": "Test fallback"}
#                 ]
#             }
            
#             response = client.post("/v1/chat/completions", json=request_data)
            
#             assert response.status_code == 200
#             data = response.json()
#             assert data["router"]["requested_model"] == "qwen3|gemma3|llama3.1-8b"
#             assert data["router"]["actual_model"] == "gemma3"
#             assert data["router"]["model_options"] == ["qwen3", "gemma3", "llama3.1-8b"]
            
#     def test_chat_completion_validation_error(self, client):
#         """Test chat completion with invalid request data."""
#         request_data = {
#             "model": "llama3.1-8b",
#             # Missing required 'messages' field
#             "max_tokens": 100
#         }
        
#         response = client.post("/v1/chat/completions", json=request_data)
        
#         assert response.status_code == 422  # Validation error
        
#     def test_chat_completion_service_error(self, client):
#         """Test chat completion when service fails."""
#         with patch('app.app.get_router_service') as mock_get_router, \
#              patch('app.app._router_instance', None):
#             mock_router = MagicMock()
            
#             # Create async mock that raises HTTPException
#             async def mock_chat_completion_error(request):
#                 raise HTTPException(
#                     status_code=503, 
#                     detail={"error": {"message": "Service unavailable", "type": "service_error"}}
#                 )
            
#             mock_router.chat_completion = AsyncMock(side_effect=mock_chat_completion_error)
#             mock_get_router.return_value = mock_router
            
#             request_data = {
#                 "model": "llama3.1-8b",
#                 "messages": [
#                     {"role": "user", "content": "Test"}
#                 ]
#             }
            
#             response = client.post("/v1/chat/completions", json=request_data)
            
#             assert response.status_code == 503
#             data = response.json()
#             assert "error" in data
#             assert data["error"]["message"] == "Service unavailable"
            
#     def test_chat_completion_rate_limit_error(self, client):
#         """Test chat completion when rate limited."""
#         with patch('app.app.get_router_service') as mock_get_router:
#             mock_router = AsyncMock()
#             mock_router.chat_completion.side_effect = HTTPException(
#                 status_code=429,
#                 detail={
#                     "error": {
#                         "message": "All configured services are rate limited",
#                         "type": "rate_limit_exceeded"
#                     }
#                 }
#             )
#             mock_get_router.return_value = mock_router
            
#             request_data = {
#                 "model": "llama3.1-8b", 
#                 "messages": [
#                     {"role": "user", "content": "Test"}
#                 ]
#             }
            
#             response = client.post("/v1/chat/completions", json=request_data)
            
#             assert response.status_code == 429
#             data = response.json()
#             assert data["error"]["type"] == "rate_limit_exceeded"


# @pytest.mark.unit
# class TestModelsEndpoint:
#     """Test models listing endpoints."""
    
#     def test_list_models_success(self, client, cerebras_models_response, openai_models_response):
#         """Test successful model listing."""
#         combined_response = {
#             "object": "list",
#             "data": cerebras_models_response["data"] + openai_models_response["data"],
#             "router": {
#                 "services": [
#                     {"name": "cerebras", "backend_type": "cerebras", "models_count": 2},
#                     {"name": "openai", "backend_type": "openai", "models_count": 2}
#                 ],
#                 "working_services": 2,
#                 "total_services": 2,
#                 "combined_models": 4
#             }
#         }
        
#         with patch('app.app.get_router_service') as mock_get_router, \
#              patch('app.app._router_instance', None):
#             mock_router = MagicMock()
            
#             # Create async mock for list_models
#             async def mock_list_models():
#                 return combined_response
                
#             mock_router.list_models = AsyncMock(side_effect=mock_list_models)
#             mock_get_router.return_value = mock_router
            
#             response = client.get("/v1/models")
            
#             assert response.status_code == 200
#             data = response.json()
#             assert data["object"] == "list"
#             assert len(data["data"]) == 4
#             assert data["router"]["working_services"] == 2
#             assert data["router"]["combined_models"] == 4
            
#             # Verify models have service information
#             for model in data["data"]:
#                 assert "service" in model
#                 assert "backend_type" in model
                
#     def test_list_models_service_error(self, client):
#         """Test model listing when service fails."""
#         with patch('app.app.get_router_service') as mock_get_router, \
#              patch('app.app._router_instance', None):
#             mock_router = MagicMock()
            
#             # Create async mock that raises HTTPException
#             async def mock_list_models_error():
#                 raise HTTPException(status_code=500, detail="Service error")
            
#             mock_router.list_models = AsyncMock(side_effect=mock_list_models_error)
#             mock_get_router.return_value = mock_router
            
#             response = client.get("/v1/models")
            
#             assert response.status_code == 500
            
#     def test_get_model_by_id_success(self, client):
#         """Test getting specific model by ID."""
#         mock_model_data = {
#             "id": "llama3.1-8b",
#             "object": "model",
#             "created": 1234567890,
#             "owned_by": "Meta",
#             "service": "cerebras",
#             "backend_type": "cerebras"
#         }
        
#         combined_response = {
#             "object": "list",
#             "data": [mock_model_data],
#             "router": {"working_services": 1}
#         }
        
#         with patch('app.app.get_router_service') as mock_get_router, \
#              patch('app.app._router_instance', None):
#             mock_router = MagicMock()
            
#             # Create async mock for list_models
#             async def mock_list_models():
#                 return combined_response
            
#             mock_router.list_models = AsyncMock(side_effect=mock_list_models)
#             mock_get_router.return_value = mock_router
            
#             response = client.get("/v1/models/llama3.1-8b")
            
#             assert response.status_code == 200
#             data = response.json()
#             assert data["id"] == "llama3.1-8b"
#             assert data["service"] == "cerebras"
            
#     def test_get_model_by_id_not_found(self, client):
#         """Test getting non-existent model by ID."""
#         combined_response = {
#             "object": "list", 
#             "data": [],
#             "router": {"working_services": 0}
#         }
        
#         with patch('app.app.get_router_service') as mock_get_router:
#             mock_router = AsyncMock()
#             mock_router.list_models.return_value = combined_response
#             mock_get_router.return_value = mock_router
            
#             response = client.get("/v1/models/nonexistent-model")
            
#             assert response.status_code == 404
#             data = response.json()
#             assert "error" in data
#             assert "not found" in data["error"]["message"]


@pytest.mark.unit
class TestRouterEndpoints:
    """Test router-specific endpoints."""
    
    def test_router_stats(self, client):
        """Test router statistics endpoint."""
        mock_stats = {
            "total_requests": 10,
            "total_failovers": 2,
            "total_rate_limit_skips": 1,
            "service_stats": {
                "cerebras": {"requests": 8, "failures": 1},
                "openai": {"requests": 2, "failures": 0}
            }
        }
        
        with patch('app.app.get_router_service') as mock_get_router, \
             patch('app.app._router_instance', None):
            mock_router = MagicMock()
            mock_router.get_stats.return_value = mock_stats
            mock_get_router.return_value = mock_router
            
            response = client.get("/router/stats")
            
            assert response.status_code == 200
            data = response.json()
            assert data["total_requests"] == 10
            assert data["total_failovers"] == 2
            assert data["total_rate_limit_skips"] == 1
            assert "service_stats" in data
            assert "cerebras" in data["service_stats"]
            assert "openai" in data["service_stats"]
            
    def test_router_health(self, client):
        """Test router health endpoint."""
        mock_health = {
            "overall_status": "healthy",
            "services": {
                "cerebras": {"status": "healthy", "backend_type": "cerebras"},
                "openai": {"status": "healthy", "backend_type": "openai"}
            }
        }
        
        with patch('app.app.get_router_service') as mock_get_router, \
             patch('app.app._router_instance', None):
            mock_router = MagicMock()
            mock_router.get_health.return_value = mock_health
            mock_get_router.return_value = mock_router
            
            response = client.get("/router/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["overall_status"] == "healthy"
            assert "services" in data
            
    def test_router_reset_stats(self, client):
        """Test router reset statistics endpoint."""
        with patch('app.app.get_router_service') as mock_get_router, \
             patch('app.app._router_instance', None):
            mock_router = MagicMock()
            mock_router.reset_stats.return_value = None
            mock_get_router.return_value = mock_router
            
            response = client.post("/router/reset-stats")
            
            assert response.status_code == 200
            data = response.json()
            assert data["message"] == "Router statistics reset"
            mock_router.reset_stats.assert_called_once()
            
    # def test_router_rate_limits(self, client):
    #     """Test router rate limits endpoint."""
    #     mock_rate_limits = {
    #         "current_time": 1234567890,
    #         "services": {
    #             "cerebras": {
    #                 "rate_limit_requests": 10,
    #                 "rate_limit_window": 60,
    #                 "current_requests": 3,
    #                 "window_start": 1234567830,
    #                 "remaining_requests": 7,
    #                 "reset_time": 1234567890
    #             },
    #             "openai": {
    #                 "rate_limit_requests": None,
    #                 "rate_limit_window": 60,
    #                 "current_requests": 0,
    #                 "unlimited": True
    #             }
    #         }
    #     }
        
    #     with patch('app.app.get_router_service') as mock_get_router, \
    #          patch('app.app._router_instance', None):
    #         mock_router = MagicMock()
    #         mock_router.get_stats.return_value = mock_rate_limits
    #         mock_get_router.return_value = mock_router
            
    #         response = client.get("/router/rate-limits")
            
    #         assert response.status_code == 200
    #         data = response.json()
    #         assert "current_time" in data
    #         assert "services" in data
    #         assert "cerebras" in data["services"]
    #         assert data["services"]["cerebras"]["remaining_requests"] == 7
    #         assert data["services"]["openai"]["unlimited"] is True


# @pytest.mark.unit
# class TestErrorHandling:
#     """Test error handling middleware."""
    
#     def test_http_exception_handler(self, client):
#         """Test HTTP exception handling."""
#         with patch('app.app.get_router_service') as mock_get_router, \
#              patch('app.app._router_instance', None):
#             mock_router = MagicMock()
            
#             # Create async mock that raises HTTPException
#             async def mock_chat_completion_error(request):
#                 raise HTTPException(
#                     status_code=400,
#                     detail={
#                         "error": {
#                             "message": "Bad request",
#                             "type": "invalid_request"
#                         }
#                     }
#                 )
            
#             mock_router.chat_completion = AsyncMock(side_effect=mock_chat_completion_error)
#             mock_get_router.return_value = mock_router
            
#             request_data = {
#                 "model": "test",
#                 "messages": [{"role": "user", "content": "test"}]
#             }
            
#             response = client.post("/v1/chat/completions", json=request_data)
            
#             assert response.status_code == 400
#             data = response.json()
#             assert "error" in data
#             assert data["error"]["message"] == "Bad request"
#             assert data["error"]["type"] == "invalid_request"
            
#     def test_general_exception_handler(self, client):
#         """Test general exception handling."""
#         with patch('app.app.get_router_service') as mock_get_router, \
#              patch('app.app._router_instance', None):
#             mock_router = MagicMock()
            
#             # Create async mock that raises generic Exception
#             async def mock_chat_completion_error(request):
#                 raise Exception("Unexpected error")
            
#             mock_router.chat_completion = AsyncMock(side_effect=mock_chat_completion_error)
#             mock_get_router.return_value = mock_router
            
#             request_data = {
#                 "model": "test",
#                 "messages": [{"role": "user", "content": "test"}]
#             }
            
#             response = client.post("/v1/chat/completions", json=request_data)
            
#             assert response.status_code == 500
#             data = response.json()
#             assert "error" in data
#             assert "Internal server error" in data["error"]["message"]
#             assert data["error"]["type"] == "internal_error"


@pytest.mark.integration
class TestEndpointIntegration:
    """Integration tests for API endpoints."""
    
    # def test_full_chat_completion_flow(self, client):
    #     """Test complete chat completion flow with router."""
    #     mock_response_data = {
    #         "id": "chatcmpl-integration-test",
    #         "object": "chat.completion",
    #         "created": 1234567890,
    #         "model": "llama3.1-8b",
    #         "choices": [
    #             {
    #                 "index": 0,
    #                 "message": {"role": "assistant", "content": "Integration test response"},
    #                 "finish_reason": "stop"
    #             }
    #         ],
    #         "usage": {
    #             "prompt_tokens": 15,
    #             "completion_tokens": 8,
    #             "total_tokens": 23
    #         },
    #         "router": {
    #             "service": "cerebras",
    #             "attempt": 1,
    #             "duration": 1.234,
    #             "backend_type": "cerebras",
    #             "requested_model": "qwen3|llama3.1-8b",
    #             "actual_model": "llama3.1-8b",
    #             "model_options": ["qwen3", "llama3.1-8b"]
    #         }
    #     }
        
    #     # Mock the router service
    #     with patch('app.app.get_router_service') as mock_get_router, \
    #          patch('app.app._router_instance', None):
    #         mock_router = MagicMock()
            
    #         # Create async mock for chat completion
    #         from app.models import ChatCompletionResponse, Choice, Message, Usage
    #         async def mock_chat_completion(request):
    #             return ChatCompletionResponse(**mock_response_data)
            
    #         mock_router.chat_completion = AsyncMock(side_effect=mock_chat_completion)
    #         mock_get_router.return_value = mock_router
            
    #         # Test request
    #         request_data = {
    #             "model": "qwen3|llama3.1-8b",
    #             "messages": [
    #                 {"role": "user", "content": "Integration test message"}
    #             ],
    #             "max_tokens": 50,
    #             "temperature": 0.8
    #         }
            
    #         response = client.post("/v1/chat/completions", json=request_data)
    #         print(response.json()) 
    #         print(response.status_code)

    #         assert response.status_code == 200
    #         data = response.json()
            
    #         # Verify response structure
    #         assert data["id"] == "chatcmpl-integration-test"
    #         assert data["model"] == "llama3.1-8b"
    #         assert data["choices"][0]["message"]["content"] == "Integration test response"
            
    #         # Verify router metadata
    #         assert data["router"]["service"] == "cerebras"
    #         assert data["router"]["requested_model"] == "qwen3|llama3.1-8b"
    #         assert data["router"]["actual_model"] == "llama3.1-8b"
    #         assert data["router"]["model_options"] == ["qwen3", "llama3.1-8b"]
            
    #         # Verify router was called with correct parameters
    #         mock_router.chat_completion.assert_called_once()
    #         call_args = mock_router.chat_completion.call_args[0][0]
    #         assert call_args.model == "qwen3|llama3.1-8b"
    #         assert len(call_args.messages) == 1
    #         assert call_args.messages[0].content == "Integration test message"
