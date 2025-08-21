# 🔧 LLM Router Configuration Guide

El LLM Router ahora soporta múltiples backends de APIs compatibles con OpenAI. Aquí tienes la guía completa de configuración.

## 🎯 Backends Soportados

- **OpenAI**: API oficial de OpenAI
- **Cerebras**: API de Cerebras AI (por defecto)
- **Ollama**: Servidores locales como llama.cpp, Ollama, etc.
- **Custom**: Cualquier API compatible con OpenAI

## 📁 Archivo .env

Crea un archivo `.env` en la raíz del proyecto con la configuración que necesites:

### 🔹 Configuración Básica

```env
# Selecciona el backend (obligatorio)
BACKEND_TYPE=cerebras

# Configuración del servidor
HOST=0.0.0.0
PORT=8000
REQUEST_TIMEOUT=60
```

### 🔹 Configuración por Backend

#### 1. Cerebras (Recomendado)
```env
BACKEND_TYPE=cerebras
CEREBRAS_API_KEY=your_cerebras_api_key_here
# CEREBRAS_BASE_URL=https://api.cerebras.ai/v1  # Opcional
```

#### 2. OpenAI
```env
BACKEND_TYPE=openai
OPENAI_API_KEY=sk-your_openai_api_key_here
# OPENAI_BASE_URL=https://api.openai.com/v1  # Opcional
```

#### 3. Ollama Server
```env
BACKEND_TYPE=ollama
OLLAMA_BASE_URL=http://localhost:11434/v1
# OLLAMA_AUTH_KEY=your_ollama_auth_key_here  # Only needed if your Ollama setup requires authentication
```

#### 4. Custom Backend
```env
BACKEND_TYPE=custom
API_KEY=your_custom_api_key
BASE_URL=https://your-backend.com/v1
```

### 🔹 Configuración Genérica (Alternativa)

También puedes usar variables genéricas que funcionan con cualquier backend:

```env
BACKEND_TYPE=your_backend_type
API_KEY=your_api_key
BASE_URL=https://your-backend-url.com/v1
```

## 🚀 Uso del Servicio

### Iniciar el servidor
```bash
python main.py
```

### Endpoints disponibles
- **API Base**: `http://localhost:8000`
- **Documentación**: `http://localhost:8000/docs`
- **Información del backend**: `GET /backend/info`
- **Chat Completions**: `POST /v1/chat/completions`
- **Modelos**: `GET /v1/models`

## 🧪 Ejemplos de Prueba

### 1. Verificar backend actual
```bash
curl "http://localhost:8000/backend/info"
```

### 2. Listar modelos disponibles
```bash
curl "http://localhost:8000/v1/models"
```

### 3. Chat completion
```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "llama3.1-8b",
    "messages": [{"role": "user", "content": "Hello!"}],
    "temperature": 0.7
  }'
```

## 📖 Compatibilidad con Clientes OpenAI

### Python (openai library)
```python
import openai

client = openai.OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="not-needed"  # La API key se configura en el servidor
)

response = client.chat.completions.create(
    model="llama3.1-8b",
    messages=[{"role": "user", "content": "Hello!"}]
)
```

### JavaScript/Node.js
```javascript
import OpenAI from 'openai';

const client = new OpenAI({
  baseURL: 'http://localhost:8000/v1',
  apiKey: 'not-needed' // La API key se configura en el servidor
});

const response = await client.chat.completions.create({
  model: 'llama3.1-8b',
  messages: [{ role: 'user', content: 'Hello!' }]
});
```

## 🔄 Cambiar Backend en Tiempo de Ejecución

Para cambiar de backend, simplemente:

1. Modifica la variable `BACKEND_TYPE` en tu `.env`
2. Configura las variables correspondientes (API key, URL)
3. Reinicia el servidor

## 🛠️ Configuraciones Populares

### Para Desarrollo Local
```env
BACKEND_TYPE=ollama
OLLAMA_BASE_URL=http://localhost:8080
PORT=8000
```

### Para Producción con Cerebras
```env
BACKEND_TYPE=cerebras
CEREBRAS_API_KEY=your_production_key
HOST=0.0.0.0
PORT=8000
REQUEST_TIMEOUT=120
```

### Para Testing con OpenAI
```env
BACKEND_TYPE=openai
OPENAI_API_KEY=sk-your_test_key
REQUEST_TIMEOUT=30
```

## ⚠️ Notas Importantes

1. **API Keys**: Solo son obligatorias para OpenAI y Cerebras
2. **Ollama servers**: No necesitan API key por defecto, solo la URL del servidor. Solo se agregan al router si están configurados.
3. **Timeout**: Ajusta según la velocidad de tu backend
4. **URL Format**: Las URLs deben incluir el protocolo (http/https)

## 🐛 Troubleshooting

### Error: "No API key provided"
- Verifica que hayas configurado la API key correcta para tu backend
- Para Cerebras: `CEREBRAS_API_KEY`
- Para OpenAI: `OPENAI_API_KEY`

### Error: "Connection error"
- Verifica que la URL del backend sea correcta
- Para servers locales, asegúrate de que estén ejecutándose

### Backend no reconocido
- Verifica que `BACKEND_TYPE` sea uno de: `openai`, `cerebras`, `ollama`, `custom`
