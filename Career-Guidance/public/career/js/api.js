/**
 * CareerCompass AI — Centralized API Client with Supabase Auth Integration
 * Uses Supabase JWT Bearer tokens for all protected backend requests.
 */

// Supabase Configuration
const SUPABASE_PROJECT_URL = 'https://fwupeplirgbyujdpzsyk.supabase.co';
const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ3dXBlcGxpcmdieXVqZHB6c3lrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQzNTI0MzMsImV4cCI6MjA5OTkyODQzM30.jpi6dvHuMPA4SAaadido8V51AiwfGbqvoGdshJvlpxY';

function getSupabase() {
    if (window._supabaseInstance) return window._supabaseInstance;
    if (window.supabase && typeof window.supabase.createClient === 'function') {
        window._supabaseInstance = window.supabase.createClient(SUPABASE_PROJECT_URL, SUPABASE_ANON_KEY);
        return window._supabaseInstance;
    }
    if (window.supabase && typeof window.supabase.auth !== 'undefined') {
        return window.supabase;
    }
    return null;
}

// Environment-aware backend URL:
// Local development (localhost, 127.0.0.1, file://) -> local FastAPI server on port 8000
// Production (Netlify / remote domain) -> deployed Render backend
const IS_LOCAL = typeof window !== 'undefined' && (
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1' ||
    window.location.protocol === 'file:'
);

const API_BASE_URL = (typeof window !== 'undefined' && window.__API_BASE_URL__) || (
    IS_LOCAL
        ? 'http://127.0.0.1:8000/api'
        : '/api'
);

class ApiClient {
    constructor() {
        this.baseUrl = API_BASE_URL;
    }

    // --- Authentication Helpers ---
    async getSession() {
        const client = getSupabase();
        if (!client) return null;
        try {
            const { data, error } = await client.auth.getSession();
            if (error || !data || !data.session) return null;
            return data.session;
        } catch (err) {
            console.error('Error fetching Supabase session:', err);
            return null;
        }
    }

    async getCurrentUser() {
        const session = await this.getSession();
        return session ? session.user : null;
    }

    async signIn(email, password) {
        const client = getSupabase();
        if (!client) throw new Error('Supabase client is not initialized.');
        const { data, error } = await client.auth.signInWithPassword({ email, password });
        if (error) throw error;
        return data;
    }

    async signUp(email, password, fullName = '') {
        const client = getSupabase();
        if (!client) throw new Error('Supabase client is not initialized.');
        const { data, error } = await client.auth.signUp({
            email,
            password,
            options: {
                data: { full_name: fullName }
            }
        });
        if (error) throw error;
        return data;
    }

    async signOut() {
        const client = getSupabase();
        if (client) {
            try {
                await client.auth.signOut();
            } catch (err) {
                console.error('Sign out error:', err);
            }
        }
        localStorage.removeItem('career_compass_profile_id');
        window.location.href = '/index.html?action=signedout';
    }

    // --- Core Fetch with Bearer Auth ---
    async _fetch(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        
        const headers = {
            'Content-Type': 'application/json',
            ...(options.headers || {})
        };

        // Attach verified Supabase JWT Bearer token
        const session = await this.getSession();
        if (session && session.access_token) {
            headers['Authorization'] = `Bearer ${session.access_token}`;
        }

        // If body is FormData, remove Content-Type so browser sets boundary
        if (options.body instanceof FormData) {
            delete headers['Content-Type'];
        }

        let response;
        try {
            response = await fetch(url, {
                ...options,
                headers
            });
        } catch (networkError) {
            console.error(`Network Error (${endpoint}):`, networkError);
            if (networkError.name === 'TypeError' && networkError.message.includes('fetch')) {
                const hint = (this.baseUrl.includes('127.0.0.1') || this.baseUrl.includes('localhost'))
                    ? 'Please check if FastAPI is running on port 8000.'
                    : 'Please check if the backend service is running or waking up.';
                throw new Error(`Unable to connect to backend server at ${this.baseUrl}. ${hint}`);
            }
            throw networkError;
        }

        let data;
        const contentType = response.headers.get('content-type') || '';
        if (contentType.includes('application/json')) {
            try {
                data = await response.json();
            } catch (jsonErr) {
                const text = await response.text().catch(() => '');
                throw new Error(`Invalid JSON response from server (${response.status}): ${text || jsonErr.message}`);
            }
        } else {
            const text = await response.text().catch(() => '');
            data = { detail: text || `Server returned HTTP ${response.status}` };
        }

        if (!response.ok) {
            if (response.status === 401) {
                console.warn('Unauthorized request to', endpoint);
            }
            const errMsg = (data && (data.message || data.detail)) || `Request failed with status ${response.status}`;
            const error = new Error(errMsg);
            error.status = response.status;
            error.data = data;
            throw error;
        }

        return data;
    }

    // --- Profile ---
    async getProfile() {
        const res = await this._fetch('/profile');
        if (res && res.success && res.data && res.data.id) {
            localStorage.setItem('career_compass_profile_id', res.data.id);
        }
        return res;
    }

    async createProfile(profileData) {
        const res = await this._fetch('/profile', {
            method: 'POST',
            body: JSON.stringify(profileData)
        });
        if (res && res.success && res.data && res.data.id) {
            localStorage.setItem('career_compass_profile_id', res.data.id);
        }
        return res;
    }

    async updateProfile(profileData) {
        const res = await this._fetch('/profile', {
            method: 'PUT',
            body: JSON.stringify(profileData)
        });
        if (res && res.success && res.data && res.data.id) {
            localStorage.setItem('career_compass_profile_id', res.data.id);
        }
        return res;
    }

    async getSkillsList() {
        return await this._fetch('/profile/skills/all');
    }

    async getInterestsList() {
        return await this._fetch('/profile/interests/all');
    }

    // --- Assessment ---
    async getAssessmentQuestions(lang = 'en') {
        return await this._fetch(`/profile/assessment/questions?lang=${encodeURIComponent(lang)}`);
    }

    async getAdaptiveNextQuestion(answers = [], transitionAcknowledged = false, lang = 'en') {
        return await this._fetch(`/profile/assessment/next?lang=${encodeURIComponent(lang)}`, {
            method: 'POST',
            body: JSON.stringify({ answers, transition_acknowledged: transitionAcknowledged })
        });
    }

    async submitAssessment(answers) {
        return await this._fetch('/profile/assessment/submit', {
            method: 'POST',
            body: JSON.stringify({ answers })
        });
    }

    // --- Careers ---
    async getCareers(branch = '', search = '') {
        const params = new URLSearchParams();
        if (branch) params.append('branch', branch);
        if (search) params.append('search', search);
        return await this._fetch(`/careers?${params.toString()}`);
    }

    async getCareerDetail(careerId) {
        return await this._fetch(`/careers/${careerId}`);
    }

    // --- Analysis ---
    async getLatestAnalysis() {
        return await this._fetch('/analysis/career');
    }

    async generateAnalysis(forceRegenerate = false) {
        return await this._fetch('/analysis/career', {
            method: 'POST',
            body: JSON.stringify({ force_regenerate: forceRegenerate })
        });
    }

    async selectCareer(careerTitle) {
        return await this._fetch('/analysis/select-career', {
            method: 'POST',
            body: JSON.stringify({ career_title: careerTitle })
        });
    }

    async getRoadmapProgress() {
        return await this._fetch('/analysis/roadmap');
    }

    async updateRoadmapStep(stepNumber, completed) {
        return await this._fetch('/analysis/roadmap/progress', {
            method: 'POST',
            body: JSON.stringify({ step_number: stepNumber, completed })
        });
    }

    // --- Chat ---
    async getChatSessions() {
        return await this._fetch('/chat/sessions');
    }

    async getChatHistory(sessionId) {
        return await this._fetch(`/chat/history/${sessionId}`);
    }

    async sendChatMessage(message, sessionId = null) {
        const body = { message };
        if (sessionId) body.session_id = sessionId;
        return await this._fetch('/chat/send', {
            method: 'POST',
            body: JSON.stringify(body)
        });
    }

    // --- Resume ---
    async getLatestResumeAnalysis() {
        return await this._fetch('/resume/latest');
    }

    async analyzeResume(file) {
        const formData = new FormData();
        formData.append('file', file);
        return await this._fetch('/resume/analyze', {
            method: 'POST',
            body: formData
        });
    }

    async deleteResumeAnalysis() {
        return await this._fetch('/resume', {
            method: 'DELETE'
        });
    }

    async getBuilderResume() {
        return await this._fetch('/resume/builder-resume');
    }

    // --- Admin ---
    async adminCreateCareer(data) {
        return await this._fetch('/admin/careers', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    async adminUpdateCareer(careerId, data) {
        return await this._fetch(`/admin/careers/${careerId}`, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    async adminDeleteCareer(careerId) {
        return await this._fetch(`/admin/careers/${careerId}`, {
            method: 'DELETE'
        });
    }

    async adminCreateSkill(data) {
        return await this._fetch('/admin/skills', {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }
}

const api = new ApiClient();

// Centralized XSS Defense Utility
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(text).replace(/[&<>"']/g, (m) => map[m]);
}

// Utility for formatting error messages (XSS-safe)
function showError(elementId, message) {
    const el = document.getElementById(elementId);
    if (el) {
        el.innerHTML = `<div class="alert alert-danger"><i class="fas fa-exclamation-circle"></i> ${escapeHtml(message)}</div>`;
        el.style.display = 'block';
    } else {
        alert(message);
    }
}

// Route Protection Guard
async function requireAuth() {
    let retries = 5;
    while (retries > 0 && !getSupabase()) {
        await new Promise(r => setTimeout(r, 100));
        retries--;
    }
    const session = await api.getSession();
    if (!session) {
        window.location.href = '/index.html?showLogin=true';
        return null;
    }
    return session.user;
}

// Dynamic Admin Navigation Synchronization
async function syncAdminNav() {
    const adminNav = document.getElementById('admin-nav-item');
    if (!adminNav) return;
    try {
        const res = await api.getProfile();
        if (res && res.data && res.data.is_admin) {
            adminNav.style.display = 'flex';
        } else {
            adminNav.style.display = 'none';
        }
    } catch (e) {
        adminNav.style.display = 'none';
    }
}
