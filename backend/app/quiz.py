import os
import json
import re
from groq import Groq
from supabase import create_client, Client

# Initialize Clients
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
supabase: Client = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))

def clean_json_string(json_string):
    """
    Cleans the string to ensure it is valid JSON.
    Removes Markdown code blocks (```json ... ```).
    """
    json_string = re.sub(r'^```json\s*', '', json_string)
    json_string = re.sub(r'^```\s*', '', json_string)
    json_string = re.sub(r'\s*```$', '', json_string)
    return json_string.strip()

async def generate_quiz(doc_id: str, num_questions: int, difficulty: str = "Hard"):
    print(f"🎓 Generating {num_questions} {difficulty} questions for Doc: {doc_id}")

    try:
        # 1. Fetch chunks
        response = supabase.table("document_chunks") \
            .select("content") \
            .eq("document_id", doc_id) \
            .limit(15) \
            .execute()
        
        if not response.data:
            return {"error": "Document not found or empty."}

        context_text = "\n".join([chunk['content'] for chunk in response.data])[:15000]

        # 2. UPDATED Prompt with 'explanation' field
        system_prompt = f"""
        You are a strict university professor setting a {difficulty} exam.
        
        TASK:
        Generate {num_questions} multiple-choice questions based strictly on the provided text.
        
        CRITICAL OUTPUT RULES:
        1. Output ONLY valid JSON.
        2. Structure:
        {{
            "questions": [
                {{
                    "question": "Question text?",
                    "options": ["A) Option 1", "B) Option 2", "C) Option 3", "D) Option 4"],
                    "answer": "The exact text of the correct option",
                    "explanation": "A short clear reason why this answer is correct based on the text."
                }}
            ]
        }}
        """

        # 3. Call Groq
        completion = groq_client.chat.completions.create(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"CONTEXT DATA:\n{context_text}"}
            ],
            model="llama-3.3-70b-versatile",
            temperature=0.2, 
            response_format={"type": "json_object"} 
        )
        
        raw_content = completion.choices[0].message.content
        cleaned_content = clean_json_string(raw_content)
        quiz_data = json.loads(cleaned_content)
        
        time_limit_seconds = num_questions * 45 
        
        return {
            "questions": quiz_data.get('questions', []),
            "timer_seconds": time_limit_seconds,
            "difficulty": difficulty
        }

    except Exception as e:
        print(f"❌ Error: {e}")
        return {"error": "Failed to generate quiz."}