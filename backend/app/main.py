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
# In Docker, we map volume to /app/data
STATIC_ROOT = os.path.join(os.getcwd(), "data")
os.makedirs(STATIC_ROOT, exist_ok=True)

# Mount /static to serve images
# Access: http://localhost:8000/static/projects/{id}/images/img.jpg
app.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")

app.include_router(routes.router, prefix="/api")

@app.get("/health")
def health_check():
    return {"status": "ok"}
