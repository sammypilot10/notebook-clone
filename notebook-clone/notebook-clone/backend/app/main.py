from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any # <--- Added List, Dict, Any
from dotenv import load_dotenv
import os

# Load environment variables
load_dotenv()

from app.ingestion import process_upload
from app.chat import get_answer

app = FastAPI(title="NotebookLM Clone")

# --- CORS CONFIGURATION ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)
# ---------------------------

# Updated Request Model (Now includes history)
class ChatRequest(BaseModel):
    question: str
    doc_id: Optional[str] = None
    history: List[Dict[str, Any]] = [] # <--- NEW: Receives chat history from frontend

@app.get("/")
def home():
    return {"status": "System is active"}

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDFs are supported")
    
    return await process_upload(file)

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # Pass question, history, AND doc_id to the chat engine
    response = get_answer(request.question, request.history, request.doc_id) 
    return response

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)