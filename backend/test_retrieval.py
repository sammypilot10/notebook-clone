import os
import asyncio
from dotenv import load_dotenv
from supabase import create_client
from fastembed import TextEmbedding

load_dotenv()

# Setup Clients
supabase = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))
embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")

async def test_search(query: str):
    print(f"Querying: '{query}'...")
    
# We add .tolist() to convert the NumPy array to a standard list
    query_vector = list(embedding_model.embed([query]))[0].tolist()   
    
    # 2. Search Supabase using the RPC function we made
    response = supabase.rpc("match_documents", {
        "query_embedding": query_vector,
        "match_threshold": 0.5, # Lower threshold = looser matches
        "match_count": 3
    }).execute()
    
    # 3. Print Results
    if response.data:
        print("\n✅ Found matches!")
        for match in response.data:
            print(f"--- Score: {match['similarity']:.4f} ---")
            print(f"Content: {match['content'][:100]}...") # Show first 100 chars
            print(f"Page: {match['metadata']['page']}")
    else:
        print("❌ No matches found. Did you upload a PDF yet?")

if __name__ == "__main__":
    # Change this question to something relevant to your uploaded PDF
    asyncio.run(test_search("What is this document about?"))