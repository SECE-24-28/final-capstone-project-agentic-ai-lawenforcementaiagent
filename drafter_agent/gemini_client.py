import os
import google.generativeai as genai
import logging
from dotenv import load_dotenv
from datetime import datetime  
load_dotenv()
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY not found in environment variables")

model = genai.GenerativeModel('gemini-3-flash-preview')

async def generate_document(document_type: str, context: dict, case_id: str):
    """Generates a legal document via Google Gemini API."""
    try:
        if document_type == 'HEARING_BRIEF':
            prompt = f"""You are a legal assistant in India. Read this case information and generate a 
hearing preparation brief for the advocate. Include:
1. Case number, date, time, court hall
2. What the last order says (critical)
3. Documents that must be in hand
4. Opponent's last arguments
5. Strong points for the advocate
6. Client confirmation status
Keep it concise but complete.

CASE DETAILS:
- Case Number: {case_id}
- Hearing Date: {context.get('hearing_date')} at {context.get('hearing_time')}
- Court Hall: {context.get('hall')}

LAST ORDER:
{context.get('last_order')}

OPPONENT ARGUMENTS:
{context.get('opponent_arguments')}

CASE HISTORY:
{context.get('case_history')}
"""
            response = model.generate_content(prompt)
            return response.text

        elif document_type == 'ADJOURNMENT_REASON':
            raw_reason = context.get('reason', 'personal reasons')
            prompt = f"""You are a formal legal assistant.
The user provided this raw, brief reason for why they need an adjournment today:
"{raw_reason}"
Convert this into exactly ONE highly formal, perfectly structured legal sentence.
It must start exactly with the word "That ".
Example: "That the counsel for the Petitioner is suffering from severe viral fever and is therefore not in a position to appear before this Hon'ble Court today."
Return ONLY the sentence, no quotes, no extra text."""
            response = model.generate_content(prompt)
            # Strip any stray quotes and whitespace
            return response.text.replace('"', '').strip()
        elif document_type == 'ORDER_SUMMARY':
            language = context.get('language', 'tamil')
            prompt = f"""You are a legal assistant in India. Read this court order and create TWO packages.

Lawyer Package (Detailed, Legal terminology):
1. Technical order analysis (what judge said legally)
2. Case history context (previous orders, arguments)
3. Risk assessment (what could go wrong)
4. Action items (what to do today, this week, by deadline)
5. Appeal implications (if anything goes wrong)
6. Client confirmation status (have you talked to client?)
7. Strategic notes (opponent's position, strength of yours)
8. Similar cases (precedent from Indian Kanoon)
9. Checklist (step-by-step what to do)
10. Timeline (exact dates for each action)

Client Package (Simple language, use {language} language):
1. What the court said (in their language)
2. What it means for them
3. What documents to bring
4. By when (deadline)
5. What happens if they don't
6. Step-by-step action items
7. Who to contact (lawyer name: {context.get('lawyer_name', '[Lawyer Name]')}, phone: {context.get('lawyer_phone', '[Lawyer Phone]')})
8. Simple explanation of each step
9. Reassurance (you can win if you do this)
10. Emergency contact (who to call if stuck)

Order text: {context.get('order_text')}

CRITICAL INSTRUCTION: You MUST format your response exactly with these two split headers. Do not use markdown for the headers.

---ADVOCATE VERSION---
[lawyer package text]

---CLIENT VERSION---
[client package text]"""
            response = model.generate_content(prompt)
            content = response.text
            parts = content.split("---CLIENT VERSION---")
            advocate_version = parts[0].replace("---ADVOCATE VERSION---", "").strip()
            client_version = parts[1].strip() if len(parts) > 1 else ""
            return advocate_version, client_version

        elif document_type == 'DOCUMENT_CHECKLIST':
            language = context.get('language', 'English')
            prompt = f"""You are a legal assistant helping a client prepare for court. This case is a {context.get('case_type')} case.
The court ordered: {context.get('last_order')}
Generate a simple checklist of documents the client must carry to the hearing.
Make it very simple — client is not a lawyer.
Use {language} language.
Format as numbered list with simple instructions."""
            response = model.generate_content(prompt)
            return response.text

        elif document_type == 'COUNTER_ARGUMENTS':
            prompt = f"""You are a legal assistant in India. The opponent filed this:
{context.get('opponent_filing')}

Generate counter arguments based on this case history:
{context.get('case_history')}

For each opponent argument, provide:
1. What they claimed
2. Why it is weak
3. Our counter argument with evidence
4. Relevant case law if applicable
Keep it structured for the advocate to use."""
            response = model.generate_content(prompt)
            return response.text
        
        else:
            raise ValueError(f"Unknown document_type: {document_type}")

    except Exception as e:
        logger.error(f"Gemini API error for {document_type}: {e}")
        raise e
