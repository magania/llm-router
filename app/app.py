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
FastAPI application that replicates OpenAI API and forwards to multiple LLM backends.
"""
import time
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
from typing import Dict, Any

from .config import settings
from .models import (
    ChatCompletionRequest, 
    ChatCompletionResponse,
)
from .router_service import RouterService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title=settings.api_title,
    description=settings.api_description,
    version=settings.api_version,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global router instance (cached)
_router_instance = None

def get_router_service() -> RouterService:
    """Get router service instance (always uses router, even with single service)."""
    global _router_instance
    
    if _router_instance is None:
        services = settings.get_router_services()
        if not services:
            raise ValueError("No services are configured")
        _router_instance = RouterService(services)
        logger.info(f"Initialized router with {len(services)} services: {[s.name for s in services]}")
    
    return _router_instance


@app.get("/", summary="Root endpoint")
async def root() -> Dict[str, Any]:
    """Root endpoint that provides basic API information."""
    services = settings.get_router_services()
    return {
        "message": "LLM Router - OpenAI API compatible endpoint",
        "version": settings.api_version,
        "docs": "/docs",
        "mode": "router",
        "services_count": len(services),
        "services": [{"name": s.name, "type": s.backend_type, "priority": s.priority} for s in services],
        "primary_backend": services[0].backend_type if services else "unknown"
    }


@app.get("/backend/info", summary="Backend information")
async def backend_info() -> Dict[str, Any]:
    """Get information about the current backend configuration."""
    router = get_router_service()
    return {
        "mode": "router",
        "status": "active",
        "router_stats": router.get_stats(),
        "health": router.get_health()
    }


@app.get("/health", summary="Health check")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint."""
    router = get_router_service()
    health = router.get_health()
    return {
        "status": health["overall_status"],
        "mode": "router",
        "details": health
    }


@app.get("/router/stats", summary="Router statistics")
async def router_stats() -> Dict[str, Any]:
    """Get router statistics."""
    router = get_router_service()
    return router.get_stats()


@app.get("/router/health", summary="Router health check")
async def router_health() -> Dict[str, Any]:
    """Get detailed health information for all services."""
    router = get_router_service()
    return router.get_health()


@app.post("/router/reset-stats", summary="Reset router statistics")
async def reset_router_stats() -> Dict[str, str]:
    """Reset router statistics."""
    router = get_router_service()
    router.reset_stats()
    return {"status": "success", "message": "Router statistics reset"}


@app.get("/router/rate-limits", summary="Rate limiting status")
async def router_rate_limits() -> Dict[str, Any]:
    """Get current rate limiting status for all services."""
    router = get_router_service()
    stats = router.get_stats()
    return {
        "rate_limiting": stats["rate_limiting"],
        "total_rate_limit_skips": stats["total_rate_limit_skips"],
        "rate_limit_skip_rate": stats["rate_limit_skip_rate"],
        "current_time": time.time()
    }


@app.post(
    "/v1/chat/completions",
    response_model=ChatCompletionResponse,
    summary="Create chat completion",
    description="Creates a model response for the given chat conversation."
)
async def create_chat_completion(
    request: ChatCompletionRequest,
    router: RouterService = Depends(get_router_service)
) -> ChatCompletionResponse:
    """
    Create a chat completion using the router.
    
    This endpoint is compatible with OpenAI's chat completions API.
    """
    try:
        logger.info(f"Received chat completion request for model: {request.model}")
        response = await router.chat_completion(request)
        logger.info(f"Successfully processed chat completion for model: {request.model}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error in chat completion: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"Internal server error: {str(e)}",
                    "type": "internal_error"
                }
            }
        )


@app.get(
    "/v1/models",
    summary="List models",
    description="Lists the currently available models."
)
async def list_models(
    router: RouterService = Depends(get_router_service)
) -> Dict[str, Any]:
    """
    List available models from the router.
    Compatible with OpenAI's models API.
    """
    try:
        models = await router.list_models()
        logger.info(f"Successfully retrieved {len(models.get('data', []))} models")
        return models
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"Failed to retrieve models: {str(e)}",
                    "type": "internal_error"
                }
            }
        )


@app.get(
    "/v1/models/{model_id}",
    summary="Retrieve model",
    description="Retrieves a model instance."
)
async def get_model(
    model_id: str,
    router: RouterService = Depends(get_router_service)
) -> Dict[str, Any]:
    """
    Get information about a specific model.
    
    This endpoint is compatible with OpenAI's model retrieval API.
    """
    try:
        logger.info(f"Received request for model: {model_id}")
        
        # Get all models and find the requested one
        models_response = await router.list_models()
        models = models_response.get("data", [])
        
        for model in models:
            if model.get("id") == model_id:
                logger.info(f"Found model: {model_id}")
                return model
        
        # Model not found
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "message": f"Model '{model_id}' not found",
                    "type": "not_found_error"
                }
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving model {model_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "message": f"Failed to retrieve model: {str(e)}",
                    "type": "internal_error"
                }
            }
        )


# Custom exception handler for better error responses
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    """Custom exception handler for HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.detail if isinstance(exc.detail, dict) else {"error": {"message": str(exc.detail)}}
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    """Custom exception handler for general exceptions."""
    logger.error(f"Unhandled exception: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "message": "Internal server error",
                "type": "internal_error"
            }
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting LLM Router on {settings.host}:{settings.port}")
    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info"
    )
