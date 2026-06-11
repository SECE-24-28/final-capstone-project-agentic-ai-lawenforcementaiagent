"""Escalation service integration exports."""

from .api import (
    router as escalation_router,
    start_escalation_service,
    stop_escalation_service,
)

__all__ = [
    "escalation_router",
    "start_escalation_service",
    "stop_escalation_service",
]
