import asyncio
import json
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
import redis.asyncio as redis
from dotenv import load_dotenv

from models import GenerateRequest, ApproveRequest, DocumentResponse, ApprovalResponse, PendingResponse, PendingDocument
from database import save_document, update_document_status, get_pending_documents, get_document_by_id, delete_document
from gemini_client import generate_document
from ocr_service import extract_text_from_file

load_dotenv()
logging.basicConfig(level=getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO))
logger = logging.getLogger(__name__)

redis_client = None

async def listen_to_redis():
    """Background task to listen for tasks from Reasoner on Redis."""
    global redis_client
    if not redis_client:
        return
    
    pubsub = redis_client.pubsub()
    await pubsub.subscribe("drafter_tasks")
    logger.info("Listening to Redis channel: drafter_tasks")
    
    try:
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    case_id = data.get("case_id")
                    doc_type = data.get("document_type")
                    context = data.get("context", {})
                    
                    logger.info(f"Received task via Redis queue for {case_id}, {doc_type}")
                    
                    result = await generate_document(doc_type, context, case_id)
                    
                    content = ""
                    client_content = None
                    language = None
                    
                    if doc_type == 'ORDER_SUMMARY':
                        content, client_content = result
                        language = context.get('language', 'tamil')
                    else:
                        content = result
                    
                    doc_id = save_document(
                        case_id=case_id,
                        document_type=doc_type,
                        content=content,
                        client_content=client_content,
                        language=language
                    )

                    await redis_client.publish("drafter_results", json.dumps({
                        "doc_id": doc_id,
                        "case_id": case_id,
                        "status": "pending_approval"
                    }))
                except Exception as e:
                    logger.error(f"Error processing redis task: {e}")
    except asyncio.CancelledError:
        logger.info("Redis listener task cancelled")
    finally:
        await pubsub.unsubscribe("drafter_tasks")
        await pubsub.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis_client
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        redis_client = redis.from_url(redis_url)
        # Test connection
        await redis_client.ping()
        asyncio.create_task(listen_to_redis())
        logger.info("Connected to Redis")
    except Exception as e:
        logger.error(f"Failed to connect to redis: {e}. Queue functionality will be disabled.")
        redis_client = None
    
    yield
    
    if redis_client:
        await redis_client.close()

app = FastAPI(title="VakilAgent - Drafter Agent", description="Generates legal documents automatically", lifespan=lifespan)

@app.post("/drafter/generate", response_model=DocumentResponse)
async def generate_endpoint(req: GenerateRequest):
    try:
        logger.info(f"Generating document for case {req.case_id}, type {req.document_type}")
        
        # Determine handling based on document type
        content = ""
        client_content = None
        language = None
        
        if req.document_type == 'ORDER_SUMMARY':
            # Order summary uses Gemini split output
            result = await generate_document(req.document_type, req.context, req.case_id)
            content, client_content = result
            language = req.context.get('language', 'tamil')
        elif req.document_type == 'ADJOURNMENT_APPLICATION':
            # Intercept: Expand User Reason -> Fill Generic HTML Template -> Build PDF -> Cloudinary
            from template_builder import generate_pdf_from_template
            from cloudinary_service import upload_pdf_to_cloudinary
            
            # Use Gemini to expand the dirty reason into a formal legal argument
            logger.info("Enhancing Adjournment Reason via AI...")
            ai_expanded_reason = await generate_document("ADJOURNMENT_REASON", req.context, req.case_id)
            
            template_filename = "generic_adjournment.html"
            temp_pdf = f"templates/adjournments/temp_{req.case_id.replace('/', '_')}.pdf"
            
            # Enrich context for Jinja
            enriched_context = {
                **req.context,
                "court_name": req.context.get("court_name", "_________________").upper(),
                "district": req.context.get("district", "NEW DELHI").upper(),
                "petitioner_name": req.context.get("petitioner_name", "XYZ"),
                "respondent_name": req.context.get("respondent_name", "ABC"),
                "ai_expanded_reason": ai_expanded_reason,
                "filing_party_role": req.context.get("filing_party_role", "petitioner"),
                "filing_party_name": req.context.get("petitioner_name", "XYZ"),
                "current_date": datetime.now().strftime("%d-%m-%Y")
            }
            
            generated_pdf = generate_pdf_from_template(template_filename, enriched_context, temp_pdf)
            
            if generated_pdf:
                cloudinary_url = upload_pdf_to_cloudinary(generated_pdf)
                if cloudinary_url:
                    content = f"PDF GENERATED SUCCESSFULLY: {cloudinary_url}"
                    if os.path.exists(generated_pdf):
                        os.remove(generated_pdf)
                else:
                    content = f"LOCAL PDF GENERATED (Cloudinary Upload Failed): {generated_pdf}"
            else:
                content = "Failed to generate PDF for adjournment application."
        
        # Normal flow for other document types
        else:
            result = await generate_document(req.document_type, req.context, req.case_id)
            content = result
            client_content = None
            language = None

        doc_id = save_document(
            case_id=req.case_id,
            document_type=req.document_type,
            content=content,
            client_content=client_content,
            language=language
        )
        
        return DocumentResponse(
            doc_id=doc_id,
            document_type=req.document_type,
            content=content,
            client_content=client_content,
            approval_status="pending",
            created_at=datetime.now(timezone.utc).isoformat()
        )
    except Exception as e:
        logger.error(f"Error generating document: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/drafter/approve/{doc_id}", response_model=ApprovalResponse)
async def approve_endpoint(doc_id: str, req: ApproveRequest):
    try:
        logger.info(f"Updating approval status for {doc_id} to {req.action}")
        status = req.action
        if status == "approve":
            next_status = "approved"
            update_document_status(doc_id, next_status, req.edited_content)
        elif status == "reject":
            delete_document(doc_id)
            logger.info(f"Deleted rejected document {doc_id} from database")
            return ApprovalResponse(
                doc_id=doc_id,
                approval_status="deleted",
                next_action="none"
            )
        elif status == "edit":
            next_status = "edited"
            update_document_status(doc_id, next_status, req.edited_content)
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
            
        next_action = "send_to_client" if next_status in ["approved", "edited"] else "escalate"
        
        return ApprovalResponse(
            doc_id=doc_id,
            approval_status=next_status,
            next_action=next_action
        )
    except Exception as e:
        logger.error(f"Error updating approval status: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/drafter/pending", response_model=PendingResponse)
async def get_pending_endpoint():
    try:
        rows = get_pending_documents()
        documents = []
        for r in rows:
            created_at = r.get("created_at")
            wait_time = 0
            if created_at:
                try:
                    if created_at.tzinfo is None:
                        created_at = created_at.replace(tzinfo=timezone.utc)
                    wait_time = int((datetime.now(timezone.utc) - created_at).total_seconds() / 60)
                except Exception:
                    pass
                
            documents.append(PendingDocument(
                doc_id=f"doc_{r['id']}",
                case_id=r.get('case_id', ''),
                document_type=r.get('document_type', ''),
                preview=r.get('preview', ''),
                created_at=created_at.isoformat() if created_at else "",
                wait_time_minutes=wait_time
            ))
            
        return PendingResponse(count=len(documents), documents=documents)
    except Exception as e:
        logger.error(f"Error getting pending documents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/drafter/document/{doc_id}")
async def get_document_endpoint(doc_id: str):
    try:
        doc = get_document_by_id(doc_id)
        if not doc:
            raise HTTPException(status_code=404, detail="Document not found")
        
        created_at = doc.get('created_at')
        
        return {
            "doc_id": doc_id,
            "content": doc.get('content', ''),
            "approval_status": doc.get('approval_status', ''),
            "created_at": created_at.isoformat() if created_at else ""
        }
    except Exception as e:
        logger.error(f"Error getting document: {e}")
        if isinstance(e, HTTPException):
            raise
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/drafter/ocr")
async def ocr_court_order_endpoint(file: UploadFile = File(...)):
    """Uploads an image or PDF of a court order and returns the extracted text."""
    try:
        content_type = file.content_type
        is_pdf = content_type == "application/pdf"
        
        if not (content_type.startswith("image/") or is_pdf):
            raise HTTPException(status_code=400, detail="Only images and PDFs are supported for extraction")
            
        file_bytes = await file.read()
        logger.info(f"Extracting text from uploaded {content_type} file")
        
        extracted_text = extract_text_from_file(file_bytes, is_pdf=is_pdf)
        
        return {
            "status": "success",
            "filename": file.filename,
            "extracted_text": extracted_text
        }
    except Exception as e:
        logger.error(f"Error processing upload: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/drafter/ocr_order_summary", response_model=DocumentResponse)
async def ocr_order_summary_endpoint(
    file: UploadFile = File(...),
    case_id: str = Form(...),
    language: str = Form("tamil"),
    lawyer_name: str = Form(""),
    lawyer_phone: str = Form("")
):
    """Integrated endpoint: Upload PDF/Image, runs OCR, then dynamically generates Lawyer/Client Packages."""
    try:
        content_type = file.content_type
        is_pdf = content_type == "application/pdf"
        
        if not (content_type.startswith("image/") or is_pdf):
            raise HTTPException(status_code=400, detail="Only images and PDFs are supported.")
            
        file_bytes = await file.read()
        logger.info(f"Extracting OCR text from uploaded memory file for case {case_id}...")
        
        extracted_text = extract_text_from_file(file_bytes, is_pdf=is_pdf)
        
        context = {
            "order_text": extracted_text,
            "language": language,
            "lawyer_name": lawyer_name,
            "lawyer_phone": lawyer_phone
        }
        
        logger.info(f"Generating full ORDER_SUMMARY via AI...")
        result = await generate_document("ORDER_SUMMARY", context, case_id)
        
        content, client_content = result
        
        doc_id = save_document(
            case_id=case_id,
            document_type="ORDER_SUMMARY",
            content=content,
            client_content=client_content,
            language=language
        )
        
        return DocumentResponse(
            doc_id=doc_id,
            document_type="ORDER_SUMMARY",
            content=content,
            client_content=client_content,
            approval_status="pending",
            created_at=datetime.now(timezone.utc).isoformat()
        )
    except Exception as e:
        logger.error(f"Error processing OCR Order Summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8004))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("main:app", host=host, port=port, reload=True)
