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
Router service that manages multiple OpenAI-compatible services with failover and rate limiting.
"""
import time
import logging
from collections import deque, defaultdict
from typing import Dict, Any, List, Optional, Tuple, Deque
from fastapi import HTTPException

from .openai_service import OpenAIService
from .models import ChatCompletionRequest, ChatCompletionResponse
from .config import ServiceConfig

logger = logging.getLogger(__name__)


class RouterService:
    """Router that manages multiple OpenAI-compatible services with automatic failover."""
    
    def __init__(self, services: List[ServiceConfig]):
        """
        Initialize the router with a list of service configurations.
        
        Args:
            services: List of ServiceConfig objects, will be sorted by priority
        """
        if not services:
            raise ValueError("At least one service configuration is required")
        
        # Sort services by priority (lower number = higher priority)
        self.service_configs = sorted(services, key=lambda s: s.priority)
        
        # Initialize OpenAI services
        self.services: List[Tuple[str, OpenAIService]] = []
        
        for config in self.service_configs:
            try:
                service = OpenAIService(
                    backend_type=config.backend_type,
                    base_url=config.base_url,
                    api_key=config.api_key,
                    timeout=config.timeout
                )
                self.services.append((config.name, service))
                logger.info(f"Initialized service '{config.name}' ({config.backend_type}) with priority {config.priority}")
            except Exception as e:
                logger.error(f"Failed to initialize service '{config.name}': {str(e)}")
                # Don't add to services list if initialization fails
        
        if not self.services:
            raise ValueError("No services could be initialized successfully")
        
        # Metrics
        self.request_count = 0
        self.failover_count = 0
        self.rate_limit_skips = 0
        self.service_stats = {name: {"requests": 0, "failures": 0, "rate_limited": 0} for name, _ in self.services}
        
        # Rate limiting tracking - sliding window of request timestamps for each service
        self.request_timestamps: Dict[str, Deque[float]] = defaultdict(lambda: deque())
        
        # Model cache - tracks which models each service supports
        self.model_cache: Dict[str, List[str]] = {}  # service_name -> list of model IDs
        self.cache_last_updated: Dict[str, float] = {}  # service_name -> timestamp
        self.cache_ttl = 300  # Cache TTL in seconds (5 minutes)
    
    def _is_rate_limited(self, service_name: str, service_config: Any) -> bool:
        """
        Check if a service is currently rate limited.
        
        Args:
            service_name: Name of the service
            service_config: ServiceConfig object for the service
            
        Returns:
            True if the service is rate limited, False otherwise
        """
        if not service_config.has_rate_limit():
            return False
        
        current_time = time.time()
        window_start = current_time - service_config.rate_limit_window
        
        # Get or create timestamps deque for this service
        timestamps = self.request_timestamps[service_name]
        
        # Remove old timestamps that are outside the window
        while timestamps and timestamps[0] <= window_start:
            timestamps.popleft()
        
        # Check if we've reached the rate limit
        current_requests = len(timestamps)
        is_limited = current_requests >= service_config.rate_limit_requests
        
        if is_limited:
            logger.info(f"⚠️  Service '{service_name}' is rate limited: {current_requests}/{service_config.rate_limit_requests} requests in {service_config.rate_limit_window}s")
        
        return is_limited
    
    def _record_request(self, service_name: str) -> None:
        """Record a request for rate limiting purposes."""
        current_time = time.time()
        self.request_timestamps[service_name].append(current_time)
    
    def _update_model_cache(self, service_name: str, models: List[Dict[str, Any]]) -> None:
        """
        Update the model cache for a specific service.
        
        Args:
            service_name: Name of the service
            models: List of model dictionaries from the service
        """
        model_ids = [model.get("id", "") for model in models if model.get("id")]
        self.model_cache[service_name] = model_ids
        self.cache_last_updated[service_name] = time.time()
        logger.debug(f"Updated model cache for '{service_name}': {len(model_ids)} models")
    
    def _is_cache_valid(self, service_name: str) -> bool:
        """Check if the model cache for a service is still valid."""
        if service_name not in self.cache_last_updated:
            return False
        return (time.time() - self.cache_last_updated[service_name]) < self.cache_ttl
    
    def _service_supports_model(self, service_name: str, model_id: str) -> bool:
        """
        Check if a service supports a specific model.
        
        Args:
            service_name: Name of the service
            model_id: ID of the model to check
            
        Returns:
            True if the service supports the model, False otherwise
        """
        if service_name not in self.model_cache:
            return True  # If no cache, assume it might support it
        return model_id in self.model_cache[service_name]
    
    def _parse_model_options(self, model_string: str) -> List[str]:
        """
        Parse model string to extract fallback options.
        
        Args:
            model_string: Model string, possibly containing | for fallbacks
            
        Returns:
            List of model options in priority order
        """
        return [model.strip() for model in model_string.split("|")]
    
    def _get_best_model_for_service(self, service_name: str, model_options: List[str]) -> Optional[str]:
        """
        Get the best supported model for a service from the options list.
        
        Args:
            service_name: Name of the service
            model_options: List of model options in priority order
            
        Returns:
            The best supported model ID or None if none are supported
        """
        for model_option in model_options:
            if self._service_supports_model(service_name, model_option):
                return model_option
        return None
    
    async def _refresh_stale_caches(self) -> None:
        """
        Refresh model caches for services with stale or missing cache data.
        This ensures we have up-to-date model information for filtering.
        """
        for service_name, service in self.services:
            if not self._is_cache_valid(service_name):
                try:
                    logger.debug(f"Refreshing model cache for service '{service_name}'")
                    models = await service.list_models()
                    self._update_model_cache(service_name, models.get("data", []))
                except Exception as e:
                    logger.warning(f"Failed to refresh cache for service '{service_name}': {str(e)}")
                    # Continue with possibly stale or empty cache
        
    def _get_available_service_index(self) -> Optional[int]:
        """
        Find the first available service that is not rate limited.
        
        Returns:
            Index of the first available service, or None if all are rate limited
        """
        for i, (service_name, service) in enumerate(self.services):
            service_config = self.service_configs[i]
            
            if not self._is_rate_limited(service_name, service_config):
                return i
        
        return None
    
    async def chat_completion(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """
        Execute chat completion with rate limiting and automatic failover.
        
        Supports model fallback syntax: "model1|model2|model3" will try models in order
        based on what each service supports. Updates model cache when needed.
        """
        self.request_count += 1
        last_exception = None
        attempted_services = set()
        
        # Parse model options (support fallback syntax with |)
        model_options = self._parse_model_options(request.model)
        logger.info(f"Parsed model options: {model_options}")
        
        # Try to refresh cache for any services that don't have valid cache
        await self._refresh_stale_caches()
        
        while len(attempted_services) < len(self.services):
            # Find the first available service (not rate limited, not already attempted, and supports at least one model)
            selected_index = None
            selected_service_name = None
            selected_service = None
            selected_model = None
            
            for i, (service_name, service) in enumerate(self.services):
                if service_name in attempted_services:
                    continue
                    
                service_config = self.service_configs[i]
                
                # Check rate limiting
                if self._is_rate_limited(service_name, service_config):
                    self.service_stats[service_name]["rate_limited"] += 1
                    logger.info(f"⏭️  Skipping rate limited service '{service_name}'")
                    
                    # Skip this service but don't mark as attempted (it might become available later)
                    if len(attempted_services) == 0:  # Only count as rate_limit_skip on first attempt
                        self.rate_limit_skips += 1
                    continue
                
                # Check if service supports any of the requested model options
                best_model = self._get_best_model_for_service(service_name, model_options)
                if best_model is None:
                    logger.info(f"⏭️  Skipping service '{service_name}' - doesn't support any of: {model_options}")
                    # Mark as attempted since it can't fulfill this request
                    attempted_services.add(service_name)
                    continue
                
                # Service is available and supports the model
                selected_index = i
                selected_service_name = service_name
                selected_service = service
                selected_model = best_model
                logger.info(f"Selected service '{service_name}' will use model '{best_model}'")
                break
            
            # If no service is available (all are rate limited or attempted)
            if selected_index is None:
                # Check if all services are rate limited
                all_rate_limited = True
                for i, (service_name, service) in enumerate(self.services):
                    if service_name not in attempted_services:
                        service_config = self.service_configs[i]
                        if not self._is_rate_limited(service_name, service_config):
                            all_rate_limited = False
                            break
                
                if all_rate_limited:
                    logger.error(f"🚨 All services are rate limited or failed")
                    raise HTTPException(
                        status_code=429,
                        detail={
                            "error": {
                                "message": "All configured services are rate limited",
                                "type": "rate_limit_exceeded",
                                "attempted_services": len(attempted_services),
                                "total_services": len(self.services)
                            }
                        }
                    )
                else:
                    # All remaining services have been attempted and failed
                    break
            
            # Attempt to use the selected service
            try:
                attempt_number = len(attempted_services) + 1
                logger.info(f"Attempting chat completion with service '{selected_service_name}' (attempt {attempt_number}/{len(self.services)})")
                
                # Record the request for rate limiting BEFORE the actual call
                self._record_request(selected_service_name)
                
                # Track service usage
                self.service_stats[selected_service_name]["requests"] += 1
                
                # Create a copy of the request with the selected model
                modified_request = request.copy()
                modified_request.model = selected_model
                
                # Execute request with the service-specific model
                start_time = time.time()
                response = await selected_service.chat_completion(modified_request)
                duration = time.time() - start_time
                
                logger.info(f"✅ Success with service '{selected_service_name}' using model '{selected_model}' in {duration:.2f}s")
                
                # Add router metadata to response
                response.router = {
                    "service": selected_service_name,
                    "attempt": attempt_number,
                    "duration": round(duration, 3),
                    "backend_type": self.service_configs[selected_index].backend_type,
                    "requested_model": request.model,
                    "actual_model": selected_model,
                    "model_options": model_options
                }
                
                return response
                
            except HTTPException as e:
                logger.warning(f"❌ Service '{selected_service_name}' failed: HTTP {e.status_code} - {e.detail}")
                
                # Track failure
                self.service_stats[selected_service_name]["failures"] += 1
                last_exception = e
                attempted_services.add(selected_service_name)
                
                # Continue to try next available service
                if len(attempted_services) < len(self.services):
                    self.failover_count += 1
                    logger.info(f"🔄 Failing over to next available service...")
                    continue
                    
            except Exception as e:
                logger.error(f"❌ Service '{selected_service_name}' failed with unexpected error: {str(e)}")
                
                # Track failure
                self.service_stats[selected_service_name]["failures"] += 1
                attempted_services.add(selected_service_name)
                
                # Convert to HTTPException
                last_exception = HTTPException(
                    status_code=500,
                    detail={
                        "error": {
                            "message": f"Service '{selected_service_name}' failed: {str(e)}",
                            "type": "service_error",
                            "service": selected_service_name
                        }
                    }
                )
                
                # Continue to try next available service
                if len(attempted_services) < len(self.services):
                    self.failover_count += 1
                    logger.info(f"🔄 Failing over to next available service...")
                    continue
        
        # All services failed or are rate limited
        logger.error(f"🚨 All {len(self.services)} services failed or are unavailable")
        
        # Raise the last exception, or create a generic one
        if last_exception:
            raise last_exception
        else:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": {
                        "message": "All configured services are unavailable",
                        "type": "service_unavailable",
                        "attempted_services": len(attempted_services),
                        "total_services": len(self.services)
                    }
                }
            )
    
    async def list_models(self) -> Dict[str, Any]:
        """
        List models from all working services.
        
        Combines models from all services that respond successfully.
        """
        combined_models = []
        successful_services = []
        
        for i, (service_name, service) in enumerate(self.services):
            try:
                logger.info(f"Attempting to list models from service '{service_name}'")
                models = await service.list_models()
                
                # Add models from this service with service identifier
                for model in models.get("data", []):
                    model_copy = model.copy()
                    # Add service info to each model (without modifying OpenAI standard fields)
                    model_copy["service"] = service_name
                    model_copy["backend_type"] = self.service_configs[i].backend_type
                    
                    combined_models.append(model_copy)
                
                successful_services.append({
                    "name": service_name,
                    "backend_type": self.service_configs[i].backend_type,
                    "models_count": len(models.get("data", []))
                })
                
                # Update model cache for this service
                self._update_model_cache(service_name, models.get("data", []))
                
                logger.info(f"✅ Retrieved {len(models.get('data', []))} models from service '{service_name}'")
                
            except Exception as e:
                logger.warning(f"❌ Service '{service_name}' failed to list models: {str(e)}")
                continue
        
        # If we got models from any service, return combined results
        if combined_models:
            logger.info(f"Combined {len(combined_models)} models from {len(successful_services)} working services")
            return {
                "object": "list",
                "data": combined_models,
                "router": {
                    "services": successful_services,
                    "total_services": len(self.services),
                    "working_services": len(successful_services),
                    "combined_models": len(combined_models)
                }
            }
        
        # No services worked, return fallback
        logger.warning("All services failed to list models, returning fallback")
        return self._get_combined_fallback_models()
    
    def _get_combined_fallback_models(self) -> Dict[str, Any]:
        """Get combined fallback models from all configured services."""
        combined_models = []
        current_time = int(time.time())
        
        for i, (service_name, service) in enumerate(self.services):
            fallback_models = service._get_fallback_models()
            for model in fallback_models.get("data", []):
                # Add service identifier to model (without modifying OpenAI standard fields)
                model_copy = model.copy()
                model_copy["service"] = service_name
                model_copy["backend_type"] = self.service_configs[i].backend_type
                combined_models.append(model_copy)
        
        return {
            "object": "list",
            "data": combined_models,
            "router": {
                "service": "combined_fallback",
                "attempt": len(self.services),
                "backend_type": "fallback"
            }
        }
    
    def get_stats(self) -> Dict[str, Any]:
        """Get router statistics and service health."""
        # Calculate current rate limiting status
        rate_limiting_stats = {}
        for i, (service_name, _) in enumerate(self.services):
            service_config = self.service_configs[i]
            if service_config.has_rate_limit():
                current_time = time.time()
                window_start = current_time - service_config.rate_limit_window
                timestamps = self.request_timestamps[service_name]
                
                # Clean old timestamps
                while timestamps and timestamps[0] <= window_start:
                    timestamps.popleft()
                
                current_requests = len(timestamps)
                rate_limiting_stats[service_name] = {
                    "rate_limit": f"{service_config.rate_limit_requests}/{service_config.rate_limit_window}s",
                    "current_requests": current_requests,
                    "remaining_quota": max(0, service_config.rate_limit_requests - current_requests),
                    "is_rate_limited": current_requests >= service_config.rate_limit_requests,
                    "window_reset_in": round(service_config.rate_limit_window - (current_time - (timestamps[0] if timestamps else current_time)), 1) if timestamps else 0
                }
            else:
                rate_limiting_stats[service_name] = {
                    "rate_limit": "none",
                    "current_requests": 0,
                    "remaining_quota": "unlimited",
                    "is_rate_limited": False,
                    "window_reset_in": 0
                }
        
        return {
            "total_requests": self.request_count,
            "total_failovers": self.failover_count,
            "total_rate_limit_skips": self.rate_limit_skips,
            "failover_rate": round(self.failover_count / max(self.request_count, 1) * 100, 2),
            "rate_limit_skip_rate": round(self.rate_limit_skips / max(self.request_count, 1) * 100, 2),
            "configured_services": len(self.services),
            "service_stats": self.service_stats.copy(),
            "service_order": [name for name, _ in self.services],
            "rate_limiting": rate_limiting_stats
        }
    
    def get_health(self) -> Dict[str, Any]:
        """Get health status of all configured services."""
        health_status = {
            "overall_status": "healthy",
            "services": {}
        }
        
        unhealthy_count = 0
        
        for i, (service_name, service) in enumerate(self.services):
            stats = self.service_stats[service_name]
            
            # Simple health calculation based on recent failure rate
            total_requests = stats["requests"]
            failures = stats["failures"]
            
            if total_requests == 0:
                status = "unknown"
            else:
                failure_rate = failures / total_requests
                if failure_rate < 0.1:  # Less than 10% failure rate
                    status = "healthy"
                elif failure_rate < 0.5:  # Less than 50% failure rate
                    status = "degraded"
                else:
                    status = "unhealthy"
                    unhealthy_count += 1
            
            # Get rate limiting info for health
            service_config = self.service_configs[i]
            is_rate_limited = self._is_rate_limited(service_name, service_config) if service_config.has_rate_limit() else False
            
            health_info = {
                "status": status,
                "backend_type": service.backend_type,
                "base_url": service.base_url,
                "has_api_key": bool(service.api_key),
                "requests": total_requests,
                "failures": failures,
                "failure_rate": round(failure_rate * 100, 2) if total_requests > 0 else 0,
                "rate_limited_events": stats.get("rate_limited", 0),
                "is_currently_rate_limited": is_rate_limited
            }
            
            # Add rate limiting configuration if applicable
            if service_config.has_rate_limit():
                health_info["rate_limit_config"] = {
                    "max_requests": service_config.rate_limit_requests,
                    "window_seconds": service_config.rate_limit_window
                }
            
            health_status["services"][service_name] = health_info
        
        # Determine overall status
        if unhealthy_count == len(self.services):
            health_status["overall_status"] = "unhealthy"
        elif unhealthy_count > 0:
            health_status["overall_status"] = "degraded"
        
        return health_status
    
    def reset_stats(self) -> None:
        """Reset all statistics."""
        self.request_count = 0
        self.failover_count = 0
        self.rate_limit_skips = 0
        self.service_stats = {name: {"requests": 0, "failures": 0, "rate_limited": 0} for name, _ in self.services}
        
        # Clear rate limiting timestamps but keep the deque structure
        for service_name in self.request_timestamps:
            self.request_timestamps[service_name].clear()
        
        logger.info("Router statistics reset")
    
    def __repr__(self) -> str:
        return f"RouterService(services={len(self.services)}, requests={self.request_count}, failovers={self.failover_count})"
