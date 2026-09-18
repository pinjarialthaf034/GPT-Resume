/**
 * api-config.js - Centralized API URL Resolver
 * 
 * Provides environment-aware endpoint resolution for:
 * - GPT-Resume AI Backend (via Netlify proxy in production, port 8001 in local development)
 * - Career-Guidance Backend (via Netlify proxy in production, port 8000 in local development)
 */

(function () {
    const IS_LOCAL = typeof window !== 'undefined' && (
        window.location.hostname === 'localhost' ||
        window.location.hostname === '127.0.0.1' ||
        window.location.protocol === 'file:'
    );

    /**
     * Resolves the full URL for Resume AI backend endpoints.
     * Handles endpoints like "generate-summary", "/api/generate-summary", etc.
     * Production (Netlify): /api/resume-builder/{endpoint}
     * Development (Local):  http://127.0.0.1:8001/api/{endpoint}
     * 
     * @param {string} endpoint - e.g. "generate-summary" or "/api/generate-section"
     * @returns {string} The resolved API URL
     */
    function getResumeApiUrl(endpoint) {
        if (!endpoint) return IS_LOCAL ? 'http://127.0.0.1:8001/api' : '/api/resume-builder';
        let clean = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
        if (clean.startsWith('api/')) {
            clean = clean.slice(4);
        }
        if (IS_LOCAL) {
            return `http://127.0.0.1:8001/api/${clean}`;
        }
        return `/api/resume-builder/${clean}`;
    }

    /**
     * Resolves the full URL for Career Guidance backend endpoints.
     * Handles endpoints like "profile", "/api/profile", etc.
     * Production (Netlify): /api/{endpoint}
     * Development (Local):  http://127.0.0.1:8000/api/{endpoint}
     * 
     * @param {string} endpoint - e.g. "profile" or "careers"
     * @returns {string} The resolved API URL
     */
    function getCareerApiUrl(endpoint) {
        if (!endpoint) return IS_LOCAL ? 'http://127.0.0.1:8000/api' : '/api';
        let clean = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
        if (clean.startsWith('api/')) {
            clean = clean.slice(4);
        }
        if (IS_LOCAL) {
            return `http://127.0.0.1:8000/api/${clean}`;
        }
        return `/api/${clean}`;
    }

    window.IS_LOCAL = IS_LOCAL;
    window.getResumeApiUrl = getResumeApiUrl;
    window.getCareerApiUrl = getCareerApiUrl;
})();
