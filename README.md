# 🤖 LLM Router

A FastAPI application that replicates the OpenAI API and forwards requests to multiple AI backends with automatic failover and rate limiting.

## ✨ Features

- **🔄 Multi-Backend Router**: Route requests to multiple AI services with priority-based failover
- **🔌 OpenAI API Compatible**: Fully compatible with OpenAI's chat completions API
- **🛡️ Type Safety**: Fully typed Python code using Pydantic models
- **⚡ Smart Routing**: Automatically routes requests to the best available backend
- **🔧 Flexible Configuration**: Environment-based configuration with advanced router settings
- **📊 Error Handling**: Comprehensive error handling and logging
- **📚 Documentation**: Auto-generated API documentation with FastAPI
- **🔒 Authentication System**: Built-in API key authentication with metrics
- **📏 Rate Limiting**: Per-service rate limiting with sliding window algorithm
- **🏥 Health Monitoring**: Service health checks and detailed statistics

## 🎯 Supported Backends

| Backend | Description | API Key Required |
|---------|-------------|------------------|
| **OpenAI** | Official OpenAI API | ✅ Yes |
| **Cerebras** | Cerebras AI API | ✅ Yes |
| **DeepInfra** | DeepInfra API | ✅ Yes |
| **Ollama** | Local Ollama servers | ✅ Yes|
| **Custom** | Any OpenAI-compatible API | Depends on API |

## 📋 Requirements

- Python 3.12+
- API keys for your chosen backends (except local servers like Ollama)

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure your backends

Create a `.env` file in the project root:

#### Simple Configuration (Auto Router)
```env
# Router will automatically activate with multiple backends
CEREBRAS_API_KEY=your_cerebras_api_key_here
OPENAI_API_KEY=sk-your_openai_api_key_here
# Ollama works without API key
OLLAMA_BASE_URL=http://localhost:11434/v1
```

#### Advanced Router Configuration
```env
ROUTER_SERVICES='[
  {
    "name": "primary-cerebras",
    "backend_type": "cerebras",
    "base_url": "https://api.cerebras.ai/v1",
    "api_key": "your_cerebras_key",
    "priority": 0,
    "rate_limit_requests": 100,
    "rate_limit_window": 60
  },
  {
    "name": "fallback-openai", 
    "backend_type": "openai",
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-your_openai_key",
    "priority": 1,
    "rate_limit_requests": 50,
    "rate_limit_window": 60
  }
]'
```

### 3. Configure Authentication (Optional)
```env
# Single key
AUTH_KEY=sk-your-secret-api-key

# Multiple keys
AUTH_KEY_01=sk-user1-key
AUTH_KEY_02=sk-user2-key
# ... up to AUTH_KEY_99

# Disable authentication (for development)
ENABLE_AUTH=false
```

### 4. Run the server
```bash
python main.py
```

🎉 Your API is now running at `http://localhost:8000`!

## Usage

### Running the Server

Start the FastAPI server:

```bash
python main.py
```

Or using uvicorn directly:

```bash
uvicorn app.app:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at:
- **API Base URL**: `http://localhost:8000`
- **Documentation**: `http://localhost:8000/docs`
- **Alternative Docs**: `http://localhost:8000/redoc`

### API Endpoints

#### Chat Completions

**POST** `/v1/chat/completions`

Create a chat completion. Compatible with OpenAI's API.

Example request:

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "llama3.1-8b",
    "messages": [
      {
        "role": "user",
        "content": "Hello, how are you?"
      }
    ],
    "temperature": 0.7,
    "max_tokens": 150
  }'
```

#### List Models

**GET** `/v1/models`

List available models from all configured backends.

```bash
curl -H "Authorization: Bearer your-api-key" \
  "http://localhost:8000/v1/models"
```

#### Get Model

**GET** `/v1/models/{model_id}`

Get information about a specific model.

```bash
curl -H "Authorization: Bearer your-api-key" \
  "http://localhost:8000/v1/models/llama3.1-8b"
```

#### Health Check

**GET** `/health`

Check if the service is running.

```bash
curl "http://localhost:8000/health"
```

### Router-Specific Endpoints

#### Router Information
```bash
# Basic info
curl "http://localhost:8000/"

# Detailed backend info
curl "http://localhost:8000/backend/info"

# Router statistics
curl -H "Authorization: Bearer your-api-key" \
  "http://localhost:8000/router/stats"

# Router health
curl -H "Authorization: Bearer your-api-key" \
  "http://localhost:8000/router/health"

# Rate limiting status
curl -H "Authorization: Bearer your-api-key" \
  "http://localhost:8000/router/rate-limits"
```

#### Authentication Endpoints
```bash
# Authentication status
curl -H "Authorization: Bearer your-api-key" \
  "http://localhost:8000/auth/status"

# Authentication metrics
curl -H "Authorization: Bearer your-api-key" \
  "http://localhost:8000/auth/metrics"

# Reload authentication keys
curl -X POST -H "Authorization: Bearer your-api-key" \
  "http://localhost:8000/auth/reload-keys"
```

## Using with OpenAI Client Libraries

You can use this service as a drop-in replacement for OpenAI by changing the base URL:

### Python (openai library)

```python
import openai

client = openai.OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="your-api-key"  # Required if authentication is enabled
)

response = client.chat.completions.create(
    model="llama3.1-8b",
    messages=[
        {"role": "user", "content": "Hello!"}
    ]
)

print(response.choices[0].message.content)
```

### curl

```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer your-api-key" \
  -d '{
    "model": "llama3.1-8b",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Configuration

The application uses environment variables for configuration. See [CONFIGURATION.md](CONFIGURATION.md) and [ROUTER_EXAMPLES.md](ROUTER_EXAMPLES.md) for detailed configuration options.

### Router Configuration

The application can operate in two modes:
1. **Auto Router**: Automatically activates when multiple backends are configured
2. **Explicit Router**: Uses JSON configuration via `ROUTER_SERVICES`

### Authentication Configuration

See [AUTHENTICATION.md](AUTHENTICATION.md) for detailed authentication configuration.

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ROUTER_SERVICES` | No | - | JSON configuration for router services |
| `CEREBRAS_API_KEY` | No | - | Your Cerebras AI API key |
| `OPENAI_API_KEY` | No | - | Your OpenAI API key |
| `DEEPINFRA_TOKEN` | No | - | Your DeepInfra API token |
| `OLLAMA_BASE_URL` | No | `http://localhost:11434/v1` | Ollama API base URL |
| `HOST` | No | `0.0.0.0` | Host to bind the server to |
| `PORT` | No | `8000` | Port to bind the server to |
| `REQUEST_TIMEOUT` | No | `60` | Request timeout in seconds |
| `AUTH_KEY` | No | - | Single API key for authentication |
| `ENABLE_AUTH` | No | `true` | Enable/disable authentication |
| `AUTH_HEADER_NAME` | No | `Authorization` | HTTP header name for authentication |

## Supported Models

The application forwards requests to configured backends and supports all models available through those APIs. Common models include:

- `llama3.1-8b`
- `llama3.1-70b`
- `gpt-3.5-turbo`
- `gpt-4`

Use the `/v1/models` endpoint to get the current list of available models.

## Error Handling

The application provides comprehensive error handling:

- **401 Unauthorized**: Missing or invalid API key
- **404 Not Found**: Model not found
- **429 Rate Limited**: All configured services are rate limited
- **502 Bad Gateway**: Connection error to backend API
- **503 Service Unavailable**: All configured services are unavailable
- **504 Gateway Timeout**: Request to backend API timed out
- **500 Internal Server Error**: Unexpected server error

All errors are returned in OpenAI-compatible format:

```json
{
  "error": {
    "message": "Error description",
    "type": "error_type"
  }
}
```

## Rate Limiting

The router implements per-service rate limiting with a sliding window algorithm:

- **Per-Service Limits**: Each backend can have its own rate limits
- **Automatic Failover**: If a service is rate limited, requests automatically route to the next available service
- **Real-time Monitoring**: Track rate limiting status via `/router/rate-limits` endpoint
- **Configurable Windows**: Set custom time windows for rate limiting

## Authentication System

The application includes a built-in authentication system:

- **Multiple Keys**: Support for multiple API keys
- **Metrics**: Track API key usage and success rates
- **Real-time Reload**: Reload keys without restarting the server
- **Security**: Keys are masked in logs and metrics

See [AUTHENTICATION.md](AUTHENTICATION.md) for detailed authentication documentation.

## Logging

The application logs important events including:

- Incoming requests
- Successful completions
- Errors and exceptions
- Model retrievals
- Authentication events
- Router decisions

Logs are written to stdout and can be configured through Python's logging system.

## Project Structure

```
llm-router/
├── app/
│   ├── __init__.py
│   ├── app.py              # Main FastAPI application
│   ├── auth_service.py     # Authentication service
│   ├── config.py           # Configuration management
│   ├── main.py             # App entry point
│   ├── models.py           # Pydantic models
│   ├── openai_service.py   # OpenAI service integration
│   └── router_service.py   # Router service for multiple backends
├── tests/                  # Test suite
├── main.py                 # Project entry point
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker configuration
├── AUTHENTICATION.md      # Authentication documentation
├── CONFIGURATION.md       # Configuration documentation
├── ROUTER_EXAMPLES.md     # Router configuration examples
├── DEPLOY.md              # Deployment guide
└── README.md              # This file
```

## Development

### Adding New Features

1. Add new Pydantic models to `app/models.py`
2. Extend the service classes for new API integrations
3. Add new endpoints to `app/app.py`
4. Update configuration in `app/config.py` if needed
5. Add tests in the `tests/` directory

## Deployment

See [DEPLOY.md](DEPLOY.md) for detailed deployment instructions using Docker, Docker Swarm, or Kubernetes.

## License

This project is open source and available under the MIT License.
