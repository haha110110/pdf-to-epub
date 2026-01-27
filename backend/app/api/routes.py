from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
import shutil
import os
import uuid
import logging
from app.services.pdf_processor import PDFProcessor

router = APIRouter()
logger = logging.getLogger(__name__)

# Base Data Directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data", "projects")
os.makedirs(DATA_DIR, exist_ok=True)

@router.post("/upload")
async def upload_pdf(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    """
    Upload PDF and start processing.
    Returns project_id.
    """
    project_id = str(uuid.uuid4())
    project_path = os.path.join(DATA_DIR, project_id)
    os.makedirs(project_path, exist_ok=True)
    
    pdf_path = os.path.join(project_path, "source.pdf")
    
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Start processing in background
    background_tasks.add_task(process_pdf_task, project_id, pdf_path, project_path)
    
    return {"project_id": project_id, "status": "processing"}

def process_pdf_task(project_id: str, pdf_path: str, output_dir: str):
    logger.info(f"Starting processing for project {project_id}")
    try:
        processor = PDFProcessor(pdf_path, output_dir)
        processor.process()
        logger.info(f"Finished processing for project {project_id}")
    except Exception as e:
        logger.error(f"Failed to process project {project_id}: {e}")
        # In a real app, update DB status to FAILED

@router.get("/projects/{project_id}/status")
def get_status(project_id: str):
    project_path = os.path.join(DATA_DIR, project_id)
    if not os.path.exists(project_path):
        raise HTTPException(status_code=404, detail="Project not found")
        
    md_path = os.path.join(project_path, "content.md")
    if os.path.exists(md_path):
        return {"status": "ready"}
    return {"status": "processing"}

@router.get("/projects/{project_id}/content")
def get_content(project_id: str):
    """
    Get Markdown content.
    Automatically replaces local image paths with static URLs.
    """
    project_path = os.path.join(DATA_DIR, project_id)
    md_path = os.path.join(project_path, "content.md")
    
    if not os.path.exists(md_path):
        raise HTTPException(status_code=404, detail="Content not ready")
        
    with open(md_path, "r", encoding="utf-8") as f:
        content = f.read()
        
    # Replace "images/" with "/static/projects/{id}/images/"
    # Note: Regex replacement might be safer to avoid partial matches
    static_base = f"/static/projects/{project_id}/images/"
    content = content.replace("](images/", f"]({static_base}")
    
    return {"content": content}

@router.put("/projects/{project_id}/content")
async def save_content(project_id: str, payload: dict):
    project_path = os.path.join(DATA_DIR, project_id)
    md_path = os.path.join(project_path, "content.md")
    
    content = payload.get("content")
    if not content:
        raise HTTPException(status_code=400, detail="No content provided")
        
    # Revert static URLs to local paths before saving
    # "/static/projects/{id}/images/" -> "images/"
    static_base = f"/static/projects/{project_id}/images/"
    content = content.replace(f"]({static_base}", "](images/")
    
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    return {"status": "saved"}
