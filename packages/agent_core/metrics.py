"""Prometheus metrics definitions for Konko Agent.

This module provides centralized metric definitions for observability.
Metrics are exported via the /metrics endpoint for Prometheus scraping.
"""

from prometheus_client import Counter, Gauge, Histogram  # type: ignore[import-not-found]

# Request metrics
HTTP_REQUESTS = Counter(
    "konko_http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
)
HTTP_LATENCY = Histogram(
    "konko_http_request_duration_seconds",
    "HTTP request latency",
    ["method", "endpoint"],
)

# Processing metrics
MESSAGES_PROCESSED = Counter(
    "konko_messages_processed_total",
    "Messages processed",
    ["status"],
)
MESSAGE_LATENCY = Histogram(
    "konko_message_processing_seconds",
    "Message processing latency",
)
LLM_CALLS = Counter(
    "konko_llm_calls_total",
    "LLM API calls",
    ["operation"],
)
LLM_LATENCY = Histogram(
    "konko_llm_call_duration_seconds",
    "LLM call latency",
    ["operation"],
)

# Business metrics
ESCALATIONS = Counter(
    "konko_escalations_total",
    "Escalations triggered",
    ["policy_type", "reason"],
)
VALIDATIONS = Counter(
    "konko_validations_total",
    "Field validations",
    ["field_type", "result"],
)
ACTIVE_CONVERSATIONS = Gauge(
    "konko_conversations_active",
    "Active conversations",
)
CONVERSATIONS = Counter(
    "konko_conversations_total",
    "Conversations by outcome",
    ["status"],
)
