# e:\VakilAI\drafter_agent\reasoner_agent\models.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

# ----------------------------------------------------------------------
# Incoming event from Watcher
# ----------------------------------------------------------------------
class WatcherEvent(BaseModel):
    case_id: str
    event_type: str
    event_data: Dict[str, Any]
    pdf_path: Optional[str] = None
    detected_at: datetime
    raw_text: Optional[str] = None

# ----------------------------------------------------------------------
# Action package sent to downstream agents
# ----------------------------------------------------------------------
class ActionPackage(BaseModel):
    case_id: str
    event_type: str
    urgency: str
    risk_score: int
    reasons: List[str]
    actions: List[str]
    agents_to_notify: List[str]
    lawyer_approval_needed: bool
    escalation_needed: bool
    document_type: Optional[str] = None
    context: Dict[str, Any]

# ----------------------------------------------------------------------
# Override request from lawyer UI
# ----------------------------------------------------------------------
class OverrideRequest(BaseModel):
    case_id: str
    new_urgency: str = Field(..., pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    reason: str
    advocate_id: str

# ----------------------------------------------------------------------
# Responses
# ----------------------------------------------------------------------
class HealthResponse(BaseModel):
    redis: bool
    database: bool
    groq: bool
    status: str

class StatusResponse(BaseModel):
    processed_today: int
    last_event_at: Optional[datetime] = None
    queue_size: int

class RiskScoreResponse(BaseModel):
    case_id: str
    risk_score: int
    factors: List[str]
    calculated_at: datetime
