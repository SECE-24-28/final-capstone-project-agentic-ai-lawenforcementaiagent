# e:\VakilAI\drafter_agent\reasoner_agent\reasoner.py
import json
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, List

from config import logger, URGENCY, DIRECT_ESCALATION, REDIS_CHANNELS, REDIS_URL
from database import (
    get_case_full_history,
    update_risk_score,
    save_event_to_db,
    add_lawyer_tag,
)
from safety_checks import run_all_safety_checks, calculate_risk_score
from groq_client import analyse_with_groq
from models import ActionPackage

# ----------------------------------------------------------------------
# Helper – map initial urgency from event type
# ----------------------------------------------------------------------
_INITIAL_URGENCY_MAP = {
    # CRITICAL immediate
    "CONTEMPT_FILED": URGENCY["CRITICAL"],
    "WARRANT_ISSUED": URGENCY["CRITICAL"],
    "CASE_DISMISSED": URGENCY["CRITICAL"],
    "EX_PARTE_ORDER": URGENCY["CRITICAL"],
    "STAY_APPLICATION": URGENCY["CRITICAL"],
    "SHOW_CAUSE_NOTICE": URGENCY["CRITICAL"],
    # HIGH start
    "FINAL_HEARING": URGENCY["HIGH"],
    "OPPONENT_FILED": URGENCY["HIGH"],
    "APPEAL_FILED": URGENCY["HIGH"],
    # MEDIUM start
    "ORDER_PASSED": URGENCY["MEDIUM"],
    "ADJOURNMENT_GRANTED": URGENCY["MEDIUM"],
    # LOW start
    "NEW_HEARING_DATE": URGENCY["LOW"],
}

def _initial_urgency(event_type: str) -> str:
    return _INITIAL_URGENCY_MAP.get(event_type, URGENCY["LOW"])

# ----------------------------------------------------------------------
# Core pipeline – called for every incoming event
# ----------------------------------------------------------------------
async def process_event(event: Dict[str, Any]) -> ActionPackage:
    case_id = event["case_id"]
    event_type = event["event_type"]
    logger.info(
        json.dumps(
            {
                "event": "event_received",
                "case_id": case_id,
                "event_type": event_type,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    )

    # 1️⃣ Pull full case history
    case_data = get_case_full_history(case_id)
    logger.info(
        json.dumps(
            {
                "event": "case_history_pulled",
                "case_id": case_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    )

    # 2️⃣ Initial urgency from event type
    urgency = _initial_urgency(event_type)
    logger.info(
        json.dumps(
            {
                "event": "initial_urgency_classified",
                "case_id": case_id,
                "urgency": urgency,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    )

    # 3️⃣ Run safety checks (may upgrade)
    urgency = run_all_safety_checks(case_data, urgency, event["event_data"])
    logger.info(
        json.dumps(
            {
                "event": "final_urgency_after_safety",
                "case_id": case_id,
                "urgency": urgency,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    )

    # 4️⃣ Calculate & store risk score
    new_score, risk_factors = calculate_risk_score(case_data)
    update_risk_score(case_id, new_score)
    logger.info(
        json.dumps(
            {
                "event": "risk_score_calculated",
                "case_id": case_id,
                "risk_score": new_score,
                "factors": risk_factors,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    )

    # 5️⃣ Groq contextual analysis (optional)
    groq_payload = {
        "raw_text": event.get("raw_text"),
        "event_type": event_type,
        "case_type": case_data["case"]["case_type"],
        "adjournment_count": case_data["case"]["adjournment_count"],
        "last_order_text": case_data["case"]["last_order_text"],
        "lawyer_tags": [t["tag"] for t in case_data["tags"]],
        "case_age_years": (
            datetime.now(timezone.utc) - case_data["case"]["created_at"]
        ).days
        // 365,
        "risk_score": new_score,
    }
    groq_result = await analyse_with_groq(groq_payload)

    if groq_result:
        logger.info(
            json.dumps(
                {
                    "event": "groq_api_responded",
                    "case_id": case_id,
                    "payload": groq_result,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        )
        # Groq may suggest higher urgency
        groq_urgency = groq_result.get("urgency")
        if groq_urgency and URGENCY[groq_urgency] > URGENCY[urgency]:
            urgency = URGENCY[groq_urgency]
            logger.info(
                json.dumps(
                    {
                        "event": "urgency_upgraded_by_groq",
                        "case_id": case_id,
                        "new_urgency": urgency,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                )
            )
    else:
        logger.warning(
            json.dumps(
                {
                    "event": "groq_api_failed",
                    "case_id": case_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
        )

    # ------------------------------------------------------------------
    # 6️⃣ Build action package
    # ------------------------------------------------------------------
    reasons = []
    if urgency in (URGENCY["HIGH"], URGENCY["CRITICAL"]):
        reasons.append("Safety checks or Groq indicated high risk")
    else:
        reasons.append("Initial classification sufficient")

    # Determine actions & agents based on final urgency
    actions = []
    agents = []
    lawyer_approval_needed = False
    escalation_needed = False
    document_type = None

    if urgency == URGENCY["LOW"]:
        actions = ["notify_client_new_hearing", "send_document_checklist"]
        agents = ["communicator"]
    elif urgency == URGENCY["MEDIUM"]:
        actions = [
            "generate_hearing_brief",
            "generate_document_checklist",
            "notify_client",
        ]
        agents = ["drafter", "communicator"]
        lawyer_approval_needed = True
    elif urgency == URGENCY["HIGH"]:
        actions = [
            "generate_hearing_brief",
            "generate_document_checklist",
            "alert_lawyer",
            "notify_client_urgently",
        ]
        agents = ["escalation", "drafter"]
        escalation_needed = True
    else:  # CRITICAL
        actions = [
            "alert_lawyer_immediately",
            "alert_client_urgently",
            "prepare_emergency_response_brief",
        ]
        agents = ["escalation", "drafter", "communicator"]
        escalation_needed = True

    # Document type suggestion from Groq (if any)
    if groq_result and groq_result.get("document_type"):
        document_type = groq_result["document_type"]

    action_pkg = ActionPackage(
        case_id=case_id,
        event_type=event_type,
        urgency=urgency,
        risk_score=new_score,
        reasons=reasons,
        actions=actions,
        agents_to_notify=agents,
        lawyer_approval_needed=lawyer_approval_needed,
        escalation_needed=escalation_needed,
        document_type=document_type,
        context={
            "last_order_text": case_data["case"]["last_order_text"],
            "adjournment_count": case_data["case"]["adjournment_count"],
            "client_id": case_data["case"]["client_id"],
            "client_language": "english",  # placeholder – can be fetched later
            "advocate_id": case_data["case"]["advocate_id"],
            "court_name": case_data["case"]["court_name"],
            "case_type": case_data["case"]["case_type"],
            "lawyer_tags": [t["tag"] for t in case_data["tags"]],
            "pdf_path": event.get("pdf_path"),
            "immediate_action_required": escalation_needed,
        },
    )

    # ------------------------------------------------------------------
    # 7️⃣ Persist event + action package
    # ------------------------------------------------------------------
    save_event_to_db(
        case_id=case_id,
        event_type=event_type,
        event_data=event["event_data"],
        detected_at=event["detected_at"],
        urgency=urgency,
        action_pkg=action_pkg.dict(),
    )
    logger.info(
        json.dumps(
            {
                "event": "event_saved_to_database",
                "case_id": case_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    )

    # ------------------------------------------------------------------
    # 8️⃣ Publish to downstream agents (Redis)
    # ------------------------------------------------------------------
    import redis.asyncio as redis

    async def _publish(channel: str, payload: dict):
        try:
            r = await redis.from_url(REDIS_URL)
            await r.publish(channel, json.dumps(payload))
            await r.close()
        except Exception as exc:
            logger.error(
                json.dumps(
                    {
                        "event": "redis_publish_failed",
                        "channel": channel,
                        "error": str(exc),
                        "case_id": case_id,
                    }
                )
            )

    # Direct escalation (Rule 8)
    if event_type in DIRECT_ESCALATION:
        # fire escalation immediately
        asyncio.create_task(
            _publish(REDIS_CHANNELS["ESCALATION"], action_pkg.dict())
        )
        logger.info(
            json.dumps(
                {
                    "event": "escalation_agent_notified",
                    "case_id": case_id,
                    "urgency": urgency,
                }
            )
        )

    # Normal routing based on urgency
    if urgency == URGENCY["LOW"]:
        asyncio.create_task(
            _publish(REDIS_CHANNELS["COMMUNICATOR"], action_pkg.dict())
        )
    elif urgency == URGENCY["MEDIUM"]:
        asyncio.create_task(_publish(REDIS_CHANNELS["DRAFTER"], action_pkg.dict()))
        asyncio.create_task(
            _publish(REDIS_CHANNELS["COMMUNICATOR"], action_pkg.dict())
        )
    elif urgency == URGENCY["HIGH"]:
        asyncio.create_task(_publish(REDIS_CHANNELS["ESCALATION"], action_pkg.dict()))
        asyncio.create_task(_publish(REDIS_CHANNELS["DRAFTER"], action_pkg.dict()))
    else:  # CRITICAL
        asyncio.create_task(_publish(REDIS_CHANNELS["ESCALATION"], action_pkg.dict()))
        asyncio.create_task(_publish(REDIS_CHANNELS["DRAFTER"], action_pkg.dict()))
        asyncio.create_task(
            _publish(REDIS_CHANNELS["COMMUNICATOR"], action_pkg.dict())
        )

    # Log final package built
    logger.info(
        json.dumps(
            {
                "event": "action_package_built",
                "case_id": case_id,
                "package": action_pkg.dict(),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    )

    return action_pkg
