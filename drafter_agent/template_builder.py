import os
import requests
import logging
from jinja2 import Environment, FileSystemLoader, select_autoescape
from xhtml2pdf import pisa
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
logger = logging.getLogger(__name__)

# Configure Gemini for AI template conversion
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-pro')

def fetch_indiankanoon_template(court_name: str, document_type: str = "adjournment application") -> str:
    """
    Searches IndianKanoon for a specific court's document format to use as a baseline.
    Requires an IndianKanoon API Token in the .env file.
    """
    token = os.getenv("INDIANKANOON_API_TOKEN")
    if not token:
        logger.warning("INDIANKANOON_API_TOKEN largely required for live IndianKanoon API fetching.")
        
    base_url = "https://indiankanoon.org/api/search/"
    query = f"{document_type} {court_name}"
    
    headers = {
        "Authorization": f"Token {token}",
        "Content-Type": "application/json"
    }
    
    try:
        # We query the api for a judgement that likely contains our format
        response = requests.post(base_url, headers=headers, json={"q": query, "type": "judgement"})
        if response.status_code == 200:
            data = response.json()
            # In reality, you'd parse data.get("docs", []) to find the most relevant snippet/text
            if "docs" in data and len(data["docs"]) > 0:
                raw_text = data["docs"][0].get("content", "")
                return raw_text
            return ""
        else:
            logger.error(f"IndianKanoon API returned {response.status_code}")
            return ""
    except Exception as e:
        logger.error(f"Failed to fetch from IndianKanoon: {e}")
        return ""

def ai_generate_html_template(raw_text: str, court_name: str) -> str:
    """
    Uses Gemini AI to read the raw, messy court document from IndianKanoon 
    and output a perfectly structured HTML template with Jinja2 variables.
    """
    prompt = f"""You are an expert legal formatter and web developer. 
I am going to provide you with a raw text snippet from an Indian court ({court_name}).
I need you to convert this court format into a clean HTML template.

Rules:
1. Output ONLY pure HTML. Do not output markdown, no ```html tags.
2. Maintain the absolute formal structure (center alignment for headers, right align for signatures).
3. Replace specific case details (like names, dates, case numbers) with Jinja2 placeholders.
   Examples: {{{{ petitioner_name }}}}, {{{{ respondent_name }}}}, {{{{ case_id }}}}, {{{{ current_year }}}}, {{{{ reason }}}}
4. Ensure standard font styling like Times New Roman.

Raw Court Text Snippet:
{raw_text}
"""
    try:
        response = model.generate_content(prompt)
        html_content = response.text.replace("```html", "").replace("```", "").strip()
        
        # Save to templates directory automatically
        os.makedirs("templates/adjournments", exist_ok=True)
        safe_name = court_name.replace(" ", "_").lower()
        file_path = f"templates/adjournments/{safe_name}.html"
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        logger.info(f"Successfully generated HTML template for {court_name} at {file_path}")
        return file_path
    except Exception as e:
        logger.error(f"Gemini Template AI parsing failed: {e}")
        return ""


def generate_pdf_from_template(template_name: str, context: dict, output_pdf_path: str):
    """
    Takes an AI-generated HTML template, injects context via Jinja2, 
    and generates a highly formatted final PDF using xhtml2pdf.
    """
    try:
        env = Environment(
            loader=FileSystemLoader("templates/adjournments"),
            autoescape=select_autoescape(['html', 'xml'])
        )
        template = env.get_template(template_name)
        html_out = template.render(**context)
        
        with open(output_pdf_path, "w+b") as pdf_file:
            pisa_status = pisa.CreatePDF(
                html_out, 
                dest=pdf_file
            )
        
        if pisa_status.err:
            raise Exception("PDF Generation Error!")
            
        logger.info(f"Successfully generated PDF: {output_pdf_path}")
        return output_pdf_path
        
    except Exception as e:
        logger.error(f"Failed to compile PDF: {e}")
        return None
