from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import urllib.request
import json
import re
import random
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from the exact directory of main.py
env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=env_path)

# Startup check to verify backend loading (without logging raw secret)
api_key_loaded = bool(os.getenv("GROQ_API_KEY"))
print(f"GROQ_API_KEY Loaded: {api_key_loaded}", flush=True)

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
    user_input: str = None
    default_text: str = None
    section_type: str = "summary"

class SkillsRequest(BaseModel):
    role: str = None
    name: str = None
    summary: str = None

def is_pure_greeting_or_chatter(text: str) -> bool:
    cleaned = re.sub(r'[^a-zA-Z0-9\s]', '', text.lower()).strip()
    if not cleaned:
        return True
        
    # List of common chatter, greeting, and introduction words
    chatter_words = {
        "hi", "hello", "hey", "how", "are", "you", "doing", "this", "is", "i", "am", "im", "my", "name", 
        "good", "morning", "afternoon", "evening", "there", "what", "whats", "up", "howdy", "althaf", "rufus",
        "stewart", "who", "greetings", "yo", "sup", "hola", "please", "help", "do"
    }
    
    words = cleaned.split()
    # Check if all words are within standard casual/conversational greetings
    if all(w in chatter_words for w in words):
        return True
        
    # Check typical greeting patterns or pure identity statements without professional content
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
    default_val = req.default_text.strip() if req.default_text else ""
    
    # 1. Dynamic Fallback Logic
    prompt_text = user_val or default_val
    
    # 2. INTENT DETECTION & GUARDRAIL:
    if not prompt_text or is_pure_greeting_or_chatter(prompt_text):
        return {
            "status": "success",
            "summary": "Please enter your target role, skills, or professional experience to generate a resume summary."
        }

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    endpoint = "https://api.groq.com/openai/v1/chat/completions"

    seed = random.randint(1, 1000000)

    # 3. Section-Based Prompt Dispatching:
    section_type = req.section_type.lower().strip()
    if section_type == "summary":
        section_instruction = "Generate a crisp 2-3 sentence resume summary centered strictly on the facts in the user prompt."
    elif section_type == "experience_bullets":
        section_instruction = (
            "Convert the user prompt into 3 powerful, high-impact bullet points using strong action verbs (e.g., Developed, Managed, Spearheaded). "
            "Output ONLY raw bullet points starting with standard dashes (e.g., - Developed...)."
        )
    elif section_type == "suggest_bullets":
        section_instruction = (
            "Based on the role/text provided, generate 3 strategic industry-standard achievement bullets. "
            "Output ONLY raw bullet points starting with standard dashes (e.g., - Spearheaded...)."
        )
    else:
        section_instruction = "Generate a professional resume summary."

    # Strict AI System Prompt (Anti-Hallucination rules):
    system_rules = (
        "Strictly use ONLY the facts/skills/role provided in the input prompt. "
        "NEVER invent fictional military service, past companies, or random skills if not mentioned by the user.\n"
        "BANNED WORDS: 'Results-driven', 'proven track record', 'passionate', 'dynamic'.\n"
        "Output ONLY raw text resume content without conversational chatter, greetings, quotes, or bracketed notes."
    )

    messages = [
        {
            "role": "system",
            "content": f"{system_rules}\n\nTask: {section_instruction}"
        },
        {
            "role": "user",
            "content": prompt_text
        }
    ]

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.85,
        "max_tokens": 300,
        "seed": seed
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
            
            # Apply Python re Regex cleaning on the response
            cleaned = re.sub(r'\(.*?\)', '', raw_text)
            cleaned = re.sub(r'^(Here\'s|Here is|Output)[^:]*:\s*', '', cleaned)
            cleaned = cleaned.strip('"\'').strip()
            
            return {"status": "success", "summary": cleaned}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Groq API connection or processing failed: {str(e)}")

@app.post("/api/generate-skills")
def generate_skills(req: SkillsRequest):
    role_val = req.role.strip() if req.role else "Photographer"
    name_val = req.name.strip() if req.name else "Rufus Stewart"
    summary_val = req.summary.strip() if req.summary else ""
    
    prompt_text = (
        f"Based on the job role \"{role_val}\", candidate name \"{name_val}\", and summary \"{summary_val}\", "
        f"suggest exactly 7-10 high-impact technical or creative skills for a professional resume. "
        f"Return ONLY a comma-separated list of skills, with no numbering, introduction, or additional text. "
        f"Example: Studio Lighting, Adobe Lightroom, Color Grading"
    )

    GROQ_API_KEY = os.getenv("GROQ_API_KEY")
    if not GROQ_API_KEY:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured on the backend.")
        
    endpoint = "https://api.groq.com/openai/v1/chat/completions"
    seed = random.randint(1, 1000000)

    system_rules = (
        "You are an elite AI portfolio and resume strategist. Generate professional skills.\n"
        "Strictly use the role and context provided in the input prompt. Return ONLY a comma-separated list of skills. "
        "Do not include numbers, introductions, markdown formatting, quotes, or conversational explanations."
    )

    messages = [
        {
            "role": "system",
            "content": system_rules
        },
        {
            "role": "user",
            "content": prompt_text
        }
    ]

    payload = {
        "model": "llama-3.3-70b-versatile",
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 150,
        "seed": seed
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
            
            # Apply Regex cleaning on the response
            cleaned = re.sub(r'\(.*?\)', '', raw_text)
            cleaned = re.sub(r'^(Here\'s|Here is|Output|Skills|Suggested|Sure)[^:]*:\s*', '', cleaned, flags=re.IGNORECASE)
            cleaned = cleaned.strip('"\'').strip()
            
            return {"status": "success", "skills": cleaned}
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Groq API connection or processing failed: {str(e)}")
