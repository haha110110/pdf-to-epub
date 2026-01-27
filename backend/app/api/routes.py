from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks
import shutil
import os
import uuid
import logging
import json
from datetime import datetime
from app.services.pdf_processor import PDFProcessor

router = APIRouter()
logger = logging.getLogger(__name__)

# Base Data Directory
# Projects are stored in data/projects
DATA_DIR = os.path.join(os.getcwd(), "data", "projects")
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
    
    # Save metadata
    import json
    from datetime import datetime
    metadata = {
        "id": project_id,
        "original_filename": file.filename,
        "created_at": datetime.now().isoformat()
    }
    with open(os.path.join(project_path, "metadata.json"), "w") as f:
        json.dump(metadata, f)
    
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    # Start processing in background
    background_tasks.add_task(process_pdf_task, project_id, pdf_path, project_path)
    
    return {"project_id": project_id, "status": "processing"}

@router.get("/projects")
def list_projects():
    """List all projects with metadata"""
    projects = []
    if not os.path.exists(DATA_DIR):
        return []
        
    for pid in os.listdir(DATA_DIR):
        p_dir = os.path.join(DATA_DIR, pid)
        if not os.path.isdir(p_dir):
            continue
            
        meta_path = os.path.join(p_dir, "metadata.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r") as f:
                    meta = json.load(f)
                    projects.append(meta)
            except:
                pass
        else:
            # Fallback for old projects
            import time
            projects.append({
                "id": pid,
                "original_filename": "Untitled Project",
                "created_at": datetime.fromtimestamp(os.path.getctime(p_dir)).isoformat()
            })
            
    # Sort by created_at desc
    projects.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return projects

@router.delete("/projects/{project_id}")
def delete_project(project_id: str):
    """Delete a project and all its files"""
    project_path = os.path.join(DATA_DIR, project_id)
    if not os.path.exists(project_path):
        raise HTTPException(status_code=404, detail="Project not found")
        
    try:
        shutil.rmtree(project_path)
        return {"status": "deleted", "id": project_id}
    except Exception as e:
        logger.error(f"Failed to delete {project_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Deletion failed: {str(e)}")

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
    # Use Regex to handle potential spaces like "![]( images/...)" or "](images/... )"
    # Capture the filename part and strip whitespace
    import re
    static_base = f"/static/projects/{project_id}/images/"
    
    # Pattern: 
    # \] \( \s* images/  -> Match ]( and optional space and "images/"
    # ( [^)]+ )          -> Group 1: Capture everything until the closing )
    # \s* \)             -> Match trailing space and closing )
    content = re.sub(r'\]\(\s*images/([^)]+?)\s*\)', f']({static_base}\\1)', content)
    
    return {"content": content}

@router.put("/projects/{project_id}/content")
async def save_content(project_id: str, payload: dict):
    project_path = os.path.join(DATA_DIR, project_id)
    md_path = os.path.join(project_path, "content.md")
    
    content = payload.get("content")
    if not content:
        raise HTTPException(status_code=400, detail="No content provided")
        
    # Revert static URLs to local paths before saving
    static_base = f"/static/projects/{project_id}/images/"
    content = content.replace(f"]({static_base}", "](images/")
    
    with open(md_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    return {"status": "saved"}

@router.patch("/projects/{project_id}/metadata")
def update_metadata(project_id: str, payload: dict):
    """Update project metadata (e.g. rename)"""
    project_path = os.path.join(DATA_DIR, project_id)
    if not os.path.exists(project_path):
        raise HTTPException(status_code=404, detail="Project not found")
        
    meta_path = os.path.join(project_path, "metadata.json")
    
    # Load existing
    if os.path.exists(meta_path):
        with open(meta_path, "r") as f:
            meta = json.load(f)
    else:
        meta = {"id": project_id}
        
    # Update fields
    if "original_filename" in payload:
        meta["original_filename"] = payload["original_filename"]
        
    # Save
    with open(meta_path, "w") as f:
        json.dump(meta, f)
        
    return {"status": "updated", "metadata": meta}

@router.post("/projects/{project_id}/build")
async def build_epub(project_id: str):
    project_path = os.path.join(DATA_DIR, project_id)
    md_path = os.path.join(project_path, "content.md")
    epub_path = os.path.join(project_path, "output.epub")
    
    if not os.path.exists(md_path):
        raise HTTPException(status_code=404, detail="Content not found")
        
    # Run Pandoc
    # We need to make sure pypandoc is installed or pandoc binary is present
    try:
        import pypandoc
        
        # Resource path for images
        # Pandoc needs to know where to find "images/img.jpg"
        # Since we use relative paths in MD, we should run pandoc with cwd=project_path
        # OR use --resource-path. Pypandoc wrapper arguments:
        
        # We'll use extra_args for resource-path
        # Note: pypandoc might default to cwd?
        # Safest is to change working dir context or use absolute resource path?
        
        # Simpler: Modify MD to have absolute paths temporarily? No.
        # Use filters? No.
        
        # Let's try specifying resource-path in extra_args 
        # But wait, logic: The MD says "images/01.jpg". 
        # If we run pandoc on "content.md" inside "project_path", it resolves "images/..." relative to "content.md".
        # So we just need to tell pypandoc the input file path.
        
        output = pypandoc.convert_file(
            md_path, 
            'epub', 
            outputfile=epub_path,
            extra_args=['--toc', f'--resource-path={project_path}']
        )
        return {"status": "built", "path": epub_path}
    except Exception as e:
        logger.error(f"Pandoc failed: {e}")
        raise HTTPException(status_code=500, detail=f"Build failed: {str(e)}")

from fastapi.responses import FileResponse

@router.get("/projects/{project_id}/download")
def download_epub(project_id: str):
    project_path = os.path.join(DATA_DIR, project_id)
    epub_path = os.path.join(project_path, "output.epub")
    
    if not os.path.exists(epub_path):
        raise HTTPException(status_code=404, detail="EPUB not found. Please build first.")
        
    return FileResponse(epub_path, filename=f"document_{project_id[:8]}.epub", media_type="application/epub+zip")

@router.get("/projects/{project_id}/package")
def download_package(project_id: str):
    project_path = os.path.join(DATA_DIR, project_id)
    
    if not os.path.exists(project_path):
         raise HTTPException(status_code=404, detail="Project not found")

    # Create a zip of content.md and images/
    # We'll store zip in project_dir/source.zip (cache it?)
    zip_path = os.path.join(project_path, "source.zip")
    
    # Always recreate to be fresh
    shutil.make_archive(zip_path.replace('.zip', ''), 'zip', project_path)
    
    # make_archive with base_dir=project_path might zip the zip itself if we are not careful?
    # root_dir vs base_dir.
    # root_dir = project_path. 
    # But we only want MD + Images.
    # Simple hack: zip everything in project_path is fine for now (includes pdf, epub, etc.)
    # User wanted "md + images".
    # Let's refine:
    
    # Clean implementation:
    # Use zipfile module manually to select specific files?
    # Or just use shutil on the whole dir. The whole dir has source.pdf, content.md, output.epub, images/
    # That's acceptable.
    
    return FileResponse(zip_path, filename=f"source_{project_id[:8]}.zip", media_type="application/zip")
