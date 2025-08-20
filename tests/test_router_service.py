"""
Tests for RouterService including model caching and fallback functionality.
"""
import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import HTTPException

from app.router_service import RouterService
from app.config import ServiceConfig
from app.models import ChatCompletionRequest, ChatCompletionResponse, Message


@pytest.mark.unit
class TestRouterServiceInit:
    """Test RouterService initialization."""
    
    def test_init_with_valid_services(self, sample_service_configs):
        """Test initialization with valid service configurations."""
        with patch('app.router_service.OpenAIService'):
            router = RouterService(sample_service_configs)
            
            assert len(router.services) == 3
            assert len(router.service_configs) == 3
            assert router.request_count == 0
            assert router.failover_count == 0
            assert len(router.model_cache) == 0
            
    def test_init_empty_services_raises_error(self):
        """Test initialization with empty services list raises error."""
        with pytest.raises(ValueError, match="At least one service configuration is required"):
            RouterService([])
    
    def test_services_sorted_by_priority(self, sample_service_configs):
        """Test that services are sorted by priority (lower number = higher priority)."""
        # Shuffle the configs to test sorting
        shuffled_configs = [
            sample_service_configs[1],  # priority 1 (openai)
            sample_service_configs[2],  # priority 2 (ollama)
            sample_service_configs[0],  # priority 0 (cerebras)
        ]
        
        with patch('app.router_service.OpenAIService'):
            router = RouterService(shuffled_configs)
            
            # Should be sorted by priority: cerebras (0), openai (1), ollama (2)
            assert router.service_configs[0].name == "cerebras"
            assert router.service_configs[1].name == "openai"
            assert router.service_configs[2].name == "ollama"


@pytest.mark.unit
class TestModelCaching:
    """Test model caching functionality."""
    
    def test_update_model_cache(self, router_service):
        """Test updating model cache for a service."""
        models = [
            {"id": "model1", "object": "model"},
            {"id": "model2", "object": "model"}
        ]
        
        router_service._update_model_cache("test_service", models)
        
        assert "test_service" in router_service.model_cache
        assert router_service.model_cache["test_service"] == ["model1", "model2"]
        assert "test_service" in router_service.cache_last_updated
        
    def test_is_cache_valid_fresh_cache(self, router_service):
        """Test cache validity check with fresh cache."""
        router_service.cache_last_updated["test_service"] = time.time()
        
        assert router_service._is_cache_valid("test_service") is True
        
    def test_is_cache_valid_stale_cache(self, router_service):
        """Test cache validity check with stale cache."""
        router_service.cache_last_updated["test_service"] = time.time() - 400  # Older than TTL
        
        assert router_service._is_cache_valid("test_service") is False
        
    def test_is_cache_valid_no_cache(self, router_service):
        """Test cache validity check with no cache."""
        assert router_service._is_cache_valid("nonexistent_service") is False
        
    def test_service_supports_model_with_cache(self, router_service):
        """Test model support check with cache."""
        router_service.model_cache["test_service"] = ["model1", "model2"]
        
        assert router_service._service_supports_model("test_service", "model1") is True
        assert router_service._service_supports_model("test_service", "model3") is False
        
    def test_service_supports_model_no_cache(self, router_service):
        """Test model support check without cache (should assume support)."""
        assert router_service._service_supports_model("unknown_service", "any_model") is True


@pytest.mark.unit 
class TestModelParsing:
    """Test model parsing and fallback functionality."""
    
    def test_parse_model_options_single_model(self, router_service):
        """Test parsing single model (no fallback)."""
        options = router_service._parse_model_options("gpt-4o")
        assert options == ["gpt-4o"]
        
    def test_parse_model_options_multiple_models(self, router_service):
        """Test parsing multiple models with fallback syntax."""
        options = router_service._parse_model_options("qwen3|gemma3|llama3.1-8b")
        assert options == ["qwen3", "gemma3", "llama3.1-8b"]
        
    def test_parse_model_options_with_spaces(self, router_service):
        """Test parsing models with spaces around separators."""
        options = router_service._parse_model_options("qwen3 | gemma3 | llama3.1-8b")
        assert options == ["qwen3", "gemma3", "llama3.1-8b"]
        
    def test_get_best_model_for_service_first_match(self, router_service):
        """Test getting best model when first option is supported."""
        router_service.model_cache["test_service"] = ["qwen3", "gemma3", "llama3.1-8b"]
        model_options = ["qwen3", "gemma3", "llama3.1-8b"]
        
        best_model = router_service._get_best_model_for_service("test_service", model_options)
        assert best_model == "qwen3"
        
    def test_get_best_model_for_service_second_match(self, router_service):
        """Test getting best model when second option is supported."""
        router_service.model_cache["test_service"] = ["gemma3", "llama3.1-8b"]  # No qwen3
        model_options = ["qwen3", "gemma3", "llama3.1-8b"]
        
        best_model = router_service._get_best_model_for_service("test_service", model_options)
        assert best_model == "gemma3"
        
    def test_get_best_model_for_service_no_match(self, router_service):
        """Test getting best model when no options are supported."""
        router_service.model_cache["test_service"] = ["different_model"]
        model_options = ["qwen3", "gemma3", "llama3.1-8b"]
        
        best_model = router_service._get_best_model_for_service("test_service", model_options)
        assert best_model is None


@pytest.mark.unit
class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_record_request(self, router_service):
        """Test recording a request for rate limiting."""
        service_name = "test_service"
        
        router_service._record_request(service_name)
        
        assert len(router_service.request_timestamps[service_name]) == 1
        
    def test_is_rate_limited_no_limit(self, router_service, sample_service_configs):
        """Test rate limiting check when service has no rate limit."""
        service_config = ServiceConfig(
            name="unlimited", 
            backend_type="openai", 
            base_url="test",
            rate_limit_requests=None
        )
        
        is_limited = router_service._is_rate_limited("unlimited", service_config)
        assert is_limited is False
        
    def test_is_rate_limited_under_limit(self, router_service):
        """Test rate limiting when under limit."""
        service_config = ServiceConfig(
            name="limited",
            backend_type="openai",
            base_url="test", 
            rate_limit_requests=10,
            rate_limit_window=60
        )
        
        # Add some requests but under limit
        for _ in range(5):
            router_service._record_request("limited")
            
        is_limited = router_service._is_rate_limited("limited", service_config)
        assert is_limited is False
        
    def test_is_rate_limited_over_limit(self, router_service):
        """Test rate limiting when over limit."""
        service_config = ServiceConfig(
            name="limited",
            backend_type="openai", 
            base_url="test",
            rate_limit_requests=3,
            rate_limit_window=60
        )
        
        # Add requests over limit
        for _ in range(5):
            router_service._record_request("limited")
            
        is_limited = router_service._is_rate_limited("limited", service_config)
        assert is_limited is True


@pytest.mark.asyncio
@pytest.mark.unit
class TestCacheRefresh:
    """Test cache refresh functionality."""
    
    async def test_refresh_stale_caches(self, router_service):
        """Test refreshing stale caches."""
        # Setup mock services
        service1_mock = router_service._mock_services[0]
        service1_mock.list_models.return_value = {
            "data": [{"id": "model1"}, {"id": "model2"}]
        }
        
        # Make cache stale 
        router_service.cache_last_updated["cerebras"] = time.time() - 400
        
        await router_service._refresh_stale_caches()
        
        # Verify cache was refreshed
        service1_mock.list_models.assert_called_once()
        assert "cerebras" in router_service.model_cache
        
    async def test_refresh_stale_caches_handles_errors(self, router_service):
        """Test that cache refresh handles service errors gracefully."""
        # Setup mock service to raise error
        service1_mock = router_service._mock_services[0] 
        service1_mock.list_models.side_effect = Exception("Service error")
        
        # Make cache stale
        router_service.cache_last_updated["cerebras"] = time.time() - 400
        
        # Should not raise exception
        await router_service._refresh_stale_caches()
        
        # Verify it tried to refresh but handled error
        service1_mock.list_models.assert_called_once()


@pytest.mark.asyncio
@pytest.mark.unit  
class TestChatCompletion:
    """Test chat completion functionality."""
    
    async def test_chat_completion_single_model_success(self, router_service, sample_chat_request, mock_chat_completion_response):
        """Test successful chat completion with single model."""
        # Setup mock service
        service_mock = router_service._mock_services[0]
        service_mock.chat_completion.return_value = mock_chat_completion_response
        
        # Setup model cache
        router_service.model_cache["cerebras"] = ["llama3.1-8b"]
        
        response = await router_service.chat_completion(sample_chat_request)
        
        assert response.router["service"] == "cerebras"
        assert response.router["actual_model"] == "llama3.1-8b"
        assert response.router["requested_model"] == "llama3.1-8b"
        service_mock.chat_completion.assert_called_once()
        
    async def test_chat_completion_fallback_model_success(self, router_service, sample_fallback_chat_request, mock_chat_completion_response):
        """Test successful chat completion with model fallback."""
        # Setup mock services
        service1_mock = router_service._mock_services[0]  # cerebras
        service1_mock.chat_completion.return_value = mock_chat_completion_response
        
        # Setup model caches - cerebras doesn't have qwen3 but has gemma3
        router_service.model_cache["cerebras"] = ["gemma3", "llama3.1-8b"]  # No qwen3
        router_service.model_cache["openai"] = ["gpt-4o", "gpt-3.5-turbo"]  # No requested models
        router_service.model_cache["ollama"] = ["qwen3", "gemma3"]  # Has qwen3
        
        response = await router_service.chat_completion(sample_fallback_chat_request)
        
        # Should use cerebras with gemma3 (second option from fallback)
        assert response.router["service"] == "cerebras"
        assert response.router["actual_model"] == "gemma3"
        assert response.router["requested_model"] == "qwen3|gemma3|llama3.1-8b"
        assert response.router["model_options"] == ["qwen3", "gemma3", "llama3.1-8b"]
        
    async def test_chat_completion_service_failover(self, router_service, sample_chat_request, mock_chat_completion_response):
        """Test service failover when first service fails."""
        # Setup mock services
        service1_mock = router_service._mock_services[0]  # cerebras - will fail
        service2_mock = router_service._mock_services[1]  # openai - will succeed
        
        service1_mock.chat_completion.side_effect = HTTPException(status_code=503, detail="Service unavailable")
        service2_mock.chat_completion.return_value = mock_chat_completion_response
        
        # Setup model caches
        router_service.model_cache["cerebras"] = ["llama3.1-8b"]
        router_service.model_cache["openai"] = ["llama3.1-8b"]
        
        response = await router_service.chat_completion(sample_chat_request)
        
        # Should fail over to openai
        assert response.router["service"] == "openai"
        assert response.router["attempt"] == 2
        assert router_service.failover_count == 1
        
    async def test_chat_completion_all_services_fail(self, router_service, sample_chat_request):
        """Test when all services fail."""
        # Setup all mock services to fail
        for service_mock in router_service._mock_services:
            service_mock.chat_completion.side_effect = HTTPException(status_code=503, detail="Service unavailable")
        
        # Setup model caches
        for service_name, _ in router_service.services:
            router_service.model_cache[service_name] = ["llama3.1-8b"]
        
        with pytest.raises(HTTPException) as exc_info:
            await router_service.chat_completion(sample_chat_request)
            
        assert exc_info.value.status_code == 503
        assert "Service unavailable" in str(exc_info.value.detail)
        
    async def test_chat_completion_rate_limiting(self, router_service, sample_chat_request, mock_chat_completion_response):
        """Test rate limiting behavior."""
        # Setup rate limited service config
        router_service.service_configs[0].rate_limit_requests = 1
        router_service.service_configs[0].rate_limit_window = 60
        
        # Add request to make first service rate limited
        router_service._record_request("cerebras")
        
        # Setup mock services
        service2_mock = router_service._mock_services[1]  # openai
        service2_mock.chat_completion.return_value = mock_chat_completion_response
        
        # Setup model caches
        router_service.model_cache["cerebras"] = ["llama3.1-8b"]
        router_service.model_cache["openai"] = ["llama3.1-8b"]
        
        response = await router_service.chat_completion(sample_chat_request)
        
        # Should skip rate limited cerebras and use openai
        assert response.router["service"] == "openai"
        assert router_service.rate_limit_skips == 1
        
    async def test_chat_completion_no_supporting_services(self, router_service, sample_chat_request):
        """Test when no services support the requested model."""
        # Setup model caches where no service supports the requested model
        router_service.model_cache["cerebras"] = ["different-model"]
        router_service.model_cache["openai"] = ["other-model"]  
        router_service.model_cache["ollama"] = ["another-model"]
        
        with pytest.raises(HTTPException) as exc_info:
            await router_service.chat_completion(sample_chat_request)
            
        assert exc_info.value.status_code == 429
        assert "All configured services are rate limited" in str(exc_info.value.detail)


@pytest.mark.asyncio
@pytest.mark.unit
class TestListModels:
    """Test list models functionality."""
    
    async def test_list_models_success(self, router_service, cerebras_models_response, openai_models_response):
        """Test successful model listing from multiple services."""
        # Setup mock services
        service1_mock = router_service._mock_services[0]  # cerebras
        service2_mock = router_service._mock_services[1]  # openai
        service3_mock = router_service._mock_services[2]  # ollama
        
        service1_mock.list_models.return_value = cerebras_models_response
        service2_mock.list_models.return_value = openai_models_response
        service3_mock.list_models.side_effect = Exception("Service down")  # ollama fails
        
        response = await router_service.list_models()
        
        # Should combine models from working services
        assert len(response["data"]) == 4  # 2 from cerebras + 2 from openai
        assert response["router"]["working_services"] == 2
        assert response["router"]["total_services"] == 3
        
        # Check model caches were updated
        assert "cerebras" in router_service.model_cache
        assert "openai" in router_service.model_cache
        assert len(router_service.model_cache["cerebras"]) == 2
        assert len(router_service.model_cache["openai"]) == 2
        
    async def test_list_models_all_services_fail(self, router_service):
        """Test when all services fail to list models."""
        # Setup all mock services to fail
        for service_mock in router_service._mock_services:
            service_mock.list_models.side_effect = Exception("Service error")
            # Mock the fallback models method
            service_mock._get_fallback_models.return_value = {
                "object": "list", 
                "data": [{"id": "fallback-model", "object": "model", "created": 1234567890, "owned_by": "fallback"}]
            }
        
        response = await router_service.list_models()
        
        # Should return fallback models
        assert response["router"]["service"] == "combined_fallback"
        assert len(response["data"]) > 0  # Should have some fallback models
        
    async def test_list_models_preserves_openai_fields(self, router_service, cerebras_models_response):
        """Test that OpenAI standard fields are preserved."""
        # Setup mock service
        service1_mock = router_service._mock_services[0]
        service1_mock.list_models.return_value = cerebras_models_response
        
        response = await router_service.list_models()
        
        model = response["data"][0]
        # Standard OpenAI fields should be preserved
        assert model["id"] == "llama3.1-8b"  # Not modified
        assert model["owned_by"] == "Meta"   # Not modified
        assert model["object"] == "model"   # Not modified
        assert model["created"] == 1234567890  # Not modified
        
        # Additional router fields should be added
        assert model["service"] == "cerebras"
        assert model["backend_type"] == "cerebras"


@pytest.mark.unit
class TestRouterStats:
    """Test router statistics functionality."""
    
    def test_get_stats(self, router_service):
        """Test getting router statistics."""
        router_service.request_count = 10
        router_service.failover_count = 2
        router_service.rate_limit_skips = 1
        
        stats = router_service.get_stats()
        
        assert stats["total_requests"] == 10
        assert stats["total_failovers"] == 2
        assert stats["total_rate_limit_skips"] == 1
        assert "service_stats" in stats
        assert len(stats["service_stats"]) == 3
        
    def test_get_health(self, router_service):
        """Test getting router health status."""
        # Configure mock services with required attributes
        for i, (service_name, service) in enumerate(router_service.services):
            service.backend_type = router_service.service_configs[i].backend_type
            service.base_url = router_service.service_configs[i].base_url
            service.api_key = router_service.service_configs[i].api_key
        
        health = router_service.get_health()
        
        assert health["overall_status"] == "healthy"
        assert "services" in health
        assert len(health["services"]) == 3
        
    def test_reset_stats(self, router_service):
        """Test resetting router statistics."""
        # Set some stats
        router_service.request_count = 10
        router_service.failover_count = 2
        router_service.rate_limit_skips = 1
        
        router_service.reset_stats()
        
        assert router_service.request_count == 0
        assert router_service.failover_count == 0
        assert router_service.rate_limit_skips == 0
