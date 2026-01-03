import os
from typing import Optional, List, Dict, Any
from groq import Groq
from supabase import create_client, Client
from fastembed import TextEmbedding

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

def get_answer(question: str, history: List[Dict[str, Any]], doc_id: Optional[str] = None):
    print(f"User asked: '{question}' (Doc ID: {doc_id})")

    # 1. Vectorize the Question
    query_vector = list(embedding_model.embed([question]))[0].tolist()

    # 2. Retrieve Context
    search_result = supabase.rpc("match_documents", {
        "query_embedding": query_vector,
        "match_threshold": 0.5,
        "match_count": 5,
        "filter_doc_id": doc_id
    }).execute()

    # 3. Format Context
    context_text = ""
    if search_result.data:
        for i, match in enumerate(search_result.data):
            page_num = match['metadata'].get('page', 'Unknown')
            context_text += f"\n[Source {i+1}] (Page {page_num}):\n{match['content']}\n"
    else:
        context_text = "No specific text found."

    # 4. Construct System Prompt (The Brain)
    system_prompt = """
    You are an intelligent tutor and exam expert. 
    You have access to a specific document uploaded by the user.

    MODES OF OPERATION:
    
    1. **Q&A MODE**: If the user asks a general question, answer strictly based on the context.
    
    2. **QUIZ/CBT MODE**: If the user asks for "questions", "quiz", "test", or "CBT":
       - Generate ONE multiple-choice question at a time based on the document.
       - Provide 4 options (A, B, C, D).
       - Wait for the user to answer.
       - DO NOT give the answer immediately.
       - Once the user answers, correct them if wrong, explain why, and then ask: "Ready for the next question?"
    
    GENERAL RULES:
    - Keep answers concise.
    - If the user says "next" or "continue", look at the chat history to see what was happening and continue that flow.
    """

    # 5. Build the Message History for Groq
    # We start with the System Prompt
    messages_payload = [{"role": "system", "content": system_prompt}]
    
    # We add the "Context" as a system message so the AI knows the facts
    messages_payload.append({
        "role": "system", 
        "content": f"BACKGROUND INFORMATION FROM DOCUMENT:\n{context_text}"
    })

    # We append the last 4 messages from the chat history so the AI has 'memory'
    # We map 'bot' to 'assistant' because Groq uses 'assistant'
    for msg in history[-4:]: 
        role = "assistant" if msg['role'] == "bot" else "user"
        messages_payload.append({"role": role, "content": msg['content']})

    # Finally, add the user's current question
    messages_payload.append({"role": "user", "content": question})

    # 6. Call Groq
    try:
        chat_completion = groq_client.chat.completions.create(
            messages=messages_payload,
            model="llama-3.3-70b-versatile",
            temperature=0.3, # Slightly higher creativity for question generation
        )
        answer = chat_completion.choices[0].message.content
        return { "answer": answer, "sources": search_result.data }
    
    except Exception as e:
        print(f"Error: {e}")
        return { "answer": "Error generating response.", "sources": [] }