from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import urllib.request
import json
import re
import random
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

# Startup check to verify backend loading (without logging raw secret)
raw_key = os.getenv("GROQ_API_KEY", "")
groq_key = raw_key.strip().strip('"').strip("'")
if groq_key:
    print(f"✅ [SUCCESS] Loaded GROQ_API_KEY: {groq_key[:7]}...{groq_key[-4:]}", flush=True)
else:
    print("❌ [ERROR] GROQ_API_KEY is NOT found or None!", flush=True)

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
def generate_summary(req: SummaryRequest):
    user_val = req.user_input.strip() if req.user_input else ""
    if not user_val or is_pure_greeting_or_chatter(user_val):
        return {
            "status": "success",
            "summary": "Please enter your target role, skills, or professional experience to generate a resume summary."
        }

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
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

    try:
        req_data = json.dumps(payload).encode("utf-8")
        req_obj = urllib.request.Request(
            endpoint,
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "User-Agent": "Mozilla/5.0"
            },
            method="POST"
        )
        
        with urllib.request.urlopen(req_obj) as response:
            res_json = json.loads(response.read().decode("utf-8"))
            raw_text = res_json["choices"][0]["message"]["content"]
            cleaned = re.sub(r'^(Here\'s|Here is|Output|Summary)[^:]*:\s*', '', raw_text, flags=re.IGNORECASE).strip('"\' \n')
            return {"status": "success", "summary": cleaned}
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Groq API call failed: {str(e)}"
        )

@app.post("/api/generate-section")
def generate_section(req: SectionRequest):
    user_val = req.user_input.strip() if req.user_input else ""
    section_type = req.section_type.lower().strip()
    job_title = req.job_title.strip() if req.job_title else "Professional"

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
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
        system_rules = (
            "You are an expert Tech & Industry Talent Recruiter.\n"
            "Suggest exactly 7-10 high-impact technical or creative skills for a professional resume "
            f"appropriate for the job title or context: '{user_val}'.\n"
            "STRICT RULES:\n"
            "1. Suggest high-impact skills based on the input.\n"
            "2. Return ONLY a clean, comma-separated list of skills, with no numbering, introduction, quotes, explanations, or additional text.\n"
            "Example: Project Management, Risk Assessment, Budgeting"
        )
        prompt_content = f"Generate skills for job role: '{user_val}'"
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

    try:
        req_data = json.dumps(payload).encode("utf-8")
        req_obj = urllib.request.Request(
            endpoint,
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "User-Agent": "Mozilla/5.0"
            },
            method="POST"
        )
        
        with urllib.request.urlopen(req_obj) as response:
            res_json = json.loads(response.read().decode("utf-8"))
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
            
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Groq API call failed: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
