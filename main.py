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

# Centralized AI Model Configuration
DEFAULT_AI_MODEL = "qwen/qwen3.8-27b"

def get_ai_model() -> str:
    raw_model = os.getenv("GROQ_MODEL", DEFAULT_AI_MODEL)
    clean_model = raw_model.strip().strip('"').strip("'")
    return clean_model if clean_model else DEFAULT_AI_MODEL

AI_MODEL = get_ai_model()
GROQ_API_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"

# Startup check to verify backend loading
groq_key = get_groq_api_key()
if groq_key:
    print(f"✅ [SUCCESS] Loaded GROQ_API_KEY: {groq_key[:7]}...{groq_key[-4:]}", flush=True)
else:
    print("❌ [ERROR] GROQ_API_KEY is NOT found or empty in .env!", flush=True)

print(f"🤖 [CONFIG] Active AI Model: {AI_MODEL}", flush=True)

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

# Centralized Groq API call helper
async def call_groq_chat(messages: list, temperature: float = 0.5, max_tokens: int = 400) -> str:
    api_key = get_groq_api_key()
    if not api_key:
        raise HTTPException(status_code=500, detail="GROQ_API_KEY is not configured on backend.")

    current_model = get_ai_model()
    payload = {
        "model": current_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }

    # Configure reasoning_effort="none" for direct content generation when supported (e.g. qwen)
    if "qwen" in current_model.lower():
        payload["reasoning_effort"] = "none"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "Mozilla/5.0"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(GROQ_API_ENDPOINT, json=payload, headers=headers)
            
            # Fallback if a specific model variant rejects reasoning_effort
            if response.status_code == 400 and "reasoning_effort" in response.text and "reasoning_effort" in payload:
                del payload["reasoning_effort"]
                response = await client.post(GROQ_API_ENDPOINT, json=payload, headers=headers)

            if response.status_code != 200:
                err_message = "AI service encountered an unexpected error."
                status_to_return = response.status_code
                try:
                    err_json = response.json().get("error", {})
                    err_code = err_json.get("code", "")
                    raw_msg = str(err_json.get("message", ""))
                    
                    if (
                        err_code in ["model_not_found", "model_decommissioned"]
                        or response.status_code == 404
                        or "does not exist" in raw_msg.lower()
                        or "decommissioned" in raw_msg.lower()
                    ):
                        raise HTTPException(
                            status_code=503,
                            detail="AI model is currently unavailable. Please check the AI configuration."
                        )
                    elif err_code == "invalid_api_key" or response.status_code == 401:
                        raise HTTPException(
                            status_code=401,
                            detail="Invalid Groq API key configured on backend."
                        )
                    elif response.status_code == 429 or err_code == "rate_limit_exceeded":
                        raise HTTPException(
                            status_code=429,
                            detail="AI service rate limit reached. Please try again in a few moments."
                        )
                    elif response.status_code >= 500:
                        raise HTTPException(
                            status_code=502,
                            detail="AI service is temporarily unavailable. Please try again in a few moments."
                        )
                    elif raw_msg:
                        err_message = f"AI service error: {raw_msg}"
                except HTTPException:
                    raise
                except Exception:
                    if response.status_code >= 500:
                        raise HTTPException(
                            status_code=502,
                            detail="AI service is temporarily unavailable. Please try again in a few moments."
                        )

                raise HTTPException(status_code=status_to_return, detail=err_message)

            try:
                res_json = response.json()
            except Exception:
                raise HTTPException(status_code=502, detail="AI service returned an unreadable response format.")

            choices = res_json.get("choices", [])
            if not choices or not isinstance(choices, list):
                raise HTTPException(status_code=502, detail="AI service returned an unexpected response format.")
            
            message_obj = choices[0].get("message", {})
            content = message_obj.get("content") or ""
            
            # Strip any internal thought or reasoning tags
            cleaned_content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL).strip()
            
            if not cleaned_content:
                raise HTTPException(status_code=502, detail="AI service returned an empty response. Please try again.")

            return cleaned_content

    except HTTPException:
        raise
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="AI service request timed out. Please try again.")
    except httpx.RequestError as e:
        raise HTTPException(status_code=503, detail="Unable to connect to the AI service. Please try again.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI service connection failed: {str(e)}")

@app.post("/api/generate-summary")
async def generate_summary(req: SummaryRequest):
    user_val = req.user_input.strip() if req.user_input else ""
    if not user_val or is_pure_greeting_or_chatter(user_val):
        return {
            "status": "success",
            "summary": "Please enter your target role, skills, or professional experience to generate a resume summary."
        }

    system_rules = (
        "You are a World-Class Executive Resume Writer.\n"
        "Transform the raw text notes provided into a compelling, 2-3 sentence executive resume summary.\n"
        "STRICT RULES:\n"
        "1. Do NOT repeat or wrap the input sentence verbatim.\n"
        "2. Output ONLY the polished summary text. No introductions, headers, quotes, or chatter.\n"
        "3. Keep tone objective, metric-oriented, and professional."
    )

    messages = [
        {"role": "system", "content": system_rules},
        {"role": "user", "content": f"Candidate Notes: {user_val}"}
    ]

    raw_text = await call_groq_chat(messages, temperature=0.5, max_tokens=300)
    cleaned = re.sub(r'^(Here\'s|Here is|Output|Summary)[^:]*:\s*', '', raw_text, flags=re.IGNORECASE).strip('"\' \n')
    return {"status": "success", "summary": cleaned}

@app.post("/api/generate-section")
async def generate_section(req: SectionRequest):
    user_val = req.user_input.strip() if req.user_input else ""
    section_type = req.section_type.lower().strip()
    job_title = req.job_title.strip() if req.job_title else "Professional"

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
        max_tokens = 450
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
        max_tokens = 200
        temp = 0.5
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported section_type: {section_type}")

    messages = [
        {"role": "system", "content": system_rules},
        {"role": "user", "content": prompt_content}
    ]

    raw_text = await call_groq_chat(messages, temperature=temp, max_tokens=max_tokens)
    
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


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)