import os
import google.generativeai as genai
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    logger.warning("GEMINI_API_KEY not found in environment variables")

model = genai.GenerativeModel('gemini-2.5-flash')

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

        elif document_type == 'ADJOURNMENT_APPLICATION':
            prompt = f"""You are a legal assistant. Draft an adjournment application in the exact format 
used by Madurai District Court. Include:
- Court header format: 'In the Court of District Munsif, Madurai'
- Case number: {case_id}
- Petitioner: {context.get('petitioner_name', '[Petitioner Name]')} ... Petitioner
- Respondent: {context.get('respondent_name', '[Respondent Name]')} ... Respondent
- PETITION FOR ADJOURNMENT as header
- Body stating: advocate cannot attend, reason: {context.get('reason', 'personal reasons')}, adjournment count: {context.get('adjournment_count', 0)}
- Signature line at bottom
Keep formal legal language. This will be filed in court."""
            response = model.generate_content(prompt)
            return response.text

        elif document_type == 'ORDER_SUMMARY':
            language = context.get('language', 'tamil')
            prompt = f"""You are a legal assistant in India. Read this court order and create TWO summaries:

1. For Advocate (detailed, legal language):
   - What judge ordered
   - What client must do
   - Deadline
   - Consequence if not followed
   - Urgency level

2. For Client (plain language, use {language} language):
   - Explain what court decided in simple words
   - List exactly what client needs to do
   - Give deadline clearly
   - Warn about consequences
   - Keep it short and clear

Order text: {context.get('order_text')}
Format as:
---ADVOCATE VERSION---
[advocate summary]

---CLIENT VERSION---
[client summary in {language}]"""
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
