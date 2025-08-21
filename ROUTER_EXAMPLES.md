# 🔀 Router Configuration Examples

El LLM Router ahora soporta failover automático con múltiples servicios. Aquí están los ejemplos de configuración.

## 🎯 Configuración Básica con Router

### Ejemplo 1: Cerebras + OpenAI Fallback (Con Rate Limiting)

```env
# Activar el router
USE_ROUTER=true

# Configuración JSON de servicios con rate limiting
ROUTER_SERVICES='[
  {
    "name": "primary-cerebras",
    "backend_type": "cerebras",
    "base_url": "https://api.cerebras.ai/v1",
    "api_key": "your_cerebras_key",
    "timeout": 60,
    "priority": 0,
    "rate_limit_requests": 100,
    "rate_limit_window": 60
  },
  {
    "name": "fallback-openai", 
    "backend_type": "openai",
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-your_openai_key",
    "timeout": 30,
    "priority": 1,
    "rate_limit_requests": 50,
    "rate_limit_window": 60
  }
]'
```

### Ejemplo 2: Local + Cerebras + OpenAI (Con Rate Limiting Inteligente)

```env
USE_ROUTER=true

ROUTER_SERVICES='[
  {
    "name": "ollama",
    "backend_type": "ollama",
    "base_url": "http://localhost:8080/v1",
    "timeout": 120,
    "priority": 0,
    "rate_limit_requests": 200,
    "rate_limit_window": 60
  },
  {
    "name": "cerebras-backup",
    "backend_type": "cerebras",
    "base_url": "https://api.cerebras.ai/v1",
    "api_key": "your_cerebras_key",
    "timeout": 60,
    "priority": 1,
    "rate_limit_requests": 100,
    "rate_limit_window": 60
  },
  {
    "name": "openai-emergency",
    "backend_type": "openai", 
    "base_url": "https://api.openai.com/v1",
    "api_key": "sk-your_openai_key",
    "timeout": 30,
    "priority": 2,
    "rate_limit_requests": 30,
    "rate_limit_window": 60
  }
]'
```

### Ejemplo 3: Auto-failover (Configuración Simplificada)

```env
# El router se activará automáticamente si hay múltiples APIs configuradas
CEREBRAS_API_KEY=your_cerebras_key
OPENAI_API_KEY=sk-your_openai_key

# Backend principal
BACKEND_TYPE=cerebras
```

## 🔧 Configuración Avanzada

### Ejemplo para Pruebas de Rate Limiting (Testing)

```env
USE_ROUTER=true

# Configuración con límites muy bajos para testing
ROUTER_SERVICES='[
  {
    "name": "test-cerebras",
    "backend_type": "cerebras",
    "base_url": "https://api.cerebras.ai/v1",
    "api_key": "your_key",
    "timeout": 60,
    "priority": 0,
    "rate_limit_requests": 3,
    "rate_limit_window": 30
  },
  {
    "name": "test-backup",
    "backend_type": "cerebras",
    "base_url": "https://api.cerebras.ai/v1",
    "api_key": "your_key",
    "timeout": 30,
    "priority": 1,
    "rate_limit_requests": 2,
    "rate_limit_window": 20
  }
]'
```

### Timeouts Personalizados con Rate Limiting

```env
USE_ROUTER=true

ROUTER_SERVICES='[
  {
    "name": "fast-service",
    "backend_type": "cerebras",
    "base_url": "https://api.cerebras.ai/v1",
    "api_key": "key1",
    "timeout": 15,
    "priority": 0,
    "rate_limit_requests": 500,
    "rate_limit_window": 60
  },
  {
    "name": "slow-reliable",
    "backend_type": "openai",
    "base_url": "https://api.openai.com/v1", 
    "api_key": "key2",
    "timeout": 90,
    "priority": 1,
    "rate_limit_requests": 100,
    "rate_limit_window": 60
  }
]'
```

### Múltiples Instancias del Mismo Servicio

```env
USE_ROUTER=true

ROUTER_SERVICES='[
  {
    "name": "cerebras-primary",
    "backend_type": "cerebras",
    "base_url": "https://api.cerebras.ai/v1",
    "api_key": "key1",
    "priority": 0
  },
  {
    "name": "cerebras-secondary",
    "backend_type": "cerebras", 
    "base_url": "https://api.cerebras.ai/v1",
    "api_key": "key2",
    "priority": 1
  }
]'
```

## 🧪 Comandos de Prueba

### 1. Verificar Configuración

```bash
# Ver información general
curl "http://localhost:8000/"

# Ver información detallada del backend
curl "http://localhost:8000/backend/info"
```

### 2. Estadísticas del Router (Solo en modo router)

```bash
# Ver estadísticas de uso completas (incluyendo rate limiting)
curl "http://localhost:8000/router/stats"

# Ver salud de los servicios
curl "http://localhost:8000/router/health"

# Ver estado actual de rate limiting
curl "http://localhost:8000/router/rate-limits"

# Reiniciar estadísticas
curl -X POST "http://localhost:8000/router/reset-stats"
```

### 3. Probar Failover

```bash
# Hacer múltiples requests y ver las estadísticas
for i in {1..5}; do
  curl -X POST "http://localhost:8000/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{
      "model": "llama3.1-8b",
      "messages": [{"role": "user", "content": "Test '$i'"}],
      "max_tokens": 10
    }' && echo ""
done

# Ver estadísticas después
curl "http://localhost:8000/router/stats"
```

### 4. Probar Rate Limiting

```bash
# Test con límites muy bajos (usar configuración de testing)
# Hacer requests rápidos para activar rate limiting

echo "Testing rate limiting..."
for i in {1..8}; do
  echo "Request $i:"
  curl -s -X POST "http://localhost:8000/v1/chat/completions" \
    -H "Content-Type: application/json" \
    -d '{
      "model": "llama3.1-8b",
      "messages": [{"role": "user", "content": "Test '$i'"}],
      "max_tokens": 5
    }' | jq '.error.message // "Success"'
  sleep 1
done

echo -e "\n=== Rate Limiting Status ==="
curl -s "http://localhost:8000/router/rate-limits" | jq

echo -e "\n=== Router Stats ==="
curl -s "http://localhost:8000/router/stats" | jq '.rate_limiting'
```

## 📊 Respuestas del Router

### Respuesta en Modo Single Service

```json
{
  "message": "LLM Router - OpenAI API compatible endpoint",
  "version": "1.0.0",
  "docs": "/docs",
  "mode": "single_service",
  "backend": "cerebras",
  "primary_backend": "cerebras"
}
```

### Respuesta en Modo Router

```json
{
  "message": "LLM Router - OpenAI API compatible endpoint",
  "version": "1.0.0", 
  "docs": "/docs",
  "mode": "router",
  "services_count": 2,
  "services": [
    {"name": "primary-cerebras", "type": "cerebras", "priority": 0},
    {"name": "fallback-openai", "type": "openai", "priority": 1}
  ],
  "primary_backend": "cerebras"
}
```

### Estadísticas del Router (Con Rate Limiting)

```json
{
  "total_requests": 25,
  "total_failovers": 3, 
  "total_rate_limit_skips": 8,
  "failover_rate": 12.0,
  "rate_limit_skip_rate": 32.0,
  "configured_services": 2,
  "service_stats": {
    "primary-cerebras": {
      "requests": 15, 
      "failures": 3, 
      "rate_limited": 8
    },
    "fallback-openai": {
      "requests": 10, 
      "failures": 0, 
      "rate_limited": 2
    }
  },
  "service_order": ["primary-cerebras", "fallback-openai"],
  "rate_limiting": {
    "primary-cerebras": {
      "rate_limit": "100/60s",
      "current_requests": 15,
      "remaining_quota": 85,
      "is_rate_limited": false,
      "window_reset_in": 42.1
    },
    "fallback-openai": {
      "rate_limit": "50/60s", 
      "current_requests": 50,
      "remaining_quota": 0,
      "is_rate_limited": true,
      "window_reset_in": 18.7
    }
  }
}
```

### Health Check del Router (Con Rate Limiting)

```json
{
  "overall_status": "healthy",
  "services": {
    "primary-cerebras": {
      "status": "degraded",
      "backend_type": "cerebras",
      "base_url": "https://api.cerebras.ai/v1",
      "has_api_key": true,
      "requests": 15,
      "failures": 3,
      "failure_rate": 20.0,
      "rate_limited_events": 8,
      "is_currently_rate_limited": false,
      "rate_limit_config": {
        "max_requests": 100,
        "window_seconds": 60
      }
    },
    "fallback-openai": {
      "status": "healthy",
      "backend_type": "openai", 
      "base_url": "https://api.openai.com/v1",
      "has_api_key": true,
      "requests": 10,
      "failures": 0,
      "failure_rate": 0.0,
      "rate_limited_events": 2,
      "is_currently_rate_limited": true,
      "rate_limit_config": {
        "max_requests": 50,
        "window_seconds": 60
      }
    }
  }
}
```

### Response del Endpoint `/router/rate-limits`

```json
{
  "rate_limiting": {
    "primary-cerebras": {
      "rate_limit": "100/60s",
      "current_requests": 95,
      "remaining_quota": 5,
      "is_rate_limited": false,
      "window_reset_in": 12.3
    },
    "fallback-openai": {
      "rate_limit": "50/60s",
      "current_requests": 50,
      "remaining_quota": 0,
      "is_rate_limited": true,
      "window_reset_in": 45.2
    }
  },
  "total_rate_limit_skips": 15,
  "rate_limit_skip_rate": 23.1,
  "current_time": 1703123456.789
}
```

## 🚨 Comportamiento de Failover y Rate Limiting

### 🔄 Lógica de Failover con Rate Limiting

1. **Prioridad + Rate Limiting**: Los servicios se evalúan en orden de prioridad (0 = mayor prioridad)
2. **Check de Rate Limit**: Antes de usar un servicio, se verifica si está rate limited
3. **Skip Automático**: Si un servicio está rate limited, se salta automáticamente al siguiente
4. **Failover Tradicional**: Si un servicio falla (error), se pasa al siguiente disponible
5. **Logging Inteligente**: Se registran tanto failovers por error como skips por rate limiting

### 📊 Sliding Window Rate Limiting

- **Ventana Deslizante**: Cuenta requests en los últimos X segundos desde el momento actual
- **Limpieza Automática**: Requests antiguos se eliminan automáticamente de la ventana
- **Precisión por Segundo**: Resolución de timestamps con precisión de milisegundos
- **Reset Progresivo**: No hay reset abrupto, la cuota se libera gradualmente

### 🎯 Escenarios de Uso

1. **Rate Limit Alcanzado**: Se salta al siguiente servicio sin intentar request
2. **Servicio Falla**: Se intenta con el siguiente servicio disponible (no rate limited)
3. **Todos Rate Limited**: Error 429 "All configured services are rate limited"
4. **Todos Fallan**: Error 503 "All configured services are unavailable"

### 📈 Métricas Adicionales

- **Rate Limit Skips**: Cuenta de servicios saltados por rate limiting
- **Rate Limited Events**: Eventos de rate limiting por servicio
- **Current Quota**: Requests restantes en la ventana actual
- **Window Reset Time**: Tiempo hasta que se libere el próximo slot

## 💡 Tips y Mejores Prácticas

### 🔧 Configuración General
1. **Timeouts Escalonados**: Usa timeouts más cortos para servicios rápidos, más largos para servicios de respaldo
2. **Prioridades Claras**: Usa intervalos de 10 en las prioridades (0, 10, 20) para facilitar inserción futura
3. **API Keys Separadas**: Usa diferentes API keys para cada servicio cuando sea posible
4. **Fallback Local**: Considera incluir un servidor local como último recurso

### ⚡ Rate Limiting
5. **Límites Realistas**: Configura rate limits ligeramente por debajo del límite real de la API
6. **Ventanas Apropiadas**: 60 segundos es un buen balance entre flexibilidad y control
7. **Servicios Escalonados**: Configura límites decrecientes por prioridad (ej: 200, 100, 50)
8. **Testing**: Usa límites muy bajos (2-5 requests) para probar la lógica de failover
9. **Monitoreo Rate Limits**: Usa `/router/rate-limits` para monitorear cuotas en tiempo real

### 📊 Monitoreo
10. **Salud Regular**: Revisa `/router/health` y `/router/stats` periódicamente
11. **Rate Limiting Stats**: Monitorea `rate_limit_skip_rate` para optimizar límites
12. **Window Reset Tracking**: Usa `window_reset_in` para predecir disponibilidad de servicios
13. **Alertas Inteligentes**: Configura alertas cuando `rate_limit_skip_rate > 50%`

### 🎯 Configuraciones Recomendadas

#### Para APIs de Producción
```json
"rate_limit_requests": 1000,
"rate_limit_window": 60
```

#### Para APIs con Límites Estrictos
```json
"rate_limit_requests": 100,
"rate_limit_window": 60  
```

#### Para Testing/Development
```json
"rate_limit_requests": 5,
"rate_limit_window": 30
```
