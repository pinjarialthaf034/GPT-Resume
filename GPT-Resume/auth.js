/**
 * auth.js - Centralized Supabase Auth Identity Manager for GPT-Resume
 * 
 * Single source of truth for user identity across the Resume Builder application.
 * All user identity must derive from authenticated Supabase Auth user (auth.users.id).
 * localStorage is treated ONLY as an ephemeral UI cache (for preventing layout flash),
 * NEVER as an authentication or authorization authority.
 */

(function () {
    const AUTH_CACHE_KEY_USER_ID = "resume_auth_user_id";
    const AUTH_CACHE_KEY_EMAIL = "userEmail";
    const AUTH_CACHE_KEY_NAME = "userName";
    const AUTH_CACHE_KEY_AVATAR = "userAvatar";
    const AUTH_CACHE_KEY_PROVIDER = "authProvider";
    const AUTH_CACHE_KEY_LOGGED_IN = "isLoggedIn";

    function getSupabaseClient() {
        if (window.supabase && typeof window.supabase.auth !== "undefined") {
            return window.supabase;
        }
        return null;
    }

    /**
     * Get the authenticated Supabase user securely.
     * Uses supabase.auth.getUser() which validates the JWT with the Supabase Auth server,
     * rather than trusting unverified localStorage or local cache.
     * 
     * @returns {Promise<Object|null>} The authenticated user object or null
     */
    async function getCurrentUser() {
        const client = getSupabaseClient();
        if (!client) {
            console.warn("[ResumeAuth] Supabase client is not available.");
            return null;
        }

        try {
            // First check if a session exists locally
            const { data: sessionData, error: sessionError } = await client.auth.getSession();
            if (sessionError || !sessionData?.session?.user) {
                clearEphemeralCache();
                return null;
            }

            // Cryptographically verify the session against Supabase Auth
            const { data: userData, error: userError } = await client.auth.getUser();
            if (userError || !userData?.user) {
                console.warn("[ResumeAuth] Session token validation failed:", userError);
                clearEphemeralCache();
                return null;
            }

            const user = userData.user;
            syncEphemeralCache(user);
            return user;
        } catch (err) {
            console.error("[ResumeAuth] Error retrieving authenticated user:", err);
            return null;
        }
    }

    /**
     * Get the active session securely.
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
            console.error("[ResumeAuth] Error getting session:", err);
            return null;
        }
    }

    /**
     * Route Guard: Requires an authenticated user session.
     * If unauthenticated, safely redirects to the login screen.
     * 
     * @param {string} redirectUrl Page to redirect to if unauthenticated (default: index.html?showLogin=true)
     * @returns {Promise<Object>} Returns verified user if authenticated
     */
    async function requireAuth(redirectUrl) {
        const user = await getCurrentUser();
        if (!user) {
            const target = redirectUrl || (
                window.location.pathname.includes("/templates/") 
                    ? "../index.html?showLogin=true" 
                    : "index.html?showLogin=true"
            );
            window.location.href = target;
            throw new Error("Authentication required. Redirecting to login...");
        }
        return user;
    }

    /**
     * Sign out the user, invalidate the Supabase session, and purge ephemeral storage.
     * @param {string} postSignoutUrl Optional URL to redirect to after signout
     */
    async function signOut(postSignoutUrl) {
        clearEphemeralCache();

        const client = getSupabaseClient();
        if (client) {
            try {
                await client.auth.signOut();
            } catch (err) {
                console.error("[ResumeAuth] Error during Supabase signOut:", err);
            }
        }

        if (postSignoutUrl) {
            window.location.href = postSignoutUrl;
        }
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
            } else {
                localStorage.removeItem(AUTH_CACHE_KEY_AVATAR);
            }
        } catch (e) {
            // Storage quota or privacy mode errors handled gracefully
        }
    }

    /**
     * Clear all non-authoritative ephemeral UI caches.
     */
    function clearEphemeralCache() {
        try {
            localStorage.removeItem(AUTH_CACHE_KEY_USER_ID);
            localStorage.removeItem(AUTH_CACHE_KEY_EMAIL);
            localStorage.removeItem(AUTH_CACHE_KEY_NAME);
            localStorage.removeItem(AUTH_CACHE_KEY_AVATAR);
            localStorage.removeItem(AUTH_CACHE_KEY_PROVIDER);
            localStorage.removeItem(AUTH_CACHE_KEY_LOGGED_IN);
            localStorage.removeItem("googleLoginHandled");
        } catch (e) {
            // Ignored
        }
    }

    /**
     * Listen for Supabase auth state changes.
     * @param {Function} callback Callback receiving (event, session, user)
     */
    function onAuthStateChange(callback) {
        const client = getSupabaseClient();
        if (!client) return null;

        return client.auth.onAuthStateChange(async (event, session) => {
            if (event === "SIGNED_OUT" || !session?.user) {
                clearEphemeralCache();
                if (typeof callback === "function") callback(event, null, null);
            } else if (session?.user) {
                syncEphemeralCache(session.user);
                if (typeof callback === "function") callback(event, session, session.user);
            }
        });
    }

    // Export globally
    window.ResumeAuth = {
        getCurrentUser,
        getSession,
        requireAuth,
        signOut,
        onAuthStateChange,
        syncEphemeralCache,
        clearEphemeralCache,
        getSupabaseClient
    };
})();
