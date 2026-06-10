from pydantic import BaseModel
from typing import Dict, Any, List, Optional

class GenerateRequest(BaseModel):
    case_id: str
    event_type: Optional[str] = None
    document_type: str
    context: Dict[str, Any]

class ApproveRequest(BaseModel):
    action: str  # "approve" | "edit" | "reject"
    edited_content: Optional[str] = None

class DocumentResponse(BaseModel):
    doc_id: str
    document_type: str
    content: str
    approval_status: str
    created_at: str

class ApprovalResponse(BaseModel):
    doc_id: str
    approval_status: str
    next_action: str

class PendingDocument(BaseModel):
    doc_id: str
    case_id: str
    document_type: str
    preview: str
    created_at: str
    wait_time_minutes: int

class PendingResponse(BaseModel):
    count: int
    documents: List[PendingDocument]
