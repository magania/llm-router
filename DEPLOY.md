# Deploy Guide - LLM Router

Esta guía explica cómo hacer deploy del LLM Router usando Docker.

## 🐳 Docker Deployment

### Build y Run Básico

```bash
# Build de la imagen
docker build -t llm-router .

# Run básico
docker run -d \
  --name llm-router \
  -p 8000:8000 \
  -e AUTH_KEY="tu-clave-api" \
  -e CEREBRAS_API_KEY="tu-cerebras-key" \
  -e OPENAI_API_KEY="tu-openai-key" \
  llm-router
```

### Deployment Manual

#### 1. Configuración de Desarrollo
```bash
# Build y run con variables de entorno
docker build -t llm-router .

docker run -d \
  --name llm-router \
  -p 8000:8000 \
  -e AUTH_KEY="tu-clave-api" \
  -e CEREBRAS_API_KEY="tu-cerebras-key" \
  -e OPENAI_API_KEY="tu-openai-key" \
  llm-router

# Ver logs
docker logs -f llm-router

# Parar container
docker stop llm-router
docker rm llm-router
```

#### 2. Configuración de Producción
```bash
# Build para producción
docker build -t llm-router:prod .

# Run con todas las variables necesarias
docker run -d \
  --name llm-router-prod \
  -p 8000:8000 \
  --restart unless-stopped \
  -e AUTH_KEY_01="clave-usuario-1" \
  -e AUTH_KEY_02="clave-usuario-2" \
  -e CEREBRAS_API_KEY="tu-cerebras-key" \
  -e OPENAI_API_KEY="tu-openai-key" \
  -e DEEPINFRA_TOKEN="tu-deepinfra-token" \
  llm-router:prod

# Monitorear
docker ps
docker logs -f llm-router-prod
```

## ⚙️ Variables de Entorno

### Autenticación
```bash
# Opción 1: Clave única
AUTH_KEY=sk-tu-clave-secreta

# Opción 2: Múltiples claves
AUTH_KEY_01=sk-usuario1-clave
AUTH_KEY_02=sk-usuario2-clave
AUTH_KEY_03=sk-usuario3-clave

# Configuración de autenticación
ENABLE_AUTH=true
AUTH_HEADER_NAME=Authorization
```

### Backends LLM
```bash
# Cerebras
CEREBRAS_API_KEY=tu-cerebras-key
CEREBRAS_BASE_URL=https://api.cerebras.ai/v1

# OpenAI
OPENAI_API_KEY=tu-openai-key
OPENAI_BASE_URL=https://api.openai.com/v1

# DeepInfra
DEEPINFRA_TOKEN=tu-deepinfra-token
DEEPINFRA_BASE_URL=https://api.deepinfra.com/v1/openai

# Ollama (local)
OLLAMA_BASE_URL=http://ollama:11434
```

### Configuración del Servidor
```bash
HOST=0.0.0.0
PORT=8000
REQUEST_TIMEOUT=60
API_TITLE="LLM Router"
```

## 🚀 Deployment Options

### 1. Local Development
```bash
# Build y run local
docker build -t llm-router .
docker run -d \
  --name llm-router-dev \
  -p 8000:8000 \
  -e AUTH_KEY="dev-key-123" \
  -e CEREBRAS_API_KEY="tu-cerebras-key" \
  llm-router

# Acceder a:
# - API: http://localhost:8000
# - Docs: http://localhost:8000/docs
# - Health: http://localhost:8000/health
```

### 2. Production Server

#### Deploy Básico
```bash
# Build imagen de producción
docker build -t llm-router:prod .

# Run con configuración completa
docker run -d \
  --name llm-router-prod \
  -p 8000:8000 \
  --restart unless-stopped \
  -e AUTH_KEY_01="prod-key-1" \
  -e AUTH_KEY_02="prod-key-2" \
  -e CEREBRAS_API_KEY="prod-cerebras-key" \
  -e OPENAI_API_KEY="prod-openai-key" \
  llm-router:prod
```

#### Con Docker Swarm
```bash
# Inicializar swarm
docker swarm init

# Crear servicio
docker service create \
  --name llm-router \
  --replicas 3 \
  --publish 8000:8000 \
  -e AUTH_KEY_01="swarm-key-1" \
  -e CEREBRAS_API_KEY="swarm-cerebras-key" \
  llm-router:prod

# Escalar servicio
docker service scale llm-router=5
```

### 3. Kubernetes (K8s)

#### Deployment básico
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: llm-router
spec:
  replicas: 2
  selector:
    matchLabels:
      app: llm-router
  template:
    metadata:
      labels:
        app: llm-router
    spec:
      containers:
      - name: llm-router
        image: llm-router:latest
        ports:
        - containerPort: 8000
        env:
        - name: AUTH_KEY_01
          valueFrom:
            secretKeyRef:
              name: llm-router-secrets
              key: auth-key-01
        - name: CEREBRAS_API_KEY
          valueFrom:
            secretKeyRef:
              name: llm-router-secrets
              key: cerebras-key
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: llm-router-service
spec:
  selector:
    app: llm-router
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

## 🔒 Security Best Practices

### 1. Secrets Management
```bash
# Usar Docker secrets
docker secret create auth_key_01 path/to/auth_key_01.txt
docker secret create cerebras_key path/to/cerebras_key.txt

# En docker-compose:
secrets:
  - auth_key_01
  - cerebras_key
```

### 2. Network Security
```bash
# Crear red personalizada
docker network create llm-router-net

# Usar en compose
networks:
  default:
    external:
      name: llm-router-net
```

### 3. Container Security
```bash
# Run como non-root (ya incluido en Dockerfile)
# Limitar recursos
# Usar imagen base minimal
# Escanear vulnerabilidades
docker scan llm-router:latest
```

## 📊 Monitoring y Logging

### Health Checks
```bash
# Manual health check
curl http://localhost:8000/health

# Métricas de autenticación
curl http://localhost:8000/auth/metrics

# Stats del router
curl http://localhost:8000/router/stats
```

### Logging
```bash
# Ver logs del container
docker logs -f llm-router

# Con Docker Compose
docker-compose logs -f llm-router

# Logs en producción (configurar external logging)
# - ELK Stack
# - Fluentd
# - CloudWatch
# - DataDog
```

### Monitoring Endpoints
- `GET /health` - Health check
- `GET /auth/metrics` - Auth metrics
- `GET /router/stats` - Router statistics
- `GET /router/health` - Detailed health

## 🔧 Troubleshooting

### Common Issues

#### 1. Container no inicia
```bash
# Verificar logs
docker logs llm-router

# Verificar variables de entorno
docker exec llm-router env | grep AUTH
```

#### 2. Health check falla
```bash
# Verificar conectividad
docker exec llm-router curl -f http://localhost:8000/health

# Verificar puertos
docker port llm-router
```

#### 3. Backend connectivity issues
```bash
# Verificar configuración
curl http://localhost:8000/backend/info

# Test específico
curl -H "Authorization: Bearer tu-key" \
     -H "Content-Type: application/json" \
     -d '{"model": "llama3-8b", "messages": [{"role": "user", "content": "test"}]}' \
     http://localhost:8000/v1/chat/completions
```

### Performance Tuning

#### 1. Multi-worker deployment
```bash
# En Dockerfile, cambiar CMD a:
CMD ["python", "-m", "gunicorn", "app.app:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]
```

#### 2. Resource limits
```yaml
# En docker-compose
deploy:
  resources:
    limits:
      cpus: '2'
      memory: 1G
    reservations:
      cpus: '0.5'
      memory: 512M
```

## 🌐 Load Balancer Configuration

### Nginx Example
```nginx
upstream llm_router {
    server llm-router:8000;
    # Agregar más instancias para load balancing
    # server llm-router-2:8000;
}

server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://llm_router;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Para streaming responses
        proxy_buffering off;
        proxy_cache off;
    }
    
    location /health {
        proxy_pass http://llm_router/health;
        access_log off;
    }
}
```

¡El LLM Router está listo para deploy en cualquier entorno Docker!
