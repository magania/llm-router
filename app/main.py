"""
Entry point for the LLM Router application.
"""
import uvicorn
from .config import settings

if __name__ == "__main__":
    uvicorn.run(
        "app.app:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info"
    )
