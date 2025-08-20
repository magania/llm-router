# 🤖 LLM Router

A FastAPI application that replicates the OpenAI API and forwards requests to multiple AI backends.

## ✨ Features

- **🔄 Multi-Backend Support**: OpenAI, Cerebras, Local Llama, and Custom APIs
- **🔌 OpenAI API Compatible**: Fully compatible with OpenAI's chat completions API
- **🛡️ Type Safety**: Fully typed Python code using Pydantic models
- **⚡ Smart Routing**: Automatically routes requests to the configured backend
- **🔧 Flexible Configuration**: Environment-based configuration with backend detection
- **📊 Error Handling**: Comprehensive error handling and logging
- **📚 Documentation**: Auto-generated API documentation with FastAPI

## 🎯 Supported Backends

| Backend | Description | API Key Required |
|---------|-------------|------------------|
| **Cerebras** | Cerebras AI API | ✅ Yes |
| **OpenAI** | Official OpenAI API | ✅ Yes |
| **Local Llama** | Local servers (llama.cpp, Ollama) | ✅ Yes |
| **Custom** | Any OpenAI-compatible API | Depends on API |

## 📋 Requirements

- Python 3.12+
- API key for your chosen backend (except local servers)

## 🚀 Quick Start

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure your backend

Create a `.env` file in the project root:

#### For Cerebras (Default)
```env
CEREBRAS_API_KEY=your_cerebras_api_key_here
```

#### For OpenAI
```env
OPENAI_API_KEY=sk-your_openai_api_key_here
```

#### For Local Server
```env
OLLAMA_BASE_URL=http://localhost:11434
```

### 3. Run the server
```bash
python main.py
```

🎉 Your API is now running at `http://localhost:8000`!

## Usage

### Running the Server

Start the FastAPI server:

```bash
python app.py
```

Or using uvicorn directly:

```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
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

List available models from Cerebras.

```bash
curl "http://localhost:8000/v1/models"
```

#### Get Model

**GET** `/v1/models/{model_id}`

Get information about a specific model.

```bash
curl "http://localhost:8000/v1/models/llama3.1-8b"
```

#### Health Check

**GET** `/health`

Check if the service is running.

```bash
curl "http://localhost:8000/health"
```

## Using with OpenAI Client Libraries

You can use this service as a drop-in replacement for OpenAI by changing the base URL:

### Python (openai library)

```python
import openai

client = openai.OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed"  # Cerebras key is configured on server
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
  -d '{
    "model": "llama3.1-8b",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

## Configuration

The application uses the following environment variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CEREBRAS_API_KEY` | Yes | - | Your Cerebras AI API key |
| `CEREBRAS_BASE_URL` | No | `https://api.cerebras.ai/v1` | Cerebras API base URL |
| `HOST` | No | `0.0.0.0` | Host to bind the server to |
| `PORT` | No | `8000` | Port to bind the server to |
| `REQUEST_TIMEOUT` | No | `60` | Request timeout in seconds |

## Supported Models

The application forwards requests to Cerebras and supports all models available through their API. Common models include:

- `llama3.1-8b`
- `llama3.1-70b`

Use the `/v1/models` endpoint to get the current list of available models.

## Error Handling

The application provides comprehensive error handling:

- **401 Unauthorized**: Missing or invalid Cerebras API key
- **404 Not Found**: Model not found
- **502 Bad Gateway**: Connection error to Cerebras API
- **504 Gateway Timeout**: Request to Cerebras API timed out
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

## Logging

The application logs important events including:

- Incoming requests
- Successful completions
- Errors and exceptions
- Model retrievals

Logs are written to stdout and can be configured through Python's logging system.

## Development

### Project Structure

```
llm-router/
├── app.py                 # Main FastAPI application
├── models.py             # Pydantic models for API compatibility
├── cerebras_service.py   # Service for Cerebras API integration
├── config.py             # Configuration management
├── requirements.txt      # Python dependencies
└── README.md            # This file
```

### Adding New Features

1. Add new Pydantic models to `models.py`
2. Extend the `CerebrasService` class for new API integrations
3. Add new endpoints to `app.py`
4. Update configuration in `config.py` if needed

## License

This project is open source and available under the MIT License.
