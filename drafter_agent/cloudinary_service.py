import cloudinary
import cloudinary.uploader
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

cloudinary.config( 
  cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "demo"), 
  api_key = os.getenv("CLOUDINARY_API_KEY", "demo"), 
  api_secret = os.getenv("CLOUDINARY_API_SECRET", "demo") 
)

def upload_pdf_to_cloudinary(file_path: str, public_id: str = None):
    """Uploads a generated PDF out to Cloudinary"""
    try:
        # Pdfs are treated as raw files or images depending on how you want them
        response = cloudinary.uploader.upload(file_path, resource_type="raw", public_id=public_id)
        logger.info(f"Successfully uploaded PDF to Cloudinary. URL: {response['secure_url']}")
        return response['secure_url']
    except Exception as e:
        logger.error(f"Error uploading to Cloudinary: {e}")
        return None
