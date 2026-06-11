from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from .db import Base


class Escalation(Base):
    __tablename__ = "escalations"

    escalation_id = Column(Integer, primary_key=True, index=True)
    case_id = Column(String, index=True)
    advocate_id = Column(String, index=True)
    event_type = Column(String)
    urgency_level = Column(String)
    brief = Column(Text, nullable=True)
    client_id = Column(String, nullable=True, index=True)
    client_name = Column(String, nullable=True)
    client_whatsapp_number = Column(String, nullable=True)
    client_phone = Column(String, nullable=True)
    client_email = Column(String, nullable=True)
    brief_prepared_at = Column(DateTime(timezone=True), server_default=func.now())
    channels_fired_at = Column(DateTime(timezone=True), nullable=True)
    acknowledgement_received_at = Column(DateTime(timezone=True), nullable=True)
    acknowledged_by = Column(String, nullable=True)
    action_taken = Column(Text, nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    total_alerts_sent = Column(Integer, default=0)
    backup_contact_alerted = Column(Boolean, default=False)


class AdvocateProfile(Base):
    __tablename__ = "advocate_profiles"

    advocate_id = Column(String, primary_key=True, index=True)
    name = Column(String)
    whatsapp_number = Column(String, nullable=True)
    phone_number = Column(String, nullable=True)
    email = Column(String, nullable=True)
    push_token = Column(String, nullable=True)
    quiet_hours_start = Column(String, nullable=True)
    quiet_hours_end = Column(String, nullable=True)
    backup_contact_name = Column(String, nullable=True)
    backup_contact_phone = Column(String, nullable=True)
    escalation_preferences = Column(Text, nullable=True)
