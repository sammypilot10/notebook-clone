from fastapi import FastAPI, UploadFile, File, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

# Import our logic modules
from app import ingestion
from app import chat
from app import quiz

app = FastAPI()

# 1. CORS Configuration - Updated for Vercel Production
origins = [
    "http://localhost:3000",
    "https://notebook-clone-ten.vercel.app",  # Your specific Vercel URL
    "https://notebook-clone.vercel.app",      # Default Vercel project URL
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- HEALTH CHECK (CRITICAL FOR RENDER) ---
@app.get("/")
def health_check():
    return {"status": "active", "message": "Backend is running smoothly!"}

# 2. Chat Endpoint
class ChatRequest(BaseModel):
    question: str
    history: List[Dict[str, Any]] = []
    doc_id: Optional[str] = None

@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    # This handles the AI response logic
    return await chat.get_answer(request.question, request.history, request.doc_id)

# 3. Upload Endpoint
@app.post("/upload")
async def upload_endpoint(file: UploadFile = File(...)):
    return await ingestion.process_document(file)

# 4. Quiz Endpoint
class QuizRequest(BaseModel):
    doc_id: str
    num_questions: int = 5
    difficulty: str = "Hard"

@app.post("/generate_quiz")
async def quiz_endpoint(request: QuizRequest):
    return await quiz.generate_quiz(request.doc_id, request.num_questions, request.difficulty)

# Build Version: 1.0.1 (Adding this comment forces Git to see a change)
