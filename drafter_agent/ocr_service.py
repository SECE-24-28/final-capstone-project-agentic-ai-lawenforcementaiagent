import pytesseract
from PIL import Image
import io
import logging
import os
import fitz  #PyMuPDF

logger = logging.getLogger(__name__)

# NOTE: For Windows, you MUST have Tesseract installed and specify the executable path
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
tesseract_path = os.getenv("TESSERACT_CMD_PATH", r'C:\Program Files\Tesseract-OCR\tesseract.exe')
if os.path.exists(tesseract_path):
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

def extract_text_from_file(file_bytes: bytes, is_pdf: bool = False) -> str:
    """Extracts text from an image or PDF bytestream using Tesseract OCR and PyMuPDF."""
    text_content = ""
    try:
        if is_pdf:
            # Open PDF from bytes
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            for i, page in enumerate(doc):
                # 1. Try to extract digital text first (much faster and more accurate)
                page_text = page.get_text()
                
                # 2. If no text was found, it's likely a scanned PDF, so we use OCR
                if not page_text.strip():
                    logger.info(f"Page {i+1} appears to be a scanned image. Running Tesseract OCR...")
                    pix = page.get_pixmap(dpi=300) # high res for better OCR
                    img_bytes = pix.tobytes("png")
                    image = Image.open(io.BytesIO(img_bytes))
                    page_text = pytesseract.image_to_string(image)
                
                text_content += f"\n--- Page {i+1} ---\n{page_text}"
            doc.close()
            return text_content.strip()
        else:
            # Handle standard image
            image = Image.open(io.BytesIO(file_bytes))
            text_content = pytesseract.image_to_string(image)
            return text_content.strip()
            
    except Exception as e:
        logger.error(f"Error during extraction: {e}")
        raise ValueError(f"Could not extract text: {e}")
