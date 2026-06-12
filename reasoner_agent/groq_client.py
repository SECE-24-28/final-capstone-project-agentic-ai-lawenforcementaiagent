# e:\VakilAI\drafter_agent\reasoner_agent\groq_client.py
import json
import asyncio
import logging
from typing import Dict, Any, Optional
import os
import httpx
from config import GROQ_API_KEY, logger

_GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
_MAX_RETRIES = 3
_RETRY_WAIT = 2  # seconds

def _make_payload(event: Dict[str, Any]) -> Dict[str, Any]:
    system_prompt = (
        "You are a legal reasoning assistant for Indian courts. "
        "Given the raw event text, event type and case context, "
        "return a JSON object with the following fields:\n"
        "- urgency (LOW/MEDIUM/HIGH/CRITICAL)\n"
        "- immediate_action (bool)\n"
        "- client_notification (bool)\n"
        "- document_type (string or null)\n"
        "- reason (one‑sentence explanation)\n"
        "Only output the JSON, no extra text."
    )
    user_msg = json.dumps(event, indent=2)
    return {
        "model": "llama3-70b-8192",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_msg},
        ],
        "temperature": 0.2,
        "max_tokens": 500,
    }

async def analyse_with_groq(event_payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    async with httpx.AsyncClient() as client:
        for attempt in range(1, _MAX_RETRIES + 1):
            try:
                response = await client.post(
                    _GROQ_ENDPOINT,
                    headers=headers,
                    json=_make_payload(event_payload),
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                # Groq returns a list of choices; we need the first message content
                content = data["choices"][0]["message"]["content"]
                # Expect JSON string
                return json.loads(content)
            except Exception as exc:
                logger.error(
                    f"Groq call attempt {attempt} failed: {exc}"
                )
                if attempt == _MAX_RETRIES:
                    return None
                await asyncio.sleep(_RETRY_WAIT)
    return None
