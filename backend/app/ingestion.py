import os
import uuid
from fastapi import UploadFile, HTTPException
from supabase import create_client, Client
from llama_parse import LlamaParse
from sentence_transformers import SentenceTransformer

# 1. Setup Clients
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"), 
    os.getenv("SUPABASE_KEY")
)

# --- LAZY LOADING FIX ---
# Do NOT load the model globally.
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        print("⏳ Loading embedding model for ingestion... (This happens once)")
        _embedding_model = SentenceTransformer("BAAI/bge-small-en-v1.5")
    return _embedding_model

async def process_document(file: UploadFile):
    # 2. Upload File to Supabase Storage
    try:
        file_content = await file.read()
        file_path = f"uploads/{uuid.uuid4()}_{file.filename}"
        
        supabase.storage.from_("documents").upload(file_path, file_content)
        
        # Get Public URL
        public_url = supabase.storage.from_("documents").get_public_url(file_path)
    except Exception as e:
        print(f"Storage Upload Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload file to storage")

    # 3. Parse PDF using LlamaParse
    try:
        parser = LlamaParse(
            api_key=os.getenv("LLAMA_CLOUD_API_KEY"),
            result_type="markdown"
        )
        # We need to save temp file for LlamaParse
        temp_filename = f"temp_{file.filename}"
        with open(temp_filename, "wb") as f:
            f.write(file_content)
            
        documents = parser.load_data(temp_filename)
        
        # Cleanup temp file
        if os.path.exists(temp_filename):
            os.remove(temp_filename)
            
        full_text = "\n".join([doc.text for doc in documents])
        
    except Exception as e:
        print(f"LlamaParse Error: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse PDF")

    # 4. Chunking & Embedding (LAZY LOADED)
    try:
        # Simple chunking by paragraphs or size
        chunk_size = 1000
        chunks = [full_text[i:i+chunk_size] for i in range(0, len(full_text), chunk_size)]
        
        model = get_embedding_model() # <--- Load model here, not at top
        
        vectors = []
        doc_id = str(uuid.uuid4())
        
        for i, chunk in enumerate(chunks):
            embedding = model.encode(chunk).tolist()
            vectors.append({
                "document_id": doc_id,
                "content": chunk,
                "embedding": embedding,
                "metadata": {"source": file.filename, "chunk_index": i}
            })
            
        # 5. Store in Supabase Vector Table
        if vectors:
            supabase.table("document_chunks").insert(vectors).execute()
            
        return {"status": "success", "doc_id": doc_id, "chunks": len(vectors)}

    except Exception as e:
        print(f"Embedding/Database Error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process vectors: {str(e)}")