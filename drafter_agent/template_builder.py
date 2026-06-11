import os
import logging
from jinja2 import Environment, FileSystemLoader, select_autoescape
from xhtml2pdf import pisa

logger = logging.getLogger(__name__)


def generate_pdf_from_template(template_name: str, context: dict, output_pdf_path: str):
    """
    Takes an HTML template, injects context via Jinja2,
    and generates a formatted PDF using xhtml2pdf.
    """
    try:
        os.makedirs("templates/adjournments", exist_ok=True)
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
