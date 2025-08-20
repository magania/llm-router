# Autenticación LLM Router

Este documento describe el sistema de autenticación implementado en el LLM Router, que es compatible con la API de OpenAI.

## Configuración de Claves de API

### Variables de Entorno

El sistema de autenticación utiliza variables de entorno para cargar las claves válidas:

#### Opción 1: Clave única
```bash
export AUTH_KEY="tu-clave-api-secreta"
```

#### Opción 2: Múltiples claves (sin saltos)
```bash
export AUTH_KEY_01="primera-clave-api"
export AUTH_KEY_02="segunda-clave-api"
export AUTH_KEY_03="tercera-clave-api"
# ... hasta AUTH_KEY_99
```

### Lógica de Carga de Claves

1. **Si `AUTH_KEY` existe**: Solo esa clave será válida
2. **Si `AUTH_KEY` no existe**: El sistema buscará `AUTH_KEY_01`, `AUTH_KEY_02`, etc.
3. **Sin saltos**: Si falta `AUTH_KEY_03`, no se cargarán las claves siguientes (`AUTH_KEY_04`, etc.)

## Uso de la API

### Headers de Autenticación

Todas las solicitudes a los endpoints `/v1/*` requieren autenticación:

```bash
# Formato Bearer Token (recomendado)
curl -H "Authorization: Bearer tu-clave-api" \
     -H "Content-Type: application/json" \
     -d '{"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "Hello"}]}' \
     http://localhost:8000/v1/chat/completions

# Formato directo
curl -H "Authorization: tu-clave-api" \
     -H "Content-Type: application/json" \
     -d '{"model": "gpt-3.5-turbo", "messages": [{"role": "user", "content": "Hello"}]}' \
     http://localhost:8000/v1/chat/completions
```

### Endpoints Protegidos

Los siguientes endpoints requieren autenticación:
- `POST /v1/chat/completions`
- `GET /v1/models`
- `GET /v1/models/{model_id}`

### Endpoints No Protegidos

Los siguientes endpoints no requieren autenticación:
- `GET /` - Información básica
- `GET /health` - Health check
- `GET /backend/info` - Información del backend
- `GET /router/*` - Estadísticas del router
- `GET /auth/*` - Métricas de autenticación (excepto reset)

## Métricas de Autenticación

### Ver Métricas
```bash
curl http://localhost:8000/auth/metrics
```

Respuesta ejemplo:
```json
{
  "valid_keys_count": 3,
  "total_requests": 150,
  "total_success": 145,
  "total_errors": 5,
  "success_rate": 96.67,
  "active_keys": 2,
  "keys_metrics": {
    "abcd...wxyz": {
      "requests_count": 100,
      "success_count": 98,
      "error_count": 2,
      "first_request": 1704067200.0,
      "last_request": 1704070800.0,
      "success_rate": 98.0
    },
    "efgh...ijkl": {
      "requests_count": 50,
      "success_count": 47,
      "error_count": 3,
      "first_request": 1704068000.0,
      "last_request": 1704070500.0,
      "success_rate": 94.0
    }
  }
}
```

### Estado de Autenticación
```bash
curl http://localhost:8000/auth/status
```

### Recargar Claves
```bash
curl -X POST http://localhost:8000/auth/reload-keys
```

### Resetear Métricas
```bash
curl -X POST http://localhost:8000/auth/reset-metrics
```

## Configuración

### Deshabilitar Autenticación (para desarrollo)
```bash
export ENABLE_AUTH=false
```

### Cambiar Header de Autenticación
```bash
export AUTH_HEADER_NAME="X-API-Key"
```

## Compatibilidad con OpenAI

El sistema es completamente compatible con clientes OpenAI:

### Python con openai
```python
import openai

client = openai.OpenAI(
    api_key="tu-clave-api",
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[{"role": "user", "content": "Hello"}]
)
```

### JavaScript con openai
```javascript
import OpenAI from 'openai';

const openai = new OpenAI({
  apiKey: 'tu-clave-api',
  baseURL: 'http://localhost:8000/v1',
});

const chatCompletion = await openai.chat.completions.create({
  messages: [{ role: 'user', content: 'Hello' }],
  model: 'gpt-3.5-turbo',
});
```

## Códigos de Error

### 401 - Authentication Error

#### Missing API Key
```json
{
  "error": {
    "message": "Missing API key. Please provide a valid API key in the Authorization header.",
    "type": "authentication_error",
    "code": "missing_api_key"
  }
}
```

#### Invalid API Key
```json
{
  "error": {
    "message": "Invalid API key provided. Please check your API key and try again.",
    "type": "authentication_error",
    "code": "invalid_api_key"
  }
}
```

## Ejemplo de .env

```bash
# Opción 1: Clave única
AUTH_KEY=sk-abcd1234567890abcd1234567890abcd1234567890abcd12

# Opción 2: Múltiples claves
# AUTH_KEY_01=sk-user1-abcd1234567890abcd1234567890abcd1234567890
# AUTH_KEY_02=sk-user2-efgh1234567890efgh1234567890efgh1234567890
# AUTH_KEY_03=sk-user3-ijkl1234567890ijkl1234567890ijkl1234567890

# Configuración opcional
ENABLE_AUTH=true
AUTH_HEADER_NAME=Authorization
```

## Seguridad

1. **Claves enmascaradas**: Las métricas muestran solo los primeros y últimos 4 caracteres de cada clave
2. **Logging seguro**: Los logs muestran solo los primeros 8 caracteres de claves inválidas
3. **Variables de entorno**: Las claves se cargan solo desde variables de entorno
4. **Recarga en tiempo real**: Las claves se pueden recargar sin reiniciar el servidor
