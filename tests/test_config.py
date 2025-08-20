"""
Tests for configuration functionality.
"""
import pytest
import json
from unittest.mock import patch, MagicMock

from app.config import Settings, ServiceConfig, BackendType


@pytest.mark.unit
class TestServiceConfig:
    """Test ServiceConfig functionality."""
    
    def test_service_config_init(self):
        """Test ServiceConfig initialization."""
        config = ServiceConfig(
            name="test-service",
            backend_type="openai",
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            timeout=30,
            priority=1,
            rate_limit_requests=10,
            rate_limit_window=60
        )
        
        assert config.name == "test-service"
        assert config.backend_type == "openai"
        assert config.base_url == "https://api.openai.com/v1"
        assert config.api_key == "test-key"
        assert config.timeout == 30
        assert config.priority == 1
        assert config.rate_limit_requests == 10
        assert config.rate_limit_window == 60
        
    def test_service_config_defaults(self):
        """Test ServiceConfig default values."""
        config = ServiceConfig(
            name="test-service",
            backend_type="cerebras",
            base_url="https://api.cerebras.ai/v1"
        )
        
        assert config.api_key is None
        assert config.timeout == 60
        assert config.priority == 0
        assert config.rate_limit_requests is None
        assert config.rate_limit_window == 60
        
    def test_has_rate_limit_true(self):
        """Test has_rate_limit when rate limit is configured."""
        config = ServiceConfig(
            name="test",
            backend_type="openai",
            base_url="test",
            rate_limit_requests=10,
            rate_limit_window=60
        )
        
        assert config.has_rate_limit() is True
        
    def test_has_rate_limit_false_none(self):
        """Test has_rate_limit when rate limit is None."""
        config = ServiceConfig(
            name="test",
            backend_type="openai",
            base_url="test",
            rate_limit_requests=None
        )
        
        assert config.has_rate_limit() is False
        
    def test_has_rate_limit_false_zero(self):
        """Test has_rate_limit when rate limit is zero."""
        config = ServiceConfig(
            name="test",
            backend_type="openai",
            base_url="test",
            rate_limit_requests=0
        )
        
        assert config.has_rate_limit() is False
        
    def test_service_config_repr(self):
        """Test ServiceConfig string representation."""
        config = ServiceConfig(
            name="test-service",
            backend_type="openai",
            base_url="test",
            priority=1,
            rate_limit_requests=10,
            rate_limit_window=60
        )
        
        repr_str = repr(config)
        assert "test-service" in repr_str
        assert "openai" in repr_str
        assert "priority=1" in repr_str
        assert "rate_limit=10/60s" in repr_str


@pytest.mark.unit
class TestSettingsInit:
    """Test Settings initialization."""
    
    def test_settings_defaults(self):
        """Test Settings with default values."""
        with patch.dict('os.environ', {}, clear=True):
            settings = Settings()
            
            assert settings.cerebras_api_key is None
            assert settings.cerebras_base_url == "https://api.cerebras.ai/v1"
            assert settings.openai_api_key is None
            assert settings.openai_base_url == "https://api.openai.com/v1"
            assert settings.ollama_base_url == "http://localhost:11434"
            assert settings.request_timeout == 60
            assert settings.router_services == ""
            
    def test_settings_from_env_vars(self):
        """Test Settings loading from environment variables."""
        env_vars = {
            'CEREBRAS_API_KEY': 'cerebras-key',
            'CEREBRAS_BASE_URL': 'https://custom-cerebras.com/v1',
            'OPENAI_API_KEY': 'openai-key',
            'OPENAI_BASE_URL': 'https://custom-openai.com/v1',
            'OLLAMA_BASE_URL': 'http://custom-llama:8080',
            'REQUEST_TIMEOUT': '120',
            'ROUTER_SERVICES': '[]'
        }
        
        with patch.dict('os.environ', env_vars, clear=True):
            settings = Settings()
            
            assert settings.cerebras_api_key == 'cerebras-key'
            assert settings.cerebras_base_url == 'https://custom-cerebras.com/v1'
            assert settings.openai_api_key == 'openai-key'
            assert settings.openai_base_url == 'https://custom-openai.com/v1'
            assert settings.ollama_base_url == 'http://custom-llama:8080'
            assert settings.request_timeout == 120
            assert settings.router_services == '[]'





@pytest.mark.unit
class TestRouterServices:
    """Test router services configuration."""
    
    def test_get_router_services_from_json(self):
        """Test parsing router services from JSON string."""
        router_json = json.dumps([
            {
                "name": "cerebras",
                "backend_type": "cerebras",
                "base_url": "https://api.cerebras.ai/v1",
                "api_key": "cerebras-key",
                "priority": 0,
                "rate_limit_requests": 10,
                "rate_limit_window": 60
            },
            {
                "name": "openai",
                "backend_type": "openai", 
                "base_url": "https://api.openai.com/v1",
                "api_key": "openai-key",
                "priority": 1
            }
        ])
        
        settings = Settings(router_services=router_json)
        services = settings.get_router_services()
        
        assert len(services) == 2
        assert services[0].name == "cerebras"
        assert services[0].backend_type == "cerebras"
        assert services[0].priority == 0
        assert services[0].rate_limit_requests == 10
        assert services[1].name == "openai"
        assert services[1].backend_type == "openai"
        assert services[1].priority == 1
        assert services[1].rate_limit_requests is None
        
    def test_get_router_services_fallback_to_individual_configs(self):
        """Test fallback to individual service configs when JSON is empty."""
        settings = Settings(
            router_services="",  # Empty JSON
            cerebras_api_key="cerebras-key",
            cerebras_base_url="https://api.cerebras.ai/v1",
            openai_api_key="openai-key",
            openai_base_url="https://api.openai.com/v1"
        )
        
        services = settings.get_router_services()
        
        assert len(services) >= 3  # Should have cerebras, openai, and ollama
        
        # Find services by name
        cerebras_service = next((s for s in services if s.name == "cerebras"), None)
        openai_service = next((s for s in services if s.name == "openai"), None)
        ollama_service = next((s for s in services if s.name == "ollama"), None)
        
        assert cerebras_service is not None
        assert cerebras_service.api_key == "cerebras-key"
        assert cerebras_service.base_url == "https://api.cerebras.ai/v1"
        
        assert openai_service is not None
        assert openai_service.api_key == "openai-key"
        assert openai_service.base_url == "https://api.openai.com/v1"
        
        assert ollama_service is not None
        assert ollama_service.api_key is None
        assert ollama_service.base_url == "http://localhost:11434"
        
    def test_get_router_services_invalid_json(self):
        """Test handling of invalid JSON in router services."""
        settings = Settings(router_services="invalid json {")
        
        # Should fallback to individual configs without raising exception
        services = settings.get_router_services()
        assert isinstance(services, list)
        
    def test_get_router_services_missing_required_fields(self):
        """Test handling of missing required fields in JSON."""
        router_json = json.dumps([
            {
                "name": "incomplete-service",
                # Missing backend_type and base_url
            }
        ])
        
        settings = Settings(router_services=router_json)
        
        # Should handle gracefully and may skip invalid services
        services = settings.get_router_services()
        assert isinstance(services, list)
        

        
    def test_get_router_services_with_custom_backend(self):
        """Test router services with custom backend type."""
        router_json = json.dumps([
            {
                "name": "custom-service",
                "backend_type": "custom",
                "base_url": "https://custom-api.example.com/v1",
                "api_key": "custom-key",
                "priority": 0,
                "timeout": 45
            }
        ])
        
        settings = Settings(router_services=router_json)
        services = settings.get_router_services()
        
        assert len(services) == 1
        assert services[0].name == "custom-service"
        assert services[0].backend_type == "custom"
        assert services[0].base_url == "https://custom-api.example.com/v1"
        assert services[0].api_key == "custom-key"
        assert services[0].timeout == 45


@pytest.mark.unit
class TestBackendTypes:
    """Test backend type validation."""
    
    def test_valid_backend_types(self):
        """Test that all defined backend types are valid."""
        valid_types = ["openai", "cerebras", "ollama", "custom"]
        
        for backend_type in valid_types:
            config = ServiceConfig(
                name="test",
                backend_type=backend_type,
                base_url="test"
            )
            assert config.backend_type == backend_type
            
    def test_backend_type_literal(self):
        """Test BackendType literal type."""
        # This test ensures the BackendType literal is properly defined
        from app.config import BackendType
        
        # Should be able to use as type annotation
        def test_function(backend: BackendType) -> str:
            return backend
            
        assert test_function("openai") == "openai"
        assert test_function("cerebras") == "cerebras"
        assert test_function("ollama") == "ollama"
        assert test_function("custom") == "custom"


@pytest.mark.integration
class TestSettingsIntegration:
    """Integration tests for Settings with environment variables."""
    
    def test_full_configuration_from_env(self):
        """Test complete configuration from environment variables."""
        router_services_json = json.dumps([
            {
                "name": "primary",
                "backend_type": "cerebras",
                "base_url": "https://api.cerebras.ai/v1",
                "api_key": "cerebras-key",
                "priority": 0,
                "rate_limit_requests": 5,
                "rate_limit_window": 30
            },
            {
                "name": "fallback",
                "backend_type": "openai",
                "base_url": "https://api.openai.com/v1", 
                "api_key": "openai-key",
                "priority": 1,
                "timeout": 45
            }
        ])
        
        env_vars = {
            'ROUTER_SERVICES': router_services_json,
            'REQUEST_TIMEOUT': '90'
        }
        
        with patch.dict('os.environ', env_vars, clear=True):
            settings = Settings()
            services = settings.get_router_services()
            
            assert len(services) == 2
            assert settings.request_timeout == 90
            
            # Verify first service
            primary = services[0]
            assert primary.name == "primary"
            assert primary.backend_type == "cerebras"
            assert primary.priority == 0
            assert primary.rate_limit_requests == 5
            assert primary.rate_limit_window == 30
            
            # Verify second service
            fallback = services[1]
            assert fallback.name == "fallback"
            assert fallback.backend_type == "openai"
            assert fallback.priority == 1
            assert fallback.timeout == 45
