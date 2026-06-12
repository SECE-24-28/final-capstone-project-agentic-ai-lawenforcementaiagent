# e:\VakilAI\drafter_agent\reasoner_agent\main.py
import asyncio
import json
from datetime import datetime, timezone
from typing import List
from dotenv import load_dotenv
import uvicorn
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException, BackgroundTasks

from config import (
    HOST,
    PORT,
    LOG_LEVEL,
    REDIS_URL,
    REDIS_CHANNELS,
    logger,
    GROQ_API_KEY,
)
from models import (
    WatcherEvent,
    ActionPackage,
    OverrideRequest,
    HealthResponse,
    StatusResponse,
    RiskScoreResponse,
)
from reasoner import process_event
from database import get_case_full_history, add_lawyer_tag

load_dotenv()

app = FastAPI(title="VakilAgent Reasoner", version="1.0.0")

# ----------------------------------------------------------------------
# Background Redis listener – starts on app startup
# ----------------------------------------------------------------------
@app.on_event("startup")
async def startup_event():
    logger.info("Reasoner service starting up")
    asyncio.create_task(listen_to_watcher())

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Reasoner service shutting down")

async def listen_to_watcher():
    while True:
        try:
            r = redis.from_url(REDIS_URL, decode_responses=True)
            # Add ping_interval to prevent the exact 5-second idle read timeout seen on this Windows environment
            pubsub = r.pubsub()
            await pubsub.subscribe(REDIS_CHANNELS["REASONER"])
            logger.info("Subscribed to Redis channel: reasoner_tasks")
            async for message in pubsub.listen():
                if message["type"] != "message":
                    continue
                try:
                    # decode_responses=True makes message["data"] a string
                    if isinstance(message["data"], bytes):
                        payload = json.loads(message["data"].decode("utf-8"))
                    else:
                        payload = json.loads(message["data"])
                    # Validate required fields
                    for field in ("case_id", "event_type", "detected_at"):
                        if field not in payload:
                            raise ValueError(f"Missing required field {field}")
                    # Process asynchronously – do not block listener
                    asyncio.create_task(handle_event(payload))
                except Exception as exc:
                    logger.error(
                        json.dumps(
                            {
                                "event": "redis_message_error",
                                "error": str(exc),
                            }
                        )
                    )
        except Exception as e:
            # If it's a TimeoutError, it's just the idle socket dropping. Reconnect instantly.
            if "Timeout" in str(e) or "TimeoutError" in str(type(e)):
                # Don't sleep on a timeout, just instantly reform the connection so we don't miss events
                continue
            logger.warning(f"Redis listener dropped. Reconnecting in 3s... Error: {e}")
            await asyncio.sleep(3)

async def handle_event(event_payload: dict):
    try:
        # Convert timestamps to datetime objects
        event_payload["detected_at"] = datetime.fromisoformat(
            event_payload["detected_at"]
        )
        await process_event(event_payload)
    except Exception as exc:
        logger.error(
            json.dumps(
                {
                    "event": "processing_error",
                    "case_id": event_payload.get("case_id"),
                    "error": str(exc),
                }
            )
        )
        # Even on error we still log to supervisor (already done above)

# ----------------------------------------------------------------------
# API ENDPOINT 1 – manual trigger for testing
# ----------------------------------------------------------------------
@app.post("/reasoner/analyse", response_model=ActionPackage)
async def analyse(event: WatcherEvent):
    try:
        # Direct call to pipeline (bypasses Redis)
        action_pkg = await process_event(event.dict())
        return action_pkg
    except ValueError as e:
        # Case not found
        logger.warning(f"Validation Error: {e}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"Internal Server Error: {e}\n{tb}")
        raise HTTPException(status_code=500, detail=tb)

# ----------------------------------------------------------------------
# API ENDPOINT 2 – risk‑score fetch
# ----------------------------------------------------------------------
@app.get("/reasoner/risk-score/{case_id}", response_model=RiskScoreResponse)
async def get_risk_score(case_id: str):
    case = get_case_full_history(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")
    # Re‑calculate to show factors (does not persist)
    from safety_checks import calculate_risk_score

    score, factors = calculate_risk_score(case)
    return RiskScoreResponse(
        case_id=case_id,
        risk_score=score,
        factors=factors,
        calculated_at=datetime.now(timezone.utc),
    )

# ----------------------------------------------------------------------
# API ENDPOINT 3 – lawyer overrides urgency
# ----------------------------------------------------------------------
@app.post("/reasoner/override-urgency")
async def override_urgency(req: OverrideRequest, background: BackgroundTasks):
    # Add a tag for audit
    tag = f"urgency overridden to {req.new_urgency}: {req.reason}"
    background.add_task(add_lawyer_tag, req.case_id, tag, req.advocate_id)

    # Re‑run pipeline with forced urgency
    # Fetch current case data to build a synthetic event
    case = get_case_full_history(req.case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Case not found")

    # Build a minimal event payload (event_type kept as ORIGINAL)
    # We will inject the new urgency after safety checks
    synthetic_event = {
        "case_id": req.case_id,
        "event_type": "OVERRIDE",  # placeholder – not used for classification
        "event_data": {},
        "pdf_path": None,
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "raw_text": None,
    }

    # Run normal pipeline to get action package, then replace urgency
    action_pkg = await process_event(synthetic_event)
    action_pkg.urgency = req.new_urgency
    action_pkg.lawyer_approval_needed = False
    action_pkg.escalation_needed = req.new_urgency in ("HIGH", "CRITICAL")
    # Re‑publish with new urgency
    import redis.asyncio as redis

    async def _publish(channel: str, payload: dict):
        r = await redis.from_url(REDIS_URL)
        await r.publish(channel, json.dumps(payload))
        await r.close()

    # Route based on new urgency
    if req.new_urgency == "LOW":
        background.add_task(_publish, REDIS_CHANNELS["COMMUNICATOR"], action_pkg.dict())
    elif req.new_urgency == "MEDIUM":
        background.add_task(_publish, REDIS_CHANNELS["DRAFTER"], action_pkg.dict())
        background.add_task(_publish, REDIS_CHANNELS["COMMUNICATOR"], action_pkg.dict())
    elif req.new_urgency == "HIGH":
        background.add_task(_publish, REDIS_CHANNELS["ESCALATION"], action_pkg.dict())
        background.add_task(_publish, REDIS_CHANNELS["DRAFTER"], action_pkg.dict())
    else:  # CRITICAL
        background.add_task(_publish, REDIS_CHANNELS["ESCALATION"], action_pkg.dict())
        background.add_task(_publish, REDIS_CHANNELS["DRAFTER"], action_pkg.dict())
        background.add_task(_publish, REDIS_CHANNELS["COMMUNICATOR"], action_pkg.dict())

    logger.info(
        json.dumps(
            {
                "event": "urgency_override_applied",
                "case_id": req.case_id,
                "new_urgency": req.new_urgency,
                "reason": req.reason,
                "advocate_id": req.advocate_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )
    )
    return {"detail": "Urgency override applied and actions re‑routed"}

# ----------------------------------------------------------------------
# API ENDPOINT 4 – status summary
# ----------------------------------------------------------------------
@app.get("/reasoner/status", response_model=StatusResponse)
async def status():
    # Simple stats – can be expanded later
    r = await redis.from_url(REDIS_URL)
    pending = await r.llen(REDIS_CHANNELS["REASONER"])
    # Count processed today – naive implementation
    # In production you would query a metrics table
    processed_today = 0
    last_event_at = None
    await r.close()
    return StatusResponse(
        processed_today=processed_today,
        last_event_at=last_event_at,
        queue_size=pending,
    )

# ----------------------------------------------------------------------
# API ENDPOINT 5 – health check
# ----------------------------------------------------------------------
@app.get("/reasoner/health", response_model=HealthResponse)
async def health():
    # Redis health
    try:
        r = await redis.from_url(REDIS_URL)
        await r.ping()
        redis_ok = True
        await r.close()
    except Exception:
        redis_ok = False

    # DB health
    try:
        from database import _get_connection

        conn = _get_connection()
        conn.close()
        db_ok = True
    except Exception:
        db_ok = False

    # Groq health (simple token check)
    groq_ok = bool(GROQ_API_KEY)

    overall = "healthy" if all([redis_ok, db_ok, groq_ok]) else "degraded"
    return HealthResponse(
        redis=redis_ok,
        database=db_ok,
        groq=groq_ok,
        status=overall,
    )

# ----------------------------------------------------------------------
# Run server (when executed directly)
# ----------------------------------------------------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host=HOST, port=PORT, reload=True)
