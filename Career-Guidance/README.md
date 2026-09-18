# CareerCompass AI — AI-Powered Career Guidance Platform for Diploma Students

**CareerCompass AI** is a production-grade, full-stack career advisory and intelligence platform tailored specifically for Polytechnic and Diploma engineering students across India (CSE, IT, ECE, EEE, Mechanical, Civil, and Automobile).

---

## Architecture Overview

```text
Student Profile + Academic Standing + Technical Skills + Interests + Goals + Assessment Responses + Resume Intelligence
                                       ↓
                        Student AI Context Builder
                                       ↓
           Deterministic SHA-256 Fingerprint (Smart Cache Invalidation)
                                       ↓
       Google Gemini 1.5 Flash (google-genai SDK, Single Structured JSON Call)
                                       ↓
              Strict Pydantic Schema Validation (backend/ai/schemas.py)
                                       ↓
        Dynamic Career Intelligence (5-Dimension Scores, Skill Gaps, Roadmap)
                                       ↓
                   Context-Aware AI Chat & Interactive Results UI
                                       ↓
             Supabase PostgreSQL (Persistent History, RLS Protected)
```

### Genuine AI Career Intelligence Layer

CareerCompass AI uses **Google Gemini** (`google-genai` SDK) as an authentic, evidence-driven career intelligence layer:

1. **Multi-Signal Context Synthesis**: The `ai_context_builder` gathers the student's complete profile, academic branch/semester/CGPA, explicit technical proficiencies, interest areas, career goals, 10-signal assessment choices, and parsed resume intelligence into a cohesive prompt.
2. **Dynamic Career Discovery**: Gemini dynamically identifies matching industry careers (e.g. Cloud DevOps, Embedded Developer, QA Automation Tester, CAD Specialist, Cybersecurity Analyst, Data Analyst) based on evidence. Recommendations are not constrained to static database careers.
3. **5-Dimension Compatibility Radar**: AI computes 5 distinct dimensions (Branch Fit, Skill Match, Interest Alignment, Goal Alignment, Academic Standing) feeding directly into an interactive Chart.js radar chart.
4. **Smart Fingerprint Caching**: Cache keys use a SHA-256 hash of normalized student inputs. When any skill, assessment answer, or resume changes, a fresh Gemini analysis is triggered. Identical inputs consume 0 quota.
5. **Context-Aware Chat Counselor**: Chat sessions automatically receive the student's latest career recommendations, skill gaps, assessment signals, and resume highlights so questions like *"Why did you recommend this career for me?"* receive personalized answers citing actual student evidence.
6. **Transparent Fallback**: If Gemini is temporarily unreachable (quota/timeout), the system provides an honest, clearly labeled non-AI curriculum fallback with full retry capabilities.

---

## Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | Semantic HTML5, Vanilla CSS3 (Custom Design System, Glassmorphism, Print Stylesheet), Vanilla JavaScript (ES6+), Chart.js 4.4 (5-Dimension Compatibility Radar), FontAwesome |
| **Backend** | Python 3.12/3.13, FastAPI 0.115, Uvicorn, Pydantic v2, Pydantic Settings |
| **Database** | Supabase (PostgreSQL 15), Row Level Security (RLS), Triggers, Stored Procedures |
| **Access Mode** | Unauthenticated direct access (no login/signup/JWT required) |
| **Rate Limiting** | SlowAPI 0.1.10 (Remote IP address based) |
| **AI Intelligence** | Google GenAI SDK (`google-genai` >= 1.0.0, `gemini-1.5-flash`), Multi-signal Context Builder, Exponential Backoff, 60s Timeout, Pydantic Validation |
| **File Processing** | PyPDF, python-docx (safe in-memory text extraction, 5MB limit) |
| **Testing** | pytest (54 comprehensive automated tests), pytest-asyncio, FastAPI TestClient |
| **Containerization** | Docker (python:3.12-slim, non-root user `appuser`) |

---

## Folder Structure

```text
CareerCompass AI/
├── backend/
│   ├── ai/
│   │   ├── gemini_provider.py    # Gemini SDK integration, retry, timeout, JSON validator
│   │   ├── prompts.py            # Versioned prompt templates (System, User, Schemas)
│   │   └── schemas.py            # Pydantic schemas for AI responses
│   ├── api/
│   │   ├── admin.py              # Protected admin routes (careers, skills CRUD)
│   │   ├── analysis.py           # Career analysis and roadmap progress endpoints
│   │   ├── auth.py               # Supabase register, login, me endpoints
│   │   ├── careers.py            # Career explorer & detail endpoints
│   │   ├── chat.py               # AI counselor chat endpoints
│   │   ├── profile.py            # Student profile, skills, interests & assessments
│   │   └── resume.py             # Resume parsing & AI analysis endpoints
│   ├── models/
│   │   ├── career.py             # Career and analysis schemas
│   │   ├── common.py             # API response envelopes
│   │   └── profile.py            # Profile, branch enum, proficiency schemas
│   ├── repositories/
│   │   ├── analysis_repo.py      # Supabase career analyses & roadmap persistence
│   │   ├── career_repo.py        # Careers, skills, projects queries
│   │   ├── chat_repo.py          # Chat sessions and messages persistence
│   │   └── profile_repo.py       # Profiles, student skills & answers persistence
│   ├── services/
│   │   ├── analysis_service.py   # Analysis orchestration & cache management
│   │   ├── chat_service.py       # Chat session context building & Gemini chat
│   │   ├── matching_engine.py    # Deterministic scoring algorithm
│   │   └── resume_service.py     # Safe file validation & text parsing
│   ├── config.py                 # Pydantic BaseSettings (.env loading & defaults)
│   ├── deps.py                   # FastAPI dependency injection (Auth & Admin guards)
│   └── main.py                   # App entrypoint, CORS, routers & exception handlers
├── database/
│   ├── schema.sql                # PostgreSQL tables, foreign keys & indexes
│   ├── functions.sql             # Version bump, timestamp & security triggers
│   ├── rls_policies.sql          # Row Level Security policies for all tables
│   └── seed_data.sql             # 17+ careers, 40+ skills, projects & assessments
├── frontend/
│   ├── css/
│   │   └── styles.css            # Complete design system & responsive rules
│   ├── js/
│   │   └── api.js                # Centralized API client & auth handlers
│   ├── admin.html                # Admin management console
│   ├── assessment.html           # Interactive career aptitude quiz
│   ├── auth.html                 # Login and registration portal
│   ├── chat.html                 # AI Career Counselor chat interface
│   ├── dashboard.html            # Student overview, roadmap progress, quick stats
│   ├── explorer.html             # Filterable and searchable career pathways
│   ├── index.html                # Platform landing page
│   ├── profile.html              # Academic profile, skills & interest manager
│   ├── results.html              # AI analysis results, match scores, skill gaps
│   ├── resume.html               # Resume uploader & readiness score feedback
│   └── roadmap.html              # Step-by-step milestone timeline with progress tracking
├── tests/
│   ├── test_ai_schemas.py        # AI JSON schema & Pydantic validation tests
│   ├── test_api_endpoints.py     # Health check & route integration tests
│   ├── test_auth_and_security.py # Security boundaries, password & admin tests
│   └── test_matching_engine.py   # Deterministic algorithm & edge case tests
├── .dockerignore
├── .env.example
├── .gitignore
├── Dockerfile
└── requirements.txt
```

---

## Setup & Installation

### 1. Prerequisites

- Python 3.12 or 3.13
- A [Supabase](https://supabase.com/) project
- A [Google AI Studio](https://aistudio.google.com/) Gemini API Key

### 2. Environment Configuration

Copy `.env.example` to `.env` in the root folder:

```bash
cp .env.example .env
```

Fill in your actual credentials:

```env
SUPABASE_URL=https://your-project-ref.supabase.co
SUPABASE_ANON_KEY=your-supabase-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-supabase-service-role-key

GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-1.5-flash

APP_ENV=development
APP_SECRET_KEY=generate-a-secure-random-secret
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:5500,http://localhost:5500,http://localhost:8000
```

### 3. Database Initialization

In your Supabase project dashboard, navigate to the **SQL Editor** and execute the SQL scripts in this exact order:

1. `database/schema.sql` (Creates core tables, foreign keys, constraints, and indexes)
2. `database/functions.sql` (Creates stored functions and privilege protection triggers)
3. `database/rls_policies.sql` (Enables and configures Row Level Security)
4. `database/seed_data.sql` (Populates 17 diploma engineering careers, 40+ skills, projects, and assessment questions)

### 4. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run the Backend Locally

```bash
python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
```

The API will be live at `http://localhost:8000`. You can test the health endpoint:
```bash
curl http://localhost:8000/api/health
```
Interactive OpenAPI documentation is available at `http://localhost:8000/docs`.

### 6. Run the Frontend

You can serve the `frontend/` directory using Python's built-in HTTP server or VS Code Live Server:

```bash
cd frontend
python -m http.server 5500
```

Open your browser at `http://localhost:5500/index.html`.

---

## Running Automated Tests

Run the complete test suite with verbose output:

```bash
pytest tests/ -v
```

Tests cover (42 total passing tests):
- Branch compatibility, proficiency weighting, and ranking logic in `matching_engine.py`
- Pydantic schema validation for AI JSON responses and markdown fence extraction
- Bearer authentication, unhashable settings fix, and `require_admin` authorization guards
- Endpoint status codes and error responses via FastAPI `TestClient`
- SlowAPI rate limiting enforcement (10/min auth, per-hour AI limits, clean 429 JSON)
- Modern `google-genai` SDK provider initialization, exponential backoff, timeout, and chat
- Frontend XSS sanitization and HTML escaping against injection vectors
- Expanded assessment seed validation (10 questions across all diploma disciplines)

---

## Docker Deployment

Build the container image:

```bash
docker build -t careercompass-ai .
```

Run the container:

```bash
docker run -d -p 8000:8000 --env-file .env --name careercompass careercompass-ai
```

The Dockerfile implements security best practices:
- Uses `python:3.12-slim` base image
- Copies only production files
- Drops root privileges and runs as non-root `appuser` (UID 1000)
- Exposes port 8000 with 2 Uvicorn workers

---

## API Reference Summary

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | System health check |
| `GET` | `/api/profile` | Get student profile, skills, and interests |
| `POST` | `/api/profile` | Create student profile |
| `PUT` | `/api/profile` | Update profile (bumps profile version) |
| `GET` | `/api/profile/skills/all` | List all reference skills |
| `GET` | `/api/profile/interests/all` | List all reference interests |
| `GET` | `/api/profile/assessment/questions` | Get assessment questions |
| `POST` | `/api/profile/assessment/submit` | Submit career assessment answers |
| `GET` | `/api/careers` | Search and filter careers by branch |
| `GET` | `/api/careers/{id}` | Get career details with skills & projects |
| `POST` | `/api/analysis/career` | Trigger AI career analysis (cached) |
| `GET` | `/api/analysis/career` | Get latest career analysis |
| `GET` | `/api/analysis/roadmap` | Get roadmap and progress tracking |
| `POST` | `/api/analysis/roadmap/progress` | Update roadmap milestone completion |
| `POST` | `/api/chat/send` | Send message to AI counselor |
| `GET` | `/api/chat/sessions` | List chat sessions |
| `GET` | `/api/chat/history/{id}` | Get conversation history for session |
| `POST` | `/api/resume/analyze` | Upload and analyze PDF/DOCX resume |
| `GET` | `/api/resume/latest` | Get most recent resume analysis |
| `POST` | `/api/admin/careers` | Create career in catalog |
| `PUT` | `/api/admin/careers/{id}` | Update career details |
| `DELETE` | `/api/admin/careers/{id}` | Delete career from catalog |
| `POST` | `/api/admin/skills` | Create skill in catalog |
