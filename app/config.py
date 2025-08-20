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
Configuration management for the LLM router.
"""
import os
import json
from typing import Optional, Literal, List, Dict, Any
from pydantic import Field, validator
from pydantic_settings import BaseSettings

BackendType = Literal["openai", "cerebras", "deepinfra", "ollama", "custom"]


class ServiceConfig:
    """Configuration for a single OpenAI service."""
    
    def __init__(
        self,
        name: str,
        backend_type: BackendType,
        base_url: str,
        api_key: Optional[str] = None,
        timeout: int = 60,
        priority: int = 0,
        rate_limit_requests: Optional[int] = None,
        rate_limit_window: int = 60
    ):
        self.name = name
        self.backend_type = backend_type
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout
        self.priority = priority  # Lower number = higher priority
        
        # Rate limiting configuration
        self.rate_limit_requests = rate_limit_requests  # Max requests in time window (None = no limit)
        self.rate_limit_window = rate_limit_window      # Time window in seconds
    
    def has_rate_limit(self) -> bool:
        """Check if this service has rate limiting enabled."""
        return self.rate_limit_requests is not None and self.rate_limit_requests > 0
    
    def __repr__(self) -> str:
        rate_info = f", rate_limit={self.rate_limit_requests}/{self.rate_limit_window}s" if self.has_rate_limit() else ""
        return f"ServiceConfig(name='{self.name}', type='{self.backend_type}', priority={self.priority}{rate_info})"


class Settings(BaseSettings):
    """Application settings."""

    # Cerebras specific env vars
    cerebras_api_key: Optional[str] = Field(
        None, description="Cerebras API key"
    )
    cerebras_base_url: str = Field(
        "https://api.cerebras.ai/v1", 
        description="Cerebras API base URL"
    )
    cerebras_rate_limit_requests: int = Field(30, description="Cerebras rate limit requests")
    cerebras_rate_limit_window: int = Field(60, description="Cerebras rate limit window in seconds")
    
    # DeepInfra specific
    deepinfra_token: Optional[str] = Field(
        None, description="DeepInfra API token"
    )
    deepinfra_base_url: str = Field(
        "https://api.deepinfra.com/v1/openai", 
        description="DeepInfra API base URL"
    )
    
    # OpenAI specific
    openai_api_key: Optional[str] = Field(
        None, description="OpenAI API key"
    )
    openai_base_url: str = Field(
        "https://api.openai.com/v1", 
        description="OpenAI API base URL"
    )
    
    # Local ollama specific
    ollama_base_url: str = Field(
        "http://localhost:11434/v1",
        description="Local ollama server base URL"
    )
    
    # Server configuration
    host: str = Field("0.0.0.0", description="Host to bind the server to")
    port: int = Field(8000, description="Port to bind the server to")
    
    # API configuration
    api_title: str = Field("LLM Router", description="API title")
    api_description: str = Field(
        "FastAPI application that replicates OpenAI API and forwards to multiple backends",
        description="API description"
    )
    api_version: str = Field("1.0.0", description="API version")
    
    # Request timeout
    request_timeout: int = Field(60, description="Request timeout in seconds")

    # Router configuration
    router_services: str = Field("", description="JSON string of router services configuration")
    
    # Authentication configuration
    enable_auth: bool = Field(True, description="Enable API key authentication")
    auth_header_name: str = Field("Authorization", description="HTTP header name for authentication")

    
    def get_router_services(self) -> List[ServiceConfig]:
        """
        Get router services configuration.
        
        Returns:
            List of ServiceConfig objects for the router
        """
        services = []
        
        if self.router_services:
            try:
                # Parse JSON configuration
                router_config = json.loads(self.router_services)
                
                for service_data in router_config:
                    service_config = ServiceConfig(
                        name=service_data["name"],
                        backend_type=service_data["backend_type"],
                        base_url=service_data["base_url"],
                        api_key=service_data.get("api_key"),
                        timeout=service_data.get("timeout", self.request_timeout),
                        priority=service_data.get("priority", 0),
                        rate_limit_requests=service_data.get("rate_limit_requests"),
                        rate_limit_window=service_data.get("rate_limit_window", 60)
                    )
                    services.append(service_config)
                    
                return services
                
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                import logging
                logging.warning(f"Failed to parse ROUTER_SERVICES JSON: {e}")
        
        # Fallback: create services from individual backend configurations
        return self._get_fallback_services()
    
    def _get_fallback_services(self) -> List[ServiceConfig]:
        """
        Create fallback services from individual backend configurations.
        Returns:
            List of ServiceConfig objects based on individual backend configs,
            in the order: cerebras, deepinfra, openai, ollama (cerebras/deepinfra/openai only if API_KEY exists, ollama always)
        """
        services = []
        priority = 0

        # Cerebras
        if self.cerebras_api_key:
            services.append(ServiceConfig(
                name="cerebras",
                backend_type="cerebras",
                base_url=self.cerebras_base_url,
                api_key=self.cerebras_api_key,
                timeout=self.request_timeout,
                priority=priority
            ))
            priority += 1

        # DeepInfra
        if self.deepinfra_token:
            services.append(ServiceConfig(
                name="deepinfra",
                backend_type="deepinfra",
                base_url=self.deepinfra_base_url,
                api_key=self.deepinfra_token,
                timeout=self.request_timeout,
                priority=priority
            ))
            priority += 1

        # OpenAI
        if self.openai_api_key:
            services.append(ServiceConfig(
                name="openai",
                backend_type="openai",
                base_url=self.openai_base_url,
                api_key=self.openai_api_key,
                timeout=self.request_timeout,
                priority=priority
            ))
            priority += 1

        # Ollama (always add)
        services.append(ServiceConfig(
            name="ollama",
            backend_type="ollama",
            base_url=self.ollama_base_url,
            api_key=None,
            timeout=self.request_timeout,
            priority=priority
        ))

        return services
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "ignore"
    }


# Global settings instance
settings = Settings()
