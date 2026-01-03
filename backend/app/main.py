from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
import os
import uvicorn

# Load environment variables
load_dotenv()

# Internal imports
from app.ingestion import process_upload
# Ensure app/chat.py exists and has the updated async get_answer function
from app.chat import get_answer 
# NEW: Import the quiz engine
from app.quiz import generate_quiz

app = FastAPI(title="NotebookLM Clone")

# --- CORS CONFIGURATION ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], 
    allow_credentials=True,
    allow_methods=["*"], 
    allow_headers=["*"], 
)

# --- DATA MODELS ---
class ChatRequest(BaseModel):
    question: str
    doc_id: Optional[str] = None
    # Receives previous messages: [{"role": "user", "content": "..."}, ...]
    history: List[Dict[str, Any]] = [] 

# NEW: Model for Quiz Generation
class QuizRequest(BaseModel):
    doc_id: str
    num_questions: int
    difficulty: str = "Hard"

# --- ENDPOINTS ---

@app.get("/")
def home():
    return {"status": "System is active"}

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Handles PDF uploads.
    """
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDFs are supported")
    
    return await process_upload(file)

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """
    Standard JSON Chat Endpoint.
    """
    try:
        # Pass question, history, AND doc_id to the chat logic
        response_data = await get_answer(request.question, request.history, request.doc_id)
        return response_data
        
    except Exception as e:
        print(f"Endpoint Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate_quiz")
async def api_generate_quiz(request: QuizRequest):
    """
    Generates a strict quiz based on a document.
    """
    return await generate_quiz(
        doc_id=request.doc_id,
        num_questions=request.num_questions,
        difficulty=request.difficulty
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)