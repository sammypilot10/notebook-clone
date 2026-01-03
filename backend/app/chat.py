import os
from typing import Optional, List, Dict, Any
from groq import Groq
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer

# 1. Setup Clients
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"), 
    os.getenv("SUPABASE_KEY")
)

# --- LAZY LOADING FIX ---
# We do NOT load the model globally anymore.
# We hold it in a variable and load it only when needed.
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        print("⏳ Loading embedding model for the first time... (This might take a moment)")
        # This only runs when the first user asks a question
        _embedding_model = SentenceTransformer("BAAI/bge-small-en-v1.5")
        print("✅ Model loaded successfully!")
    return _embedding_model

async def get_answer(question: str, history: List[Dict[str, Any]], doc_id: Optional[str] = None):
    print(f"User asked: '{question}' (Doc ID: {doc_id})")

    # --- INTELLIGENT SEARCH QUERY ---
    search_query = question
    
    if history and len(question.split()) < 10:
        last_bot_msg = next((m['content'] for m in reversed(history) if m['role'] == 'bot'), None)
        if last_bot_msg:
            search_query = f"{last_bot_msg} {question}"
            print(f"🔄 Refined Search Query: '{search_query}'")

    # 1. Vectorize the Query (Using Lazy Loader)
    # We call get_embedding_model() here instead of using a global variable
    model = get_embedding_model()
    query_vector = model.encode(search_query).tolist()

    # 2. Retrieve Context from Supabase
    params = {
        "query_embedding": query_vector,
        "match_threshold": 0.5,
        "match_count": 5,
        "filter_doc_id": doc_id 
    }
    
    try:
        search_result = supabase.rpc("match_documents", params).execute()
    except Exception as e:
        print(f"Supabase Search Error: {e}")
        return {"answer": "I encountered an error searching your documents.", "sources": []}

    # 3. Format Context
    context_text = ""
    sources_data = []
    
    if search_result.data:
        sources_data = search_result.data
        for i, match in enumerate(search_result.data):
            meta = match.get('metadata', {})
            page_num = meta.get('page', 'Unknown')
            source_name = meta.get('source', 'Document')
            context_text += f"\n[Source {i+1}] {source_name} (Page {page_num}):\n{match['content']}\n"
    else:
        context_text = "No direct match found in document. Please rely on conversation history."

    # 4. Construct System Prompt
    system_prompt = """
    You are an intelligent tutor and exam expert. 
    You have access to a specific document uploaded by the user.

    MODES OF OPERATION:
    
    1. **Q&A MODE**: Answer strictly based on the provided CONTEXT.
       - Cite your sources using [Source 1], [Source 2], etc.
    
    2. **QUIZ/CBT MODE**: If the user asks for "questions", "quiz", "test", or "CBT":
       - Generate ONE multiple-choice question at a time.
       - Provide 4 options (A, B, C, D).
       - Wait for the user to answer.
       - DO NOT give the answer immediately.
       - Once the user answers, correct them if wrong, explain why, and then ask: "Ready for the next question?"
    
    GENERAL RULES:
    - If the context is empty, look at the CHAT HISTORY.
    """

    # 5. Build Payload
    messages_payload = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": f"### BACKGROUND CONTEXT FROM DOCUMENTS:\n{context_text}"}
    ]

    for msg in history[-6:]: 
        role = "assistant" if msg.get('role') == "bot" else "user"
        content = msg.get('content', '')
        if content:
            messages_payload.append({"role": role, "content": content})

    messages_payload.append({"role": "user", "content": question})

    # 6. Call Groq Inference
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=messages_payload,
            model="llama-3.3-70b-versatile",
            temperature=0.3, 
            max_tokens=1024
        )
        
        answer = chat_completion.choices[0].message.content
        return { "answer": answer, "sources": sources_data }
    
    except Exception as e:
        print(f"Groq API Error: {e}")
        return { "answer": "I'm having trouble thinking right now (LLM Error). Please try again.", "sources": [] }