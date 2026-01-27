# Konko AI Conversational Agent

Un agente conversacional configurable construido con LangChain, LangGraph y FastAPI para recolectar información de usuarios mediante diálogos naturales.

[![CI](https://github.com/TheLuisBolivar/konko-agent/actions/workflows/ci.yml/badge.svg)](https://github.com/TheLuisBolivar/konko-agent/actions/workflows/ci.yml)
[![Quality Gate Status](https://sonarcloud.io/api/project_badges/measure?project=TheLuisBolivar_konko-agent&metric=alert_status)](https://sonarcloud.io/summary/new_code?id=TheLuisBolivar_konko-agent)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=TheLuisBolivar_konko-agent&metric=coverage)](https://sonarcloud.io/summary/new_code?id=TheLuisBolivar_konko-agent)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=TheLuisBolivar_konko-agent&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=TheLuisBolivar_konko-agent)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=TheLuisBolivar_konko-agent&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=TheLuisBolivar_konko-agent)
[![Python](https://img.shields.io/badge/python-3.10+-blue)](pyproject.toml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 🚀 Características

- ✅ **LangGraph State Machine** para control de flujo conversacional
- ✅ **Configuración basada en YAML** con validación Pydantic
- ✅ **Gestión de estado** thread-safe con soporte para Redis
- ✅ **Múltiples políticas de escalación** (keyword, timeout, sentiment, LLM intent)
- ✅ **Detección de correcciones** ("No, mi email es...")
- ✅ **Detección de off-topic** y redirección automática
- ✅ **Dual interface**: REST API + WebSocket y CLI
- ✅ **Type-safe** con mypy strict mode (100% type coverage)
- ✅ **Alta cobertura de tests** (264 tests passing)
- ✅ **Calidad de código garantizada** con pre-commit hooks
- ✅ **Análisis de seguridad** automático con Bandit
- ✅ **Complejidad controlada** (<10 por función)

## 🔄 Arquitectura del Flujo Conversacional

El agente utiliza una **state machine basada en LangGraph** para controlar el flujo de la conversación:

```
START → check_escalation
           │
    ┌──────┴──────┐
    ↓             ↓
escalate    check_correction
    ↓             │
   END     ┌──────┴──────┐
           ↓             ↓
    extract_field   check_off_topic
           │             │
           ↓      ┌──────┴──────┐
        validate  ↓             ↓
           │   prompt_next   complete
    ┌──────┴──────┐   │         ↓
    ↓             ↓   ↓        END
prompt_next   complete
    ↓             ↓
   END           END
```

### Nodos del Grafo

| Nodo | Descripción |
|------|-------------|
| `check_escalation` | Evalúa políticas de escalación (keyword, timeout, sentiment, etc.) |
| `check_correction` | Detecta correcciones del usuario ("No, mi email es...") |
| `check_off_topic` | Identifica respuestas fuera de tema |
| `extract_field` | Extrae valores de campos del mensaje del usuario |
| `validate` | Valida el valor extraído según el tipo de campo |
| `prompt_next` | Genera prompt para el siguiente campo o re-pregunta |
| `escalate` | Maneja la escalación a agente humano |
| `complete` | Genera mensaje de completitud cuando todos los campos están recolectados |

Para más detalles, ver [docs/CONVERSATION_FLOW.md](docs/CONVERSATION_FLOW.md)

## 📦 Instalación

### Requisitos

- Python 3.10+
- pip
- git

### Setup Rápido

```bash
# Clonar el repositorio
git clone https://github.com/TheLuisBolivar/konko-agent.git
cd konko-agent

# Setup completo (venv, deps, git hooks)
make setup

# Activar ambiente virtual
source .venv/bin/activate

# Verificar instalación
make verify
```

El comando `make setup` instala automáticamente:
- Ambiente virtual Python
- Todas las dependencias (producción + desarrollo)
- Pre-commit git hooks (formateo, linting, tests, seguridad)

### Docker

```bash
# Opción 1: Usar imagen de DockerHub
docker pull theluisbolivar/konko-agent:latest
docker run -p 8000:8000 -e OPENAI_API_KEY=$OPENAI_API_KEY theluisbolivar/konko-agent:latest

# Opción 2: Build local
docker build -t konko-agent .
docker run -p 8000:8000 -e OPENAI_API_KEY=$OPENAI_API_KEY konko-agent

# Opción 3: Docker Compose
docker-compose up konko-agent

# Desarrollo con hot reload
docker-compose --profile dev up konko-agent-dev
```

## 🏃 Inicio Rápido

### 1. Probar configuración básica

```bash
# Cargar y validar configuración
python -c "
from agent_config import load_config_from_yaml
config = load_config_from_yaml('configs/basic_agent.yaml')
print(f'✓ Config cargada: {len(config.fields)} campos')
print(f'  Personalidad: {config.personality.tone}')
print(f'  Saludo: {config.greeting}')
"
```

**Salida esperada:**
```
✓ Config cargada: 3 campos
  Personalidad: Tone.PROFESSIONAL
  Saludo: Hello! I'm here to help collect some information from you today.
```

### 2. Probar gestión de estado

```bash
# Crear y gestionar conversación
python -c "
from agent_runtime import ConversationState, get_default_store, MessageRole

store = get_default_store()
state = ConversationState()
store.create(state)

state.add_message(MessageRole.AGENT, '¿Cómo te llamas?')
state.add_message(MessageRole.USER, 'Luis')
state.update_field_value('name', 'Luis', True)

print(f'✓ Sesión creada: {state.session_id}')
print(f'  Mensajes: {len(state.messages)}')
print(f'  Datos recolectados: {state.get_collected_data()}')

store.clear()
"
```

**Salida esperada:**
```
✓ Sesión creada: a1b2c3d4-e5f6-7890-abcd-ef1234567890
  Mensajes: 2
  Datos recolectados: {'name': 'Luis'}
```

### 3. Ejecutar tests

```bash
# Tests unitarios
make test

# Tests con reporte de coverage
make test-cov

# Ver reporte HTML de coverage
open htmlcov/index.html
```

## 🛠️ Desarrollo

### Comandos Disponibles

```bash
make help              # Ver todos los comandos disponibles
make verify            # Verificar setup y dependencias
make test              # Ejecutar tests unitarios
make test-cov          # Tests con coverage report (HTML + terminal)
make format            # Formatear código (black + isort)
make lint              # Lint código (ruff + mypy)
make quality           # ⭐ Ejecutar TODOS los checks de calidad
make quality-check     # Verificar calidad sin auto-fix (para CI)
make security          # Ejecutar análisis de seguridad
make hooks-run         # Ejecutar pre-commit hooks manualmente
make hooks-install     # Reinstalar git hooks
make clean             # Limpiar archivos generados
make status            # Ver status de git y commits recientes
```

### Pre-commit Hooks Automáticos

Los hooks se ejecutan **automáticamente** al hacer commit/push:

**Al hacer `git commit`:**
- ✅ Formateo automático (Black, isort)
- ✅ Linting (Ruff, Flake8 con complejidad)
- ✅ Type checking (mypy strict)
- ✅ Security scan (Bandit)
- ✅ Docstring validation (pydocstyle)
- ✅ Tests unitarios rápidos

**Al hacer `git push`:**
- ✅ Todo lo anterior
- ✅ Tests completos con coverage (mínimo 80%)

Ver más detalles en [docs/PRE_COMMIT_HOOKS.md](docs/PRE_COMMIT_HOOKS.md)

### Workflow de Desarrollo

```bash
# 1. Hacer cambios
vim packages/agent_config/schemas.py

# 2. Commit (hooks se ejecutan automáticamente)
git add .
git commit -m "feat: add new feature"
# ⬆️ Los hooks verifican calidad automáticamente

# 3. Si algo falla, corregir y re-commit
# Algunos hooks auto-corrigen (black, isort, ruff)
git add .
git commit -m "feat: add new feature"

# 4. Push (ejecuta tests completos)
git push origin feature/my-feature
```

## 📁 Estructura del Proyecto

```
konko-agent/
├── packages/                    # Código fuente del proyecto
│   ├── agent_config/           # ✅ Configuración y validación
│   │   ├── __init__.py
│   │   ├── schemas.py          # Modelos Pydantic
│   │   └── loader.py           # Cargador YAML
│   ├── agent_runtime/          # ✅ Gestión de estado
│   │   ├── __init__.py
│   │   ├── state.py            # Modelos de estado
│   │   └── store.py            # Store thread-safe
│   └── agent_core/             # ✅ Lógica del agente
│       ├── __init__.py
│       ├── agent.py            # Agente principal
│       ├── llm_provider.py     # Proveedor de LLM
│       ├── escalation/         # Motor de escalación
│       │   ├── engine.py
│       │   ├── handlers/       # Handlers de políticas
│       │   └── ...
│       └── graph/              # ✅ LangGraph State Machine
│           ├── __init__.py
│           ├── state.py        # GraphState TypedDict
│           ├── nodes.py        # 8 funciones de nodo
│           ├── edges.py        # Funciones de routing
│           └── builder.py      # Constructor del grafo
│
├── configs/                     # Configuraciones de ejemplo
│   ├── basic_agent.yaml        # Configuración básica (3 campos)
│   └── advanced_agent.yaml     # Configuración avanzada (7 campos)
│
├── tests/                       # Suite de tests (264 tests)
│   └── unit/
│       ├── test_agent.py
│       ├── test_config_*.py
│       ├── test_state.py
│       ├── test_store.py
│       ├── test_escalation_*.py
│       ├── test_graph_nodes.py      # Tests de nodos
│       ├── test_graph_edges.py      # Tests de routing
│       └── test_graph_integration.py # Tests de flujos
│
├── docs/                        # Documentación
│   ├── CONVERSATION_FLOW.md    # Arquitectura del flujo conversacional
│   ├── PRE_COMMIT_HOOKS.md     # Guía de git hooks
│   └── CODE_QUALITY_TOOLS.md   # Herramientas de calidad
│
├── scripts/                     # Scripts de utilidad
│   ├── verify_setup.py         # Verificación de setup
│   └── test_progress.sh        # Check de progreso
│
├── .pre-commit-config.yaml     # Configuración de hooks
├── pyproject.toml              # Configuración del proyecto
├── Makefile                    # Comandos de desarrollo
└── README.md                   # Este archivo
```

## 📊 Métricas de Calidad

| Métrica | Valor | Status |
|---------|-------|--------|
| **Tests** | 264/264 pasando | ✅ 100% |
| **Coverage** | >95% | ✅ Excelente |
| **Type Coverage** | 100% (mypy strict) | ✅ Perfecto |
| **Complejidad** | <10 por función | ✅ Bajo |
| **Seguridad** | 0 vulnerabilidades | ✅ Seguro |
| **Linting** | 0 errores | ✅ Limpio |

### Coverage Detallado

```
Name                                 Stmts   Miss   Cover
-----------------------------------------------------------
packages/agent_config/__init__.py        4      0 100.00%
packages/agent_config/loader.py         33      2  93.94%
packages/agent_config/schemas.py        89      0 100.00%
packages/agent_runtime/__init__.py       4      0 100.00%
packages/agent_runtime/state.py         80      0 100.00%
packages/agent_runtime/store.py         72      0 100.00%
-----------------------------------------------------------
TOTAL                                  283      3  98.94%
```

## 🔧 Configuración

### Ejemplo Básico

`configs/basic_agent.yaml`:

```yaml
personality:
  tone: professional          # friendly, professional, casual, empathetic
  style: concise
  formality: neutral          # formal, neutral, informal
  emoji_usage: false

greeting: "Hello! I'm here to help collect some information."

fields:
  - name: full_name
    field_type: text
    required: true
    prompt_hint: "What's your full name?"

  - name: email
    field_type: email
    required: true
    validation_pattern: "^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,}$"
    prompt_hint: "What's your email address?"

  - name: phone_number
    field_type: phone
    required: false
    prompt_hint: "What's your phone number? (Optional)"

escalation_policies:
  - enabled: true
    reason: "User requested human assistance"
    policy_type: keyword
    config:
      keywords: ["human", "agent", "help", "representative"]

  - enabled: true
    reason: "Conversation took too long"
    policy_type: timeout
    config:
      max_duration_seconds: 600  # 10 minutes
```

### Ejemplo Avanzado

Ver `configs/advanced_agent.yaml` para un ejemplo con:
- 7 campos de diferentes tipos (text, email, phone, url, number, date)
- 5 políticas de escalación (keyword, timeout, sentiment, llm_intent, completion)
- Personalidad friendly con emojis habilitados

## 🌐 Probar la API

### Iniciar el Servidor

```bash
# Activar ambiente y configurar API key
source .venv/bin/activate
export OPENAI_API_KEY="sk-tu-api-key"

# Iniciar servidor (puerto 8000)
python main.py
```

### Endpoints Disponibles

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| `POST` | `/conversations` | Iniciar nueva conversación |
| `POST` | `/conversations/{id}/messages` | Enviar mensaje |
| `GET` | `/conversations/{id}` | Ver estado de conversación |
| `DELETE` | `/conversations/{id}` | Eliminar conversación |
| `WS` | `/ws` | WebSocket para tiempo real |
| `GET` | `/health` | Health check |
| `GET` | `/docs` | Swagger UI (documentación interactiva) |

### Probar con curl

```bash
# 1. Iniciar conversación
curl -X POST http://localhost:8000/conversations | jq

# 2. Enviar mensaje (reemplaza SESSION_ID)
curl -X POST "http://localhost:8000/conversations/SESSION_ID/messages" \
  -H "Content-Type: application/json" \
  -d '{"content": "Mi nombre es Luis"}' | jq

# 3. Probar corrección
curl -X POST "http://localhost:8000/conversations/SESSION_ID/messages" \
  -H "Content-Type: application/json" \
  -d '{"content": "No, mi nombre es Luis Bolivar"}' | jq

# 4. Probar off-topic (el agente redirige)
curl -X POST "http://localhost:8000/conversations/SESSION_ID/messages" \
  -H "Content-Type: application/json" \
  -d '{"content": "¿Qué hora es?"}' | jq

# 5. Ver estado de la conversación
curl -X GET "http://localhost:8000/conversations/SESSION_ID" | jq
```

### Probar con WebSocket

```bash
# Requiere wscat: npm install -g wscat
wscat -c ws://localhost:8000/ws

# Una vez conectado, enviar mensajes:
> {"type": "message", "content": "Mi nombre es Luis"}
> {"type": "message", "content": "luis@ejemplo.com"}
```

### Swagger UI

Abre `http://localhost:8000/docs` en tu navegador para probar la API de forma interactiva.

## 🧪 Testing

### Ejecutar Tests

```bash
# Todos los tests con output verbose
pytest tests/unit/ -v

# Con coverage detallado
pytest tests/unit/ --cov=packages --cov-report=term-missing

# Solo tests específicos
pytest tests/unit/test_config_schemas.py -v

# Ejecutar un test específico
pytest tests/unit/test_state.py::TestConversationState::test_add_message -v

# Con warnings desactivados
pytest tests/unit/ -v --disable-warnings
```

### Escribir Tests

Los tests usan `pytest` y siguen esta estructura:

```python
"""Tests for my module."""

import pytest
from agent_config import AgentConfig, FieldConfig

class TestMyFeature:
    """Tests for MyFeature."""

    def test_basic_functionality(self):
        """Test basic functionality works."""
        config = AgentConfig(fields=[FieldConfig(name="test")])
        assert len(config.fields) == 1

    def test_error_case(self):
        """Test error handling."""
        with pytest.raises(ValueError) as exc_info:
            FieldConfig(name="")
        assert "cannot be empty" in str(exc_info.value)
```

## 🔒 Seguridad

### Análisis Automático

- **Bandit**: Escanea código en busca de vulnerabilidades
- **Pre-commit**: Detecta claves privadas antes de commit
- **Dependabot** (próximamente): Actualización automática de dependencias
- **Safety** (recomendado): Escaneo de CVEs en dependencias

### Ejecutar Scan Manual

```bash
# Análisis de seguridad completo
make security

# Solo Bandit
source .venv/bin/activate
bandit -r packages/ -c pyproject.toml

# Verificar dependencias (requiere instalar safety)
pip install safety
safety check
```

### Mejores Prácticas

- ✅ **No commitear** archivos `.env` (en `.gitignore`)
- ✅ **No hardcodear** credenciales en código
- ✅ **Usar variables de entorno** para secretos
- ✅ **Revisar dependencias** regularmente
- ✅ **Mantener Python actualizado** (3.10+)

## 📚 Documentación

- **[Conversation Flow](docs/CONVERSATION_FLOW.md)** - Arquitectura del flujo conversacional (LangGraph)
- **[Pre-commit Hooks](docs/PRE_COMMIT_HOOKS.md)** - Guía completa de git hooks
- **[Code Quality Tools](docs/CODE_QUALITY_TOOLS.md)** - Herramientas de calidad y recomendaciones
- **[Implementation Plan](.epsilon/)** - Plan de implementación detallado

## 🤝 Contribuir

### Requisitos para Pull Requests

Para que un PR sea aceptado debe cumplir:

- ✅ **Todos los tests pasando** (264/264)
- ✅ **Coverage >80%** (actualmente >95%)
- ✅ **Código formateado** (black + isort)
- ✅ **Sin errores de linting** (ruff + flake8)
- ✅ **Type hints completos** (mypy strict)
- ✅ **Docstrings en código público** (Google style)
- ✅ **Sin vulnerabilidades** de seguridad
- ✅ **Aprobación de @TheLuisBolivar** (CODEOWNERS)

### Proceso de Contribución

1. **Fork** el proyecto
2. **Crea** tu feature branch (`git checkout -b feature/amazing-feature`)
3. **Desarrolla** con los hooks activados (se instalan automáticamente)
4. **Commit** tus cambios (los hooks verifican calidad)
   ```bash
   git commit -m 'feat: add amazing feature'
   ```
5. **Push** a la branch (ejecuta tests completos)
   ```bash
   git push origin feature/amazing-feature
   ```
6. **Abre** un Pull Request con descripción detallada

### Convención de Commits

Seguimos [Conventional Commits](https://www.conventionalcommits.org/):

```bash
feat: add new feature
fix: resolve bug in state management
docs: update README with examples
style: format code with black
refactor: restructure configuration loader
test: add tests for escalation policies
chore: update dependencies
```

## 🐛 Troubleshooting

### "Pre-commit hooks muy lentos"

La primera ejecución es lenta (descarga herramientas). Las siguientes son rápidas.

```bash
# Para commits urgentes (NO RECOMENDADO)
git commit --no-verify -m "mensaje"
```

### "Tests fallan localmente pero pasaban antes"

```bash
# Reinstalar dependencias
source .venv/bin/activate
pip install -e ".[dev]"

# Limpiar caché
make clean

# Re-ejecutar tests
make test
```

### "Coverage bajo después de agregar código"

```bash
# Ver qué líneas faltan
pytest --cov=packages --cov-report=term-missing

# Agregar tests para las líneas faltantes
```

### "Mypy reporta errores de tipos"

```bash
# Instalar tipos faltantes
pip install types-PyYAML types-redis

# Verificar tipos
mypy packages/
```

## 📊 Static Code Analysis (SonarCloud)

Este proyecto usa **SonarCloud** para análisis estático de código gratuito.

### Ver Resultados

Los resultados del análisis están disponibles públicamente en:

👉 **[SonarCloud Dashboard](https://sonarcloud.io/summary/new_code?id=TheLuisBolivar_konko-agent)**

### Métricas Analizadas

| Métrica | Descripción |
|---------|-------------|
| **Quality Gate** | Estado general de calidad del código |
| **Coverage** | Cobertura de tests (>95%) |
| **Maintainability** | Complejidad y deuda técnica |
| **Reliability** | Bugs y problemas de fiabilidad |
| **Security** | Vulnerabilidades y hotspots |
| **Duplications** | Código duplicado |

### Configurar SonarCloud (Para Forks)

1. Importa el proyecto en [sonarcloud.io](https://sonarcloud.io)
2. Agrega el secret `SONAR_TOKEN` en GitHub Actions
3. El análisis se ejecutará automáticamente en cada PR

## 📞 Soporte

- **Issues**: [GitHub Issues](https://github.com/TheLuisBolivar/konko-agent/issues)
- **Discusiones**: [GitHub Discussions](https://github.com/TheLuisBolivar/konko-agent/discussions)
- **Email**: luis@konko.ai
- **Seguridad**: security@konko.ai

## 📄 Licencia

Este proyecto es privado y confidencial.

## 👥 Equipo

- [@TheLuisBolivar](https://github.com/TheLuisBolivar) - Lead Developer & Code Owner

## 🙏 Agradecimientos

- [LangChain](https://github.com/langchain-ai/langchain) - Framework de LLM
- [LangGraph](https://github.com/langchain-ai/langgraph) - State machines para LLMs
- [FastAPI](https://github.com/tiangolo/fastapi) - Framework web moderno
- [Pydantic](https://github.com/pydantic/pydantic) - Validación de datos
- [pre-commit](https://pre-commit.com/) - Framework de git hooks

---

🤖 Built with [Claude Code](https://claude.com/claude-code)
