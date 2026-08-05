from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import httpx
import json
import re
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Reconfigure stdout to use UTF-8 to prevent encoding crashes on Windows terminals
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables from the exact directory of main.py
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path, override=True)

# Helper function to get clean API key
def get_groq_api_key() -> str:
    raw_key = os.getenv("GROQ_API_KEY", "")
    return raw_key.strip().strip('"').strip("'")

# Startup check to verify backend loading
groq_key = get_groq_api_key()
if groq_key:
    print(f"✅ [SUCCESS] Loaded GROQ_API_KEY: {groq_key[:7]}...{groq_key[-4:]}", flush=True)
else:
    print("❌ [ERROR] GROQ_API_KEY is NOT found or empty in .env!", flush=True)

app = FastAPI(title="AI Resume Builder Backend")

# Enable CORS for frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class SummaryRequest(BaseModel):
    user_input: str

class SectionRequest(BaseModel):
    user_input: str
    section_type: str
    job_title: str = None

def is_pure_greeting_or_chatter(text: str) -> bool:
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', text.lower()).strip()
    if not cleaned:
        return True
        
    chatter_words = {
        "hi", "hello", "hey", "how", "are", "you", "doing", "this", "is", "i", "am", "im", "my", "name", 
        "good", "morning", "afternoon", "evening", "there", "what", "whats", "up", "howdy", "althaf", "rufus",
        "stewart", "who", "greetings", "yo", "sup", "hola", "please", "help", "do"
    }
    
    words = cleaned.split()
    if all(w in chatter_words for w in words):
        return True
        
    greeting_patterns = [
        r'^(hi|hello|hey|yo)?\s*(this is|i am|im|my name is)\s+[a-zA-Z]{1,15}(?:\s+[a-zA-Z]{1,15}){0,2}$',
        r'^(hi|hello|hey|yo)?\s*(this is|i am|im|my name is)\s+[a-zA-Z]{1,15}(?:\s+[a-zA-Z]{1,15}){0,2}\s+(how are you|how are you doing|whats up|how do you do|how is it going)$',
        r'^(how are you|how do you do|how is it going|how are you doing|whats up|what is up)$'
    ]
    
    for pattern in greeting_patterns:
        if re.match(pattern, cleaned):
            return True
            
    return False

@app.post("/api/generate-summary")
async def generate_summary(req: SummaryRequest):
    user_val = req.user_input.strip() if req.user_input else ""
    if not user_val or is_pure_greeting_or_chatter(user_val):
        return {
            "status": "success",
            "summary": "Please enter your target role, skills, or professional experience to generate a resume summary."
        }

    GROQ_API_KEY = get_groq_api_key()
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured on backend.")

    endpoint = "https://api.groq.com/openai/v1/chat/completions"
    system_rules = (
        "You are a World-Class Executive Resume Writer.\n"
        "Transform the raw text notes provided into a compelling, 2-3 sentence executive resume summary.\n"
        "STRICT RULES:\n"
        "1. Do NOT repeat or wrap the input sentence verbatim.\n"
        "2. Output ONLY the polished summary text. No introductions, headers, quotes, or chatter.\n"
        "3. Keep tone objective, metric-oriented, and professional."
    )

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_rules},
            {"role": "user", "content": f"Candidate Notes: {user_val}"}
        ],
        "temperature": 0.5,
        "max_tokens": 250
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "User-Agent": "Mozilla/5.0"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(endpoint, json=payload, headers=headers)
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Groq API HTTP error: {response.text}"
                )
            
            res_json = response.json()
            raw_text = res_json["choices"][0]["message"]["content"]
            cleaned = re.sub(r'^(Here\'s|Here is|Output|Summary)[^:]*:\s*', '', raw_text, flags=re.IGNORECASE).strip('"\' \n')
            return {"status": "success", "summary": cleaned}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Groq API call failed: {str(e)}")

@app.post("/api/generate-section")
async def generate_section(req: SectionRequest):
    user_val = req.user_input.strip() if req.user_input else ""
    section_type = req.section_type.lower().strip()
    job_title = req.job_title.strip() if req.job_title else "Professional"

    GROQ_API_KEY = get_groq_api_key()
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured on backend.")

    if section_type == "experience_bullets":
        if not user_val or is_pure_greeting_or_chatter(user_val):
            placeholder = "• Please enter raw notes or experience details to generate professional bullets."
            return {
                "status": "success",
                "text": placeholder,
                "summary": placeholder,
                "skills": placeholder
            }

        system_rules = (
            "You are a World-Class Executive Resume Writer.\n"
            f"Transform the raw text notes/experience details provided into 3-4 powerful STAR-method action bullet points (Action Verb + Task + Impact/Metric) for the role '{job_title}'.\n"
            "STRICT RULES:\n"
            "1. Transform raw notes into 3-4 action-oriented bullets.\n"
            "2. Each bullet point MUST begin strictly with '• ' followed by a space.\n"
            "3. Do NOT repeat or wrap the input sentence verbatim.\n"
            "4. Output ONLY the action bullets. No introductions, headers, quotes, explanations, or conversational chatter.\n"
            "5. Keep tone objective, metric-oriented, and professional."
        )
        prompt_content = f"Enhance raw experience details: '{user_val}'"
        max_tokens = 300
        temp = 0.5

    elif section_type == "skills":
        # Prioritize the skills input text box first, then fall back to job title
        if user_val and not is_pure_greeting_or_chatter(user_val):
            context_prompt = f"Existing User Skills / Field: '{user_val}'"
        elif job_title and job_title.lower() != "professional":
            context_prompt = f"Target Job Role: '{job_title}'"
        else:
            context_prompt = "Field: Software Engineering & Development"

        system_rules = (
            "You are an expert Tech & Industry Talent Recruiter.\n"
            "Suggest exactly 7-10 high-impact technical or relevant skills matching the user's field or provided skills.\n"
            "STRICT RULES:\n"
            "1. Analyze the given context carefully. If the context contains programming/software skills (e.g. Java, Python, SQL), generate relevant software developer skills (e.g., Git, Docker, REST APIs, Microservices, System Design).\n"
            "2. Return ONLY a clean, comma-separated list of skills.\n"
            "3. Do NOT include bullet points, numbering, headers, quotes, explanations, or intro/outro chatter."
        )
        prompt_content = f"Generate 8 matching skill chips for: {context_prompt}"
        max_tokens = 150
        temp = 0.5
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported section_type: {section_type}")

    endpoint = "https://api.groq.com/openai/v1/chat/completions"

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {"role": "system", "content": system_rules},
            {"role": "user", "content": prompt_content}
        ],
        "temperature": temp,
        "max_tokens": max_tokens
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "User-Agent": "Mozilla/5.0"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(endpoint, json=payload, headers=headers)
            if response.status_code != 200:
                raise HTTPException(
                    status_code=response.status_code,
                    detail=f"Groq API HTTP error: {response.text}"
                )
            
            res_json = response.json()
            raw_text = res_json["choices"][0]["message"]["content"]
            
            cleaned = re.sub(r'\(.*?\)', '', raw_text)
            cleaned = re.sub(r'^(Here\'s|Here is|Output|Skills|Suggested|Sure|Summary)[^:]*:\s*', '', cleaned, flags=re.IGNORECASE)
            cleaned = cleaned.strip('"\'').strip()
            
            if section_type == "experience_bullets":
                lines = cleaned.split('\n')
                cleaned_lines = []
                for line in lines:
                    line = line.strip()
                    if not line:
                        continue
                    line_cleaned = re.sub(r'^[-•\*#\d\.\s]+', '', line).strip()
                    if line_cleaned:
                        cleaned_lines.append(f"• {line_cleaned}")
                cleaned = "\n".join(cleaned_lines)
            
            return {
                "status": "success",
                "text": cleaned,
                "summary": cleaned,
                "skills": cleaned
            }
            
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Groq API call failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)