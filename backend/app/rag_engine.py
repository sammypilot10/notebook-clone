import os
from typing import List, Dict, Any
from supabase import create_client, Client
from fastembed import TextEmbedding
from openai import OpenAI

# 1. Setup Clients
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# Use OpenAI for the "Reasoning" part (or switch to Anthropic/Google)
llm_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize the SAME embedding model used in ingestion (Critical!)
print("Loading embedding model for retrieval...")
embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

SYSTEM_PROMPT = """
You are a precision-focused research assistant. 
Your goal is to answer the user's question explicitly based on the provided context.

RULES:
1.  **Strict Grounding:** You must answer ONLY using the provided context chunks. Do not use outside knowledge.
2.  **Citations:** Every claim you make must be immediately followed by a citation in the format [doc_id:page_number]. 
    Example: "The revenue grew by 20% [doc_123:4]."
3.  **Refusal:** If the context does not contain the answer, strictly state: "I cannot answer this based on the available sources." Do not guess.
4.  **Tone:** Be professional, objective, and concise.
"""

def get_query_embedding(text: str) -> List[float]:
    """Generates the 384-dim vector for the query."""
    try:
        # Generate embedding
        embedding_gen = embedding_model.embed([text])
        return list(embedding_gen)[0].tolist()
    except Exception as e:
        print(f"Embedding Error: {e}")
        return []

def retrieve_context(query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """
    Searches Supabase for the most relevant chunks.
    """
    query_vector = get_query_embedding(query)
    
    if not query_vector:
        return []

    # Call the Postgres function 'match_documents' we defined earlier
    response = supabase.rpc("match_documents", {
        "query_embedding": query_vector,
        "match_threshold": 0.5, # adjust strictly (0.0 to 1.0)
        "match_count": top_k
    }).execute()

    return response.data

def format_context(chunks: List[Dict[str, Any]]) -> str:
    """
    Formats the retrieved chunks into a string for the LLM.
    """
    formatted_text = ""
    for chunk in chunks:
        # Extract metadata
        meta = chunk.get("metadata", {})
        source_name = meta.get("source", "Unknown Document")
        page_num = meta.get("page", "?")
        doc_id = chunk.get("document_id") # We need this for the citation mapping
        
        # We append a specific ID format for the LLM to reference
        # ID Format: [doc_id:page]
        chunk_header = f"--- Source: {source_name} (Page {page_num}) [ID: {doc_id}:{page_num}] ---"
        formatted_text += f"{chunk_header}\n{chunk['content']}\n\n"
        
    return formatted_text

async def chat_with_notebook(query: str):
    """
    The main RAG pipeline: Query -> Retrieve -> Augment -> Generate
    """
    # 1. Retrieve
    print(f"Searching for: {query}")
    relevant_chunks = retrieve_context(query)
    
    if not relevant_chunks:
        return "I could not find any relevant information in your documents to answer that question."

    # 2. Augment (Build Context)
    context_str = format_context(relevant_chunks)
    
    # 3. Generate (Call LLM)
    # We use streaming to make it feel fast
    response = llm_client.chat.completions.create(
        model="gpt-4o", # or "gpt-3.5-turbo" to save costs
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Context:\n{context_str}\n\nQuestion: {query}"}
        ],
        temperature=0.1, # Low temp = more factual/grounded
        stream=True
    )
    
    return response