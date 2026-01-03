import os
from typing import Optional, List, Dict, Any
from groq import Groq
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer

# 1. Setup Clients
# Ensure GROQ_API_KEY is set in your .env file
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

supabase: Client = create_client(
    os.getenv("SUPABASE_URL"), 
    os.getenv("SUPABASE_KEY")
)

# Initialize Embedding Model (Must match Ingestion dimensions: 384)
print("Loading embedding model for chat...")
embedding_model = SentenceTransformer("BAAI/bge-small-en-v1.5")

async def get_answer(question: str, history: List[Dict[str, Any]], doc_id: Optional[str] = None):
    print(f"User asked: '{question}' (Doc ID: {doc_id})")

    # --- INTELLIGENT SEARCH QUERY (THE FIX) ---
    # If the user says "B" or "Next", standard search finds nothing.
    # We fix this by combining the LAST AI MESSAGE with the user's new question.
    search_query = question
    
    # Check if we have history and the question is short (less than 10 words)
    if history and len(question.split()) < 10:
        # Find the last message from the bot
        last_bot_msg = next((m['content'] for m in reversed(history) if m['role'] == 'bot'), None)
        if last_bot_msg:
            # Create a combined query: "What is Classical Theory? B"
            # This helps the vector search find the original topic again.
            search_query = f"{last_bot_msg} {question}"
            print(f"🔄 Refined Search Query: '{search_query}'")

    # 1. Vectorize the Query
    # SentenceTransformers returns a numpy array, convert to list
    query_vector = embedding_model.encode(search_query).tolist()

    # 2. Retrieve Context from Supabase
    params = {
        "query_embedding": query_vector,
        "match_threshold": 0.5, # Lower threshold = more results, Higher = strictly relevant
        "match_count": 5,
        "filter_doc_id": doc_id # Optional: restrict search to one document
    }
    
    try:
        search_result = supabase.rpc("match_documents", params).execute()
    except Exception as e:
        print(f"Supabase Search Error: {e}")
        return {"answer": "I encountered an error searching your documents.", "sources": []}

    # 3. Format Context for the LLM
    context_text = ""
    sources_data = []
    
    if search_result.data:
        sources_data = search_result.data
        for i, match in enumerate(search_result.data):
            # Safe get for metadata fields
            meta = match.get('metadata', {})
            page_num = meta.get('page', 'Unknown')
            source_name = meta.get('source', 'Document')
            
            # Append to context string
            context_text += f"\n[Source {i+1}] {source_name} (Page {page_num}):\n{match['content']}\n"
    else:
        # Fallback: If search failed but we have history, we rely on LLM memory
        context_text = "No direct match found in document. Please rely on conversation history."

    # 4. Construct System Prompt (The Brain)
    system_prompt = """
    You are an intelligent tutor and exam expert. 
    You have access to a specific document uploaded by the user.

    MODES OF OPERATION:
    
    1. **Q&A MODE**: If the user asks a general question, answer strictly based on the provided CONTEXT.
       - Cite your sources using [Source 1], [Source 2], etc.
    
    2. **QUIZ/CBT MODE**: If the user asks for "questions", "quiz", "test", or "CBT":
       - Generate ONE multiple-choice question at a time based on the document.
       - Provide 4 options (A, B, C, D).
       - Wait for the user to answer.
       - DO NOT give the answer immediately.
       - Once the user answers, correct them if wrong, explain why, and then ask: "Ready for the next question?"
    
    GENERAL RULES:
    - Keep answers concise and helpful.
    - If the context is empty, look at the CHAT HISTORY to see if the user is answering a previous question.
    - If the user says "next" or "continue", continue the previous topic.
    """

    # 5. Build the Message Payload for Groq
    messages_payload = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": f"### BACKGROUND CONTEXT FROM DOCUMENTS:\n{context_text}"}
    ]

    # Append History (Last 6 messages for better context memory)
    for msg in history[-6:]: 
        role = "assistant" if msg.get('role') == "bot" else "user"
        content = msg.get('content', '')
        if content:
            messages_payload.append({"role": role, "content": content})

    # Append Current Question
    messages_payload.append({"role": "user", "content": question})

    # 6. Call Groq Inference
    try:
        # Note: Groq's python client is synchronous by default. 
        # In a high-load production app, consider using AsyncGroq.
        chat_completion = groq_client.chat.completions.create(
            messages=messages_payload,
            model="llama-3.3-70b-versatile", # High performance, low latency
            temperature=0.3, 
            max_tokens=1024
        )
        
        answer = chat_completion.choices[0].message.content
        
        # Return structured response
        return { 
            "answer": answer, 
            "sources": sources_data 
        }
    
    except Exception as e:
        print(f"Groq API Error: {e}")
        return { 
            "answer": "I'm having trouble thinking right now (LLM Error). Please try again.", 
            "sources": [] 
        }