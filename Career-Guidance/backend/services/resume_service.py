"""
CareerCompass AI — Resume Service
Handles file validation, text extraction, and AI analysis.
Security: validates type, size, and never executes uploaded files.
"""
import io
import logging
import os
import tempfile
from typing import Dict, Optional, Tuple

from backend.ai.gemini_provider import GeminiProvider
from backend.repositories.analysis_repo import AnalysisRepository
from backend.repositories.profile_repo import ProfileRepository

logger = logging.getLogger(__name__)

ALLOWED_EXTENSIONS = {".pdf", ".docx"}
MAX_TEXT_LENGTH = 5000  # chars — only extract this much for AI


class ResumeService:
    def __init__(
        self,
        profile_repo: ProfileRepository,
        analysis_repo: AnalysisRepository,
        ai_provider: GeminiProvider,
        max_size_bytes: int = 5 * 1024 * 1024,
    ):
        self._profile_repo = profile_repo
        self._analysis_repo = analysis_repo
        self._ai = ai_provider
        self._max_size_bytes = max_size_bytes

    async def analyze_resume(
        self,
        profile_id: str,
        file_content: bytes,
        filename: str,
    ) -> Dict:
        """
        Main entry point:
        1. Validate file type and size
        2. Extract text safely
        3. Call Gemini for feedback
        4. Validate response
        5. Save to DB
        6. Return result
        """
        # Validate
        self._validate_file(filename, len(file_content))

        # Extract text
        resume_text = self._extract_text(file_content, filename)
        if not resume_text or len(resume_text.strip()) < 50:
            raise ValueError("Could not extract meaningful text from the resume. Please upload a text-based PDF or DOCX.")

        # Get profile context
        profile = self._profile_repo.get_by_id(profile_id)
        if not profile:
            raise ValueError("Profile not found")
        
        skills = self._profile_repo.get_skills(profile_id)
        profile["skills"] = skills

        # Call Gemini
        ai_result = await self._ai.analyze_resume(resume_text, profile)

        # Save
        save_data = {
            "guidance_score": ai_result.guidance_score,
            "strengths": ai_result.strengths,
            "missing_skills": ai_result.missing_skills,
            "formatting_feedback": ai_result.formatting_feedback,
            "project_suggestions": ai_result.project_suggestions,
            "skill_alignment": ai_result.skill_alignment,
            "improvement_suggestions": ai_result.improvement_suggestions,
        }
        saved = self._analysis_repo.save_resume_analysis(profile_id, save_data)
        return saved

    def get_latest_resume_analysis(self, profile_id: str) -> Optional[Dict]:
        return self._analysis_repo.get_latest_resume_analysis(profile_id)

    def delete_resume_analysis(self, profile_id: str) -> bool:
        """Deletes only resume analysis records for this profile."""
        return self._analysis_repo.delete_resume_analysis(profile_id)

    def _validate_file(self, filename: str, size_bytes: int) -> None:
        """Validates file type and size. Raises ValueError on invalid input."""
        ext = os.path.splitext(filename.lower())[1]
        if ext not in ALLOWED_EXTENSIONS:
            raise ValueError(
                f"Unsupported file type '{ext}'. Please upload a PDF or DOCX file."
            )
        if size_bytes > self._max_size_bytes:
            max_mb = self._max_size_bytes / (1024 * 1024)
            raise ValueError(f"File too large. Maximum size is {max_mb:.0f}MB.")

    def _extract_text(self, content: bytes, filename: str) -> str:
        """
        Safely extracts text from PDF or DOCX.
        Uses temp files with automatic cleanup.
        Never executes the uploaded file.
        """
        ext = os.path.splitext(filename.lower())[1]
        
        if ext == ".pdf":
            return self._extract_pdf(content)
        elif ext == ".docx":
            return self._extract_docx(content)
        
        return ""

    def _extract_pdf(self, content: bytes) -> str:
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(content))
            text_parts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
            return "\n".join(text_parts)[:MAX_TEXT_LENGTH]
        except Exception as e:
            logger.error(f"PDF extraction error: {e}")
            raise ValueError("Failed to read PDF. Please ensure the file is not password-protected.")

    def _extract_docx(self, content: bytes) -> str:
        try:
            from docx import Document
            doc = Document(io.BytesIO(content))
            text_parts = [para.text for para in doc.paragraphs if para.text.strip()]
            return "\n".join(text_parts)[:MAX_TEXT_LENGTH]
        except Exception as e:
            logger.error(f"DOCX extraction error: {e}")
            raise ValueError("Failed to read DOCX file. Please ensure the file is valid.")
