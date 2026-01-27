# Arquitectura del Flujo Conversacional

Este documento describe la arquitectura de la state machine basada en LangGraph que controla el flujo de las conversaciones del agente.

## Visión General

El agente utiliza una **state machine compilada con LangGraph** que procesa cada mensaje del usuario a través de una serie de nodos conectados por edges condicionales. Esta arquitectura permite:

- **Modularidad**: Cada nodo tiene una responsabilidad específica
- **Extensibilidad**: Fácil agregar nuevos nodos o modificar el flujo
- **Testabilidad**: Cada nodo puede ser testeado de forma aislada
- **Claridad**: El flujo de la conversación es explícito y trazable

## Diagrama de la State Machine

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

## Nodos

### 1. `check_escalation`

**Propósito**: Evaluar si la conversación debe ser escalada a un agente humano.

**Entrada**: Estado del grafo con mensaje del usuario

**Salida**: `should_escalate: bool`, `escalation_reason: str | None`

**Lógica**:
- Utiliza el `EscalationEngine` existente
- Evalúa políticas en orden de prioridad:
  1. `keyword` - Detección de palabras clave
  2. `timeout` - Tiempo excedido
  3. `sentiment` - Análisis de sentimiento negativo
  4. `llm_intent` - Detección de intención por LLM
  5. `completion` - Estado de completitud

**Rutas de salida**:
- `escalate` → Si `should_escalate = True`
- `check_correction` → Si no hay escalación

---

### 2. `check_correction`

**Propósito**: Detectar si el usuario está corrigiendo un valor previamente proporcionado.

**Entrada**: Estado del grafo

**Salida**: `is_correction: bool`, `correction_field: str | None`

**Patrones detectados**:
```
- "No, mi email es..."
- "En realidad, debería ser..."
- "Déjame corregir..."
- "Eso está mal..."
```

**Lógica**:
1. Busca patrones de corrección en el mensaje
2. Si encuentra patrón, intenta identificar el campo
3. Para casos ambiguos, usa LLM para determinar si es corrección

**Rutas de salida**:
- `extract_field` → Si es una corrección
- `check_off_topic` → Si no es una corrección

---

### 3. `check_off_topic`

**Propósito**: Identificar respuestas irrelevantes o fuera de tema.

**Entrada**: Estado del grafo

**Salida**: `is_off_topic: bool`

**Patrones detectados**:
```
- Saludos simples: "Hola", "Hey", "Buenos días"
- Preguntas no relacionadas: "¿Cuál es el clima?"
- Cambios de tema: "Tengo otra pregunta..."
```

**Lógica**:
1. Verifica patrones comunes de off-topic
2. Para mensajes ambiguos, usa LLM para clasificar

**Rutas de salida**:
- `prompt_next` → Si es off-topic (redirige al usuario)
- `complete` → Si todos los campos están recolectados
- `extract_field` → Si el mensaje es relevante

---

### 4. `extract_field`

**Propósito**: Extraer el valor del campo actual del mensaje del usuario.

**Entrada**: Estado del grafo, campo actual o campo de corrección

**Salida**: `extracted_value: str | None`, `current_field: str`

**Lógica**:
1. Determina el campo objetivo (corrección o siguiente)
2. Construye prompt de extracción
3. Invoca LLM para extraer valor
4. Normaliza respuesta (NOT_PROVIDED, INVALID → None)

**Siguiente nodo**: `validate`

---

### 5. `validate`

**Propósito**: Validar el valor extraído según el tipo de campo.

**Entrada**: Estado del grafo con valor extraído

**Salida**: `is_valid: bool`

**Validaciones soportadas**:
| Tipo | Validación |
|------|------------|
| `email` | Patrón RFC 5322 simplificado |
| `phone` | Mínimo 7 dígitos, caracteres válidos |
| `url` | Protocolo http/https requerido |
| `number` | Parseable como float |
| `text` | Siempre válido si no está vacío |

**Lógica**:
1. Verifica que haya valor extraído
2. Aplica validador según tipo de campo
3. Aplica patrón personalizado si está configurado
4. Si es válido, actualiza el estado de conversación

**Rutas de salida**:
- `complete` → Si todos los campos están recolectados
- `prompt_next` → Si hay más campos o validación falló

---

### 6. `prompt_next`

**Propósito**: Generar el siguiente prompt para el usuario.

**Entrada**: Estado del grafo

**Salida**: `response: str`

**Comportamiento según contexto**:

| Contexto | Comportamiento |
|----------|---------------|
| Off-topic | Redirige amablemente + solicita campo |
| Valor inválido | Explica formato esperado + re-solicita |
| Normal | Solicita siguiente campo |

**Siguiente nodo**: `END`

---

### 7. `escalate`

**Propósito**: Manejar la escalación a agente humano.

**Entrada**: Estado del grafo con razón de escalación

**Salida**: `response: str` (mensaje de escalación)

**Lógica**:
1. Marca la conversación como escalada
2. Registra política y razón
3. Genera mensaje de transición

**Siguiente nodo**: `END`

---

### 8. `complete`

**Propósito**: Generar mensaje de completitud.

**Entrada**: Estado del grafo con todos los campos recolectados

**Salida**: `response: str` (mensaje de agradecimiento)

**Lógica**:
1. Genera mensaje de agradecimiento con LLM
2. Marca la conversación como completada

**Siguiente nodo**: `END`

---

## Estado del Grafo (GraphState)

```python
class GraphState(TypedDict):
    conversation: ConversationState    # Estado de la conversación
    user_message: str                  # Mensaje actual del usuario
    next_action: str                   # Siguiente acción
    should_escalate: bool              # Bandera de escalación
    escalation_reason: Optional[str]   # Razón de escalación
    is_correction: bool                # Es una corrección
    correction_field: Optional[str]    # Campo siendo corregido
    is_off_topic: bool                 # Mensaje fuera de tema
    extracted_value: Optional[str]     # Valor extraído
    is_valid: bool                     # Validación exitosa
    current_field: Optional[str]       # Campo actual
    response: str                      # Respuesta generada
    metadata: dict[str, Any]           # Metadata adicional
```

## Edges (Routing Functions)

### `route_after_escalation_check`
```python
if state["should_escalate"]:
    return "escalate"
return "check_correction"
```

### `route_after_correction_check`
```python
if state["is_correction"]:
    return "extract_field"
return "check_off_topic"
```

### `route_after_off_topic_check`
```python
if all_fields_collected:
    return "complete"
if state["is_off_topic"]:
    return "prompt_next"
return "extract_field"
```

### `route_after_validate`
```python
if all_fields_collected:
    return "complete"
return "prompt_next"
```

## Ejemplos de Flujo

### Happy Path (Flujo Normal)
```
Usuario: "Mi nombre es Juan"
→ check_escalation (no escalación)
→ check_correction (no corrección)
→ check_off_topic (on-topic)
→ extract_field (extrae "Juan")
→ validate (válido)
→ prompt_next (pide email)
→ END

Usuario: "juan@ejemplo.com"
→ check_escalation (no escalación)
→ check_correction (no corrección)
→ check_off_topic (on-topic)
→ extract_field (extrae "juan@ejemplo.com")
→ validate (válido)
→ complete (todos los campos)
→ END
```

### Flujo con Corrección
```
Usuario: "No, mi email es juan.nuevo@ejemplo.com"
→ check_escalation (no escalación)
→ check_correction (¡corrección detectada! campo: email)
→ extract_field (extrae "juan.nuevo@ejemplo.com")
→ validate (válido, actualiza email)
→ prompt_next (siguiente campo)
→ END
```

### Flujo con Off-Topic
```
Usuario: "¿Cómo está el clima?"
→ check_escalation (no escalación)
→ check_correction (no corrección)
→ check_off_topic (¡off-topic!)
→ prompt_next (redirige + pide campo)
→ END
```

### Flujo de Escalación
```
Usuario: "Necesito hablar con un humano"
→ check_escalation (¡escalación por keyword!)
→ escalate (marca y responde)
→ END
```

## Archivos del Módulo

```
packages/agent_core/graph/
├── __init__.py      # Exports
├── state.py         # GraphState TypedDict
├── nodes.py         # 8 funciones de nodo
├── edges.py         # Funciones de routing
└── builder.py       # Construcción del grafo
```

## Tests

Los tests del grafo se encuentran en:

```
tests/unit/
├── test_graph_nodes.py       # Tests de nodos individuales (16 tests)
├── test_graph_edges.py       # Tests de funciones de routing (13 tests)
└── test_graph_integration.py # Tests de flujos completos (15 tests)
```

## Extensibilidad

### Agregar un Nuevo Nodo

1. Define la función en `nodes.py`:
```python
async def my_new_node(state: GraphState, agent: ConversationalAgent) -> GraphState:
    # Tu lógica aquí
    return state
```

2. Agrégalo al builder en `builder.py`:
```python
workflow.add_node("my_new_node", partial(_wrap_node, my_new_node, agent=agent))
```

3. Conecta los edges necesarios.

### Modificar el Flujo

Edita las funciones de routing en `edges.py` para cambiar las condiciones de transición entre nodos.

---

Para más información sobre la configuración del agente, ver [README.md](../README.md).
