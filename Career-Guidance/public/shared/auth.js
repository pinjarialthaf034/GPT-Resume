/**
 * shared/auth.js - Authoritative Supabase Auth Identity & Session Manager
 * 
 * Single source of truth for user identity across both Career Guidance and GPT-Resume.
 * All user identity derives strictly from the authenticated Supabase Auth user (auth.users.id).
 * LocalStorage is treated exclusively as an ephemeral UI cache (to prevent layout flash),
 * NEVER as an authentication or authorization authority.
 */

(function () {
    const SUPABASE_PROJECT_URL = 'https://fwupeplirgbyujdpzsyk.supabase.co';
    const SUPABASE_ANON_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImZ3dXBlcGxpcmdieXVqZHB6c3lrIiwicm9sZSI6ImFub24iLCJpYXQiOjE3ODQzNTI0MzMsImV4cCI6MjA5OTkyODQzM30.jpi6dvHuMPA4SAaadido8V51AiwfGbqvoGdshJvlpxY';

    const AUTH_CACHE_KEY_USER_ID = "resume_auth_user_id";
    const AUTH_CACHE_KEY_EMAIL = "userEmail";
    const AUTH_CACHE_KEY_NAME = "userName";
    const AUTH_CACHE_KEY_AVATAR = "userAvatar";
    const AUTH_CACHE_KEY_PROVIDER = "authProvider";
    const AUTH_CACHE_KEY_LOGGED_IN = "isLoggedIn";

    /**
     * Initializes and returns the global Supabase client singleton.
     */
    function getSupabaseClient() {
        if (window._supabaseInstance) {
            return window._supabaseInstance;
        }

        if (window.supabase && typeof window.supabase.auth !== "undefined" && typeof window.supabase.from === "function") {
            window._supabaseInstance = window.supabase;
            return window._supabaseInstance;
        }

        if (window.supabase && typeof window.supabase.createClient === "function") {
            window._supabaseInstance = window.supabase.createClient(SUPABASE_PROJECT_URL, SUPABASE_ANON_KEY);
            window.supabase = window._supabaseInstance;
            return window._supabaseInstance;
        }

        return null;
    }

    const eagerClient = getSupabaseClient();
    if (eagerClient) {
        window.supabase = eagerClient;
        window._supabaseInstance = eagerClient;
    }

    /**
     * Get the authenticated Supabase user securely.
     * Validates JWT with Supabase Auth server.
     * 
     * @returns {Promise<Object|null>} The authenticated user object or null
     */
    async function getCurrentUser() {
        const client = getSupabaseClient();
        if (!client) {
            console.warn("[AppAuth] Supabase client is not available.");
            return null;
        }

        try {
            const { data: sessionData, error: sessionError } = await client.auth.getSession();
            if (sessionError || !sessionData?.session?.user) {
                clearEphemeralCache();
                return null;
            }

            const { data: userData, error: userError } = await client.auth.getUser();
            if (userError || !userData?.user) {
                console.warn("[AppAuth] Session token validation failed:", userError);
                clearEphemeralCache();
                return null;
            }

            const user = userData.user;
            syncEphemeralCache(user);
            return user;
        } catch (err) {
            console.error("[AppAuth] Error retrieving authenticated user:", err);
            return null;
        }
    }

    /**
     * Get the active Supabase session.
     * @returns {Promise<Object|null>}
     */
    async function getSession() {
        const client = getSupabaseClient();
        if (!client) return null;
        try {
            const { data: { session }, error } = await client.auth.getSession();
            if (error) return null;
            return session;
        } catch (err) {
            console.error("[AppAuth] Error getting session:", err);
            return null;
        }
    }

    /**
     * Route Guard: Requires an authenticated user session.
     * If unauthenticated, safely redirects to the portal login screen.
     * 
     * @param {string} redirectUrl Optional custom redirect URL (default: /index.html?showLogin=true)
     * @returns {Promise<Object>} Returns verified user if authenticated
     */
    async function requireAuth(redirectUrl) {
        let retries = 5;
        while (retries > 0 && !getSupabaseClient()) {
            await new Promise(r => setTimeout(r, 100));
            retries--;
        }

        const user = await getCurrentUser();
        if (!user) {
            const target = redirectUrl || "/index.html?showLogin=true";
            window.location.href = target;
            throw new Error("Authentication required. Redirecting to login...");
        }
        return user;
    }

    /**
     * Signs in with email and password.
     */
    async function signIn(email, password) {
        const client = getSupabaseClient();
        if (!client) throw new Error("Supabase client is not available.");

        const { data, error } = await client.auth.signInWithPassword({ email, password });
        if (error) throw error;

        if (data?.session?.user) {
            syncEphemeralCache(data.session.user);
        }
        return data;
    }

    /**
     * Signs up with email, password, and optional user metadata.
     */
    async function signUp(email, password, metadata = {}) {
        const client = getSupabaseClient();
        if (!client) throw new Error("Supabase client is not available.");

        const { data, error } = await client.auth.signUp({
            email,
            password,
            options: {
                data: metadata
            }
        });
        if (error) throw error;

        if (data?.session?.user) {
            syncEphemeralCache(data.session.user);
        }
        return data;
    }

    /**
     * Sign out the user, invalidate the Supabase session globally, and purge ephemeral storage.
     * @param {string} postSignoutUrl Optional URL to redirect to after signout
     */
    async function signOut(postSignoutUrl) {
        clearEphemeralCache();

        const client = getSupabaseClient();
        if (client) {
            try {
                await client.auth.signOut();
            } catch (err) {
                console.error("[AppAuth] Error during Supabase signOut:", err);
            }
        }

        const target = postSignoutUrl || "/index.html?action=signedout";
        window.location.href = target;
    }

    /**
     * Update non-authoritative ephemeral UI cache (for fast initial DOM rendering).
     */
    function syncEphemeralCache(user) {
        if (!user) {
            clearEphemeralCache();
            return;
        }

        const metadata = user.user_metadata || {};
        const fullName = metadata.full_name || metadata.name || (user.email ? user.email.split("@")[0] : "User");
        const provider = user.app_metadata?.provider || (user.identities && user.identities[0]?.provider) || "email";
        const avatarUrl = metadata.avatar_url || "";

        try {
            localStorage.setItem(AUTH_CACHE_KEY_USER_ID, user.id);
            localStorage.setItem(AUTH_CACHE_KEY_EMAIL, user.email || "");
            localStorage.setItem(AUTH_CACHE_KEY_NAME, fullName);
            localStorage.setItem(AUTH_CACHE_KEY_PROVIDER, provider);
            localStorage.setItem(AUTH_CACHE_KEY_LOGGED_IN, "true");
            if (avatarUrl) {
                localStorage.setItem(AUTH_CACHE_KEY_AVATAR, avatarUrl);
            }
        } catch (e) {
            console.warn("[AppAuth] Could not write to localStorage cache:", e);
        }
    }

    /**
     * Clear all ephemeral UI caches upon sign out or session invalidation.
     */
    function clearEphemeralCache() {
        try {
            localStorage.removeItem(AUTH_CACHE_KEY_USER_ID);
            localStorage.removeItem(AUTH_CACHE_KEY_EMAIL);
            localStorage.removeItem(AUTH_CACHE_KEY_NAME);
            localStorage.removeItem(AUTH_CACHE_KEY_AVATAR);
            localStorage.removeItem(AUTH_CACHE_KEY_PROVIDER);
            localStorage.removeItem(AUTH_CACHE_KEY_LOGGED_IN);
            localStorage.removeItem("career_compass_profile_id");
        } catch (e) {
            console.warn("[AppAuth] Could not clear localStorage cache:", e);
        }
    }

    /**
     * Listen for auth state changes from Supabase.
     */
    function onAuthStateChange(callback) {
        const client = getSupabaseClient();
        if (!client) return { data: { subscription: { unsubscribe: () => {} } } };
        return client.auth.onAuthStateChange((event, session) => {
            if (session && session.user) {
                syncEphemeralCache(session.user);
            } else if (event === 'SIGNED_OUT') {
                clearEphemeralCache();
            }
            if (typeof callback === 'function') {
                callback(event, session);
            }
        });
    }

    // Export singleton on window
    const AppAuth = {
        getSupabaseClient,
        getCurrentUser,
        getSession,
        requireAuth,
        signIn,
        signUp,
        signOut,
        syncEphemeralCache,
        clearEphemeralCache,
        onAuthStateChange
    };

    window.AppAuth = AppAuth;
    // Backward compatibility alias for Resume Builder templates
    window.ResumeAuth = AppAuth;
})();
