import os
import tempfile
import json
import nest_asyncio
from fastapi import UploadFile, HTTPException
from llama_parse import LlamaParse
from supabase import create_client, Client
from sentence_transformers import SentenceTransformer # <--- CHANGED: Using SentenceTransformers

# Apply nest_asyncio to prevent "Event loop is closed" errors with LlamaParse inside FastAPI
nest_asyncio.apply()

# 1. Setup Supabase Client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_KEY")
)

# 2. Initialize Embedding Model
# We use the same 384-dimension model, but loaded via SentenceTransformers to avoid C++ build errors.
print("Loading embedding model (BAAI/bge-small-en-v1.5)...")
embedding_model = SentenceTransformer("BAAI/bge-small-en-v1.5")

# 3. Configure LlamaParse
# result_type="markdown" is used for stability. 
# It converts the PDF to text while keeping headers and lists structure.
parser = LlamaParse(
    api_key=os.getenv("LLAMA_CLOUD_API_KEY"),
    result_type="markdown", 
    verbose=True,
    language="en"
)

def get_embedding(text: str):
    """Generates a 384-dim vector for the given text."""
    try:
        # SentenceTransformers returns a numpy array, so we convert it to a list
        embedding = embedding_model.encode(text)
        return embedding.tolist()
    except Exception as e:
        print(f"⚠️ Embedding Error: {e}")
        return []

async def process_upload(file: UploadFile):
    """
    Handles: Upload -> Temp Save -> LlamaParse -> Embedding -> Supabase Storage
    """
    print(f"🚀 Starting processing for: {file.filename}")
    
    # Create a temp file to store the upload so LlamaParse can read it
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # --- Step A: Register Document in Database ---
        print(f"📂 Registering document '{file.filename}'...")
        doc_response = supabase.table("documents").insert({
            "name": file.filename
        }).execute()
        
        # Robust ID retrieval
        if not doc_response.data:
            raise HTTPException(status_code=500, detail="Failed to insert document record.")
        doc_id = doc_response.data[0]['id']

        # --- Step B: Parse PDF ---
        print("🔍 Parsing PDF (LlamaParse)...")
        # Use async load to prevent blocking the server
        documents = await parser.aload_data(tmp_path)
        
        if not documents:
            raise ValueError("LlamaParse returned no content.")

        chunks_to_insert = []
        
        print(f"📄 Found {len(documents)} pages/sections. Generating embeddings...")
        
        # --- Step C: Process each chunk ---
        for i, doc in enumerate(documents):
            text_content = doc.text
            
            # Skip empty or very short pages to save DB space
            if not text_content or len(text_content.strip()) < 10:
                continue 

            # Extract Page Number (default to index + 1 if missing)
            page_number = doc.metadata.get("page_label", i + 1)
            
            # Generate Embedding (384 dims)
            embedding = get_embedding(text_content)
            
            if not embedding:
                print(f"⚠️ Skipping chunk {i}: Embedding generation failed.")
                continue

            # Prepare the record
            record = {
                "document_id": doc_id,
                "content": text_content,
                "embedding": embedding, 
                "chunk_index": i,
                "metadata": {
                    "page": page_number,
                    "source": file.filename,
                    # Placeholder bbox: [x, y, w, h]
                    # We use dummy zeros for now because Markdown mode doesn't return coordinates.
                    "bbox": [0, 0, 0, 0] 
                }
            }
            chunks_to_insert.append(record)

        # --- Step D: Batch Insert into Supabase ---
        if chunks_to_insert:
            print(f"💾 Saving {len(chunks_to_insert)} chunks to database...")
            supabase.table("document_chunks").insert(chunks_to_insert).execute()
            print("✅ Upload Complete & Indexed!")
            return {
                "status": "success", 
                "doc_id": doc_id, 
                "chunks_count": len(chunks_to_insert),
                "message": "Document processed successfully"
            }
        else:
            print("❌ Error: Valid text was parsed, but no chunks were created.")
            return {"status": "error", "message": "No valid text chunks found."}

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {str(e)}")
        # Optional: Delete the document entry if chunking failed
        # supabase.table("documents").delete().eq("id", doc_id).execute()
        return {"status": "error", "message": str(e)}

    finally:
        # Cleanup temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
            print("🧹 Temp file cleaned up.")