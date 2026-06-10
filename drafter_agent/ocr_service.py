import pytesseract
from PIL import Image
import io
import logging
import os

logger = logging.getLogger(__name__)

# NOTE: For Windows, you MUST have Tesseract installed and specify the executable path
# Download from: https://github.com/UB-Mannheim/tesseract/wiki
# Uncomment and update the path below if Tesseract is not in your system PATH
tesseract_path = os.getenv("TESSERACT_CMD_PATH", r'C:\Program Files\Tesseract-OCR\tesseract.exe')
if os.path.exists(tesseract_path):
    pytesseract.pytesseract.tesseract_cmd = tesseract_path

def extract_text_from_image(image_bytes: bytes) -> str:
    """Extracts text from an image bytestream using Tesseract OCR."""
    try:
        image = Image.open(io.BytesIO(image_bytes))
        # Basic enhancement can be added here
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        logger.error(f"Error during OCR extraction: {e}")
        raise ValueError(f"Could not extract text from image: {e}")
