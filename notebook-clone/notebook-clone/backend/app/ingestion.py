import nest_asyncio
nest_asyncio.apply()
import os
import tempfile
from fastapi import UploadFile
from llama_parse import LlamaParse
from supabase import create_client, Client
from fastembed import TextEmbedding

# 1. Setup Clients
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"), 
    os.getenv("SUPABASE_KEY")
)

# Initialize the Free Embedding Model
embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

# 2. Configure LlamaParse (Switched to MARKDOWN for stability)
parser = LlamaParse(
    api_key=os.getenv("LLAMA_CLOUD_API_KEY"),
    result_type="markdown", # Changed from 'json' to fix the crash
    verbose=True,
    language="en"
)

def get_embedding(text: str):
    try:
        embedding_gen = embedding_model.embed([text])
        return list(embedding_gen)[0].tolist()
    except Exception as e:
        print(f"Embedding Error: {e}")
        return []

async def process_upload(file: UploadFile):
    print(f"Starting processing for: {file.filename}")
    
    # Create a temp file to store the upload
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # A. Register Document in Database
        print("Registering document...")
        doc_response = supabase.table("documents").insert({
            "name": file.filename
        }).execute()
        doc_id = doc_response.data[0]['id']

        # B. Parse PDF
        print("Parsing PDF (LlamaParse Markdown Mode)...")
        # Markdown mode returns a list of Document objects, one per page/section
        documents = parser.load_data(tmp_path)
        
        chunks_to_insert = []
        
        # C. Loop through pages
        print(f"Found {len(documents)} pages. Generating embeddings...")
        
        for i, doc in enumerate(documents):
            text_content = doc.text
            if not text_content or len(text_content.strip()) < 10:
                continue # Skip empty pages

            # Default to page 1 if metadata is missing
            # LlamaParse usually puts page numbers in extra_info or metadata
            page_number = doc.metadata.get("page_label", i + 1)
            
            embedding = get_embedding(text_content)
            
            chunks_to_insert.append({
                "document_id": doc_id,
                "content": text_content,
                "embedding": embedding,
                "chunk_index": i,
                "metadata": {
                    "page": page_number,
                    # We use a dummy bbox since we are in Markdown mode
                    # This prevents the frontend from crashing
                    "bbox": [0, 0, 0, 0] 
                }
            })

        # D. Save to Supabase
        print(f"Saving {len(chunks_to_insert)} chunks to database...")
        if chunks_to_insert:
            supabase.table("document_chunks").insert(chunks_to_insert).execute()
            print("✅ Upload Complete!")
            return {"status": "success", "doc_id": doc_id, "chunks": len(chunks_to_insert)}
        else:
            print("❌ Error: No text extracted from PDF.")
            return {"status": "error", "message": "No text found in document"}

    except Exception as e:
        print(f"❌ CRITICAL ERROR: {e}")
        return {"status": "error", "message": str(e)}

    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)