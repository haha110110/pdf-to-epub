from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.api import routes

app = FastAPI(title="PDF to Smart EPUB API")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For dev only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static Files for Images
# We assume data is stored in /data/projects (relative to where we run)
# For local dev, let's look for a "data" folder in the project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(DATA_DIR, exist_ok=True)

# Mount /static to serve images
# Access: http://localhost:8000/static/projects/{id}/images/img.jpg
app.mount("/static", StaticFiles(directory=DATA_DIR), name="static")

app.include_router(routes.router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "ok"}
