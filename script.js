document.addEventListener("DOMContentLoaded", () => {
    // Helper to format name from email prefix if missing
    function getNameFromEmail(email) {
        if (!email) return "User";
        const prefix = email.split('@')[0];
        const parts = prefix.split(/[\._-]/);
        return parts.map(part => part.charAt(0).toUpperCase() + part.slice(1)).join(' ');
    }

    // Helper to extract initials (e.g. Rahul Kumar -> RK, Single -> RA, Email prefix -> 2 letters)
    function getInitials(name, email) {
        if (name && name.trim()) {
            const cleanName = name.trim();
            const parts = cleanName.split(/\s+/);
            if (parts.length >= 2 && parts[0] && parts[1]) {
                return (parts[0][0] + parts[1][0]).toUpperCase();
            } else if (parts.length === 1 && parts[0]) {
                const singleName = parts[0];
                if (singleName.length >= 2) {
                    return singleName.slice(0, 2).toUpperCase();
                } else if (singleName.length === 1) {
                    return (singleName[0] + "U").toUpperCase();
                }
            }
        }
        if (email && email.trim()) {
            const prefix = email.trim().split('@')[0];
            const cleanPrefix = prefix.replace(/[\._-]/g, ' ');
            const parts = cleanPrefix.trim().split(/\s+/);
            if (parts.length >= 2 && parts[0] && parts[1]) {
                return (parts[0][0] + parts[1][0]).toUpperCase();
            } else {
                if (prefix.length >= 2) {
                    return prefix.slice(0, 2).toUpperCase();
                } else if (prefix.length === 1) {
                    return (prefix[0] + "U").toUpperCase();
                }
            }
        }
        return "US";
    }

    // 1. DYNAMIC CHROMATIC BACKGROUND SLIDER LOGIC
    const slides = document.querySelectorAll(".slide");
    let currentSlide = 0;

    if (slides.length > 0) {
        setInterval(() => {
            slides[currentSlide].classList.remove("active");
            currentSlide = (currentSlide + 1) % slides.length;
            slides[currentSlide].classList.add("active");
        }, 5000);
    }

    // 2. LOGIN STATE & DOM SELECTORS
    let isLoggedIn = localStorage.getItem("isLoggedIn") === "true";
    let isSignUpMode = false;
    let currentModalConfirmCallback = null;
    let isSigningOut = false;

    const goToBuilder = document.getElementById("goToBuilder");
    const goToGuidance = document.getElementById("goToGuidance");
    const authModal = document.getElementById("authModal");
    const modalMessage = document.getElementById("modalMessage");
    const modalTitle = document.getElementById("modalTitle");
    const modalIcon = document.getElementById("modalIcon");
    const closeModalBtn = document.getElementById("closeModalBtn");

    const modalContentNotice = document.getElementById("modalContentNotice");
    const modalContentForm = document.getElementById("modalContentForm");
    const formTitle = document.getElementById("formTitle");
    const authForm = document.getElementById("authForm");
    const submitAuthBtn = document.getElementById("submitAuthBtn");
    const signUpFields = document.getElementById("signUpFields");
    const toggleFormText = document.getElementById("toggleFormText");
    const navHome = document.getElementById("navHome");
    const googleAuthBtn = document.getElementById("googleAuthBtn");

    // Initialize Supabase reference locally using window to prevent variable shadowing/ReferenceErrors
    const supabase = window.supabase;
    const isSupabaseReady = supabase && typeof supabase.auth !== 'undefined';

    if (!isSupabaseReady) {
        console.error("Supabase client is not initialized or .auth is missing. Supabase actions will be offline.");
    }

    // Google Sign-In Trigger Function forcing account selection
    async function signInWithGoogle() {
        if (!isSupabaseReady) return;
        const redirectUrl = window.location.origin.includes('netlify.app') 
            ? 'https://gpt-resume.netlify.app/index.html' 
            : `${window.location.origin}/index.html`;

        const { data, error } = await supabase.auth.signInWithOAuth({
            provider: 'google',
            options: {
                redirectTo: redirectUrl,
                queryParams: {
                    prompt: 'select_account'
                }
            }
        });
    }

    if (googleAuthBtn) {
        googleAuthBtn.addEventListener("click", signInWithGoogle);
    }

    // Recover Supabase Session
    async function checkSupabaseSession() {
        if (!isSupabaseReady) return;
        try {
            const { data: { session }, error } = await supabase.auth.getSession();
            if (session && session.user) {
                const userObj = session.user;
                const metadata = userObj.user_metadata || {};
                const nameVal = metadata.full_name || metadata.name || (userObj.email ? userObj.email.split('@')[0] : "User");
                const provider = userObj.app_metadata?.provider || (userObj.identities && userObj.identities[0]?.provider) || 'email';

                localStorage.setItem("isLoggedIn", "true");
                localStorage.setItem("userEmail", userObj.email);
                localStorage.setItem("userName", nameVal);
                localStorage.setItem("authProvider", provider);
                if (session.user.user_metadata?.avatar_url) {
                    localStorage.setItem("userAvatar", session.user.user_metadata.avatar_url);
                } else {
                    localStorage.removeItem("userAvatar");
                }

                isLoggedIn = true;
                updateLoginButton();
            }
        } catch (err) {
            console.error("Error checking Supabase session:", err);
        }
    }

    if (isSupabaseReady) {
        checkSupabaseSession();

        // Listen for auth changes
        supabase.auth.onAuthStateChange((event, session) => {
            if (session && session.user) {
                const userObj = session.user;
                const metadata = userObj.user_metadata || {};
                const nameVal = metadata.full_name || metadata.name || (userObj.email ? userObj.email.split('@')[0] : "User");
                const provider = userObj.app_metadata?.provider || (userObj.identities && userObj.identities[0]?.provider) || 'email';

                localStorage.setItem("isLoggedIn", "true");
                localStorage.setItem("userEmail", userObj.email);
                localStorage.setItem("userName", nameVal);
                localStorage.setItem("authProvider", provider);
                if (session.user.user_metadata?.avatar_url) {
                    localStorage.setItem("userAvatar", session.user.user_metadata.avatar_url);
                } else {
                    localStorage.setItem("userAvatar", "");
                }

                // If this is a newly resolved login from a Google OAuth callback redirect on index.html
                const isOAuthCallback = window.location.hash.includes("access_token=") || window.location.hash.includes("id_token=");
                if (isOAuthCallback && !localStorage.getItem("googleLoginHandled")) {
                    localStorage.setItem("googleLoginHandled", "true");

                    // Clear hash from URL so it doesn't fire repeatedly
                    if (window.history && window.history.replaceState) {
                        window.history.replaceState(null, document.title, window.location.pathname + window.location.search);
                    }

                    // Show blocking success modal with redirect callback on close button click
                    showNoticeModal(
                        "🎉",
                        "Login Successful",
                        `Welcome back, ${nameVal}! You have logged in successfully with Google.`,
                        "#10B981",
                        () => {
                            localStorage.removeItem("googleLoginHandled");
                            window.location.href = "builder.html";
                        }
                    );
                }

                isLoggedIn = true;
                updateLoginButton();
            } else if (event === 'SIGNED_OUT') {
                localStorage.removeItem("isLoggedIn");
                localStorage.removeItem("userEmail");
                localStorage.removeItem("userName");
                localStorage.removeItem("userAvatar");
                localStorage.removeItem("authProvider");
                localStorage.removeItem("googleLoginHandled");
                isLoggedIn = false;
                if (!isSigningOut) {
                    updateLoginButton();
                }
            }
        });
    }

    function openProfileModal(e) {
        if (e) e.stopPropagation();
        const profileModal = document.getElementById("profileModal") || document.getElementById("profileDropdownMenu");
        if (profileModal) {
            profileModal.classList.toggle("show");
        }
    }

    // Dynamic Login/Logout Button and User Badge Handler
    function updateLoginButton() {
        const loginBtn = document.getElementById("loginBtn");
        const profileModalContainer = document.getElementById("profileModalContainer");
        const avatarInitials = document.getElementById("avatarInitials");
        const avatarImg = document.getElementById("avatarImg");
        const profileName = document.getElementById("profileName");
        const profileEmail = document.getElementById("profileEmail");

        if (isLoggedIn) {
            // Hide login button, show profile modal container
            if (loginBtn) loginBtn.style.display = "none";
            if (profileModalContainer) profileModalContainer.style.display = "inline-block";

            const userEmail = localStorage.getItem("userEmail") || "User";
            const userName = localStorage.getItem("userName") || "";
            const userAvatar = localStorage.getItem("userAvatar");

            if (profileName) profileName.textContent = userName;
            if (profileEmail) profileEmail.textContent = userEmail;

            if (userAvatar) {
                if (avatarImg) {
                    avatarImg.src = userAvatar;
                    avatarImg.style.display = "block";
                }
                if (avatarInitials) avatarInitials.style.display = "none";
            } else {
                const initials = getInitials(userName, userEmail);
                if (avatarInitials) {
                    avatarInitials.textContent = initials;
                    avatarInitials.style.display = "flex";
                }
                if (avatarImg) avatarImg.style.display = "none";
            }
        } else {
            // Show login button, hide profile modal container
            if (loginBtn) loginBtn.style.display = "block";
            if (profileModalContainer) profileModalContainer.style.display = "none";
        }
    }

    // Global Click Listener for Event Delegation
    document.addEventListener('click', function (e) {
        // 1. Open/Toggle Profile Modal on clicking the avatar element (or its initials/img)
        const avatarBtn = e.target.closest('#userAvatar');
        if (avatarBtn) {
            e.stopPropagation();
            openProfileModal(e);
            return;
        }

        // 2. Clicked "Sign Out" button inside the profile modal
        const signOutBtn = e.target.closest('#signOutBtn');
        if (signOutBtn) {
            e.stopPropagation();
            const profileModal = document.getElementById("profileModal") || document.getElementById("profileDropdownMenu");
            if (profileModal) {
                profileModal.classList.remove("show");
            }
            handleSignOut(e);
            return;
        }

        // 3. Clicked "Upload Photo" button inside the profile modal
        const uploadAvatarBtn = e.target.closest('#uploadAvatarBtn');
        if (uploadAvatarBtn) {
            e.stopPropagation();
            const avatarUploadInput = document.getElementById("avatarUploadInput");
            if (avatarUploadInput) {
                avatarUploadInput.click();
            }
            return;
        }

        // 4. Clicked "Sign In" button (loginBtn)
        const loginBtn = e.target.closest('#loginBtn');
        if (loginBtn) {
            e.stopPropagation();
            handleLoginClick();
            return;
        }

        // 5. Default: Close dropdown when clicking outside
        const profileModal = document.getElementById("profileModal") || document.getElementById("profileDropdownMenu");
        if (profileModal && !e.target.closest('#profileModal') && !e.target.closest('#profileDropdownMenu') && !e.target.closest('#userAvatar')) {
            profileModal.classList.remove("show");
        }
    });

    // Global Change Listener for Avatar File Upload
    document.addEventListener("change", async (e) => {
        if (e.target && e.target.id === 'avatarUploadInput') {
            e.stopPropagation();
            const file = e.target.files[0];
            if (!file) return;

            try {
                if (!isSupabaseReady) {
                    throw new Error("Supabase client is not ready.");
                }

                const fileExt = file.name.split('.').pop();
                const fileName = `${Date.now()}.${fileExt}`;
                const filePath = `${fileName}`;

                const { data, error } = await supabase.storage
                    .from('avatars')
                    .upload(filePath, file);

                let publicUrl = "";
                if (error) {
                    console.warn("Storage upload failed, attempting local URL preview fallback:", error);
                    publicUrl = URL.createObjectURL(file);
                } else {
                    const { data: { publicUrl: retrievedUrl } } = supabase.storage
                        .from('avatars')
                        .getPublicUrl(filePath);
                    publicUrl = retrievedUrl;
                }

                // Update user metadata in Supabase (all are standard Supabase Auth users now)
                try {
                    const { error: metadataError } = await supabase.auth.updateUser({
                        data: { avatar_url: publicUrl }
                    });
                    if (metadataError) throw metadataError;
                } catch (metaErr) {
                    console.warn("Could not save avatar url to Supabase user metadata:", metaErr);
                }

                localStorage.setItem("userAvatar", publicUrl);

                // Instantly set src for all avatar <img> tags on the current page
                const avatarImgs = document.querySelectorAll(".user-avatar-img");
                avatarImgs.forEach(img => {
                    img.src = publicUrl;
                    img.style.display = "block";
                });

                // Hide initials if visible
                const avatarInitials = document.querySelectorAll(".user-avatar-initials");
                avatarInitials.forEach(init => {
                    init.style.display = "none";
                });

                showNoticeModal("📸", "Profile Updated", "Profile photo updated successfully!", "#10B981");

            } catch (err) {
                console.error("Avatar upload issue:", err);
                showNoticeModal("❌", "Upload Failed", "Failed to process photo upload: " + err.message, "#EF4444");
            }
        }
    });

    // Handle Sign Out Click
    async function handleSignOut(event) {
        if (event) event.stopPropagation();

        isSigningOut = true;

        const isBuilderPage = window.location.pathname.includes("builder.html");
        const isGuidancePage = window.location.pathname.includes("guidance.html");

        if (isBuilderPage || isGuidancePage) {
            // 1. Immediately clear local storage / session state
            localStorage.removeItem("isLoggedIn");
            localStorage.removeItem("userEmail");
            localStorage.removeItem("userName");
            localStorage.removeItem("userAvatar");
            localStorage.removeItem("authProvider");
            isLoggedIn = false;

            // 2. Call supabase signOut and wait
            if (isSupabaseReady) {
                try {
                    await supabase.auth.signOut();
                } catch (err) {
                    console.error("Sign out session error:", err);
                }
            }

            // 3. Force immediate page redirect
            window.location.href = "index.html?action=signedout";
            return;
        }

        // Otherwise (we are on index.html)
        // Immediately reset local storage & UI to logged-out state
        localStorage.removeItem("isLoggedIn");
        localStorage.removeItem("userEmail");
        localStorage.removeItem("userName");
        localStorage.removeItem("userAvatar");
        localStorage.removeItem("authProvider");
        isLoggedIn = false;
        updateLoginButton();

        // Close dropdown menu if open
        const profileModal = document.getElementById("profileModal") || document.getElementById("profileDropdownMenu");
        if (profileModal) {
            profileModal.classList.remove("show");
        }

        // Call supabase signOut
        if (isSupabaseReady) {
            try {
                await supabase.auth.signOut();
            } catch (err) {
                console.error("Sign out session error:", err);
            }
        }

        // Simultaneously open and display the custom success modal
        showNoticeModal(
            "👋",
            "Signout Successful",
            "You have been signed out successfully.",
            "#10B981"
        );
        isSigningOut = false;
    }

    // Handle Login Button Click (Toggle Modal / Logout)
    async function handleLoginClick() {
        if (isLoggedIn) {
            handleSignOut();
        } else {
            // Show Login Form
            if (modalContentNotice) modalContentNotice.style.display = "none";
            if (modalContentForm) modalContentForm.style.display = "block";

            setAuthMode(false);
            openModal();
        }
    }

    // Sync initial load theme to body
    const savedTheme = localStorage.getItem("theme") || "light";
    document.documentElement.setAttribute("data-theme", savedTheme);
    if (document.body) {
        document.body.setAttribute("data-theme", savedTheme);
    }
    updateLoginButton();

    // Check for showLogin URL parameter to auto-open login modal
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.get("showLogin") === "true") {
        if (modalContentNotice) modalContentNotice.style.display = "none";
        if (modalContentForm) modalContentForm.style.display = "block";
        setAuthMode(false);
        openModal();
        window.history.replaceState({}, document.title, window.location.pathname);
    }

    // Check for signedout/action URL parameters to show signout modal
    const hasSignedOutParam = urlParams.get("action") === "signedout" || urlParams.get("signedout") === "true";
    if (hasSignedOutParam) {
        // IMMEDIATELY clean up and remove the query parameter from the browser URL so F5 won't show it again
        if (window.history && window.history.replaceState) {
            window.history.replaceState({}, document.title, window.location.pathname);
        }
        
        // Clear any temporary signout flags stored in sessionStorage or localStorage
        localStorage.removeItem("signedout");
        sessionStorage.removeItem("signedout");
        localStorage.removeItem("action");
        sessionStorage.removeItem("action");

        localStorage.removeItem("isLoggedIn");
        localStorage.removeItem("userEmail");
        localStorage.removeItem("userName");
        localStorage.removeItem("userAvatar");
        localStorage.removeItem("authProvider");
        isLoggedIn = false;
        updateLoginButton();

        showNoticeModal(
            "👋",
            "Signout Successful",
            "You have been signed out successfully.",
            "#10B981"
        );
    }

    function setAuthMode(signUp) {
        isSignUpMode = signUp;

        const authErrorText = document.getElementById("authErrorText");
        if (authErrorText) {
            authErrorText.style.display = "none";
            authErrorText.textContent = "";
        }

        if (formTitle) formTitle.textContent = signUp ? "Create an Account" : "Sign In to GPT Hub";
        if (submitAuthBtn) submitAuthBtn.textContent = signUp ? "Sign Up" : "Log In";
        if (signUpFields) signUpFields.style.display = signUp ? "flex" : "none";

        if (toggleFormText) {
            if (signUp) {
                toggleFormText.innerHTML = `Already have an account? <a href="#" id="switchToSignUp" style="color: #0070f3; font-weight: 600; text-decoration: none;">Log In</a>`;
            } else {
                toggleFormText.innerHTML = `Don't have an account? <a href="#" id="switchToSignUp" style="color: #0070f3; font-weight: 600; text-decoration: none;">Sign Up</a>`;
            }
        }

        const switchToSignUp = document.getElementById("switchToSignUp");
        if (switchToSignUp) {
            switchToSignUp.addEventListener("click", (e) => {
                e.preventDefault();
                setAuthMode(!isSignUpMode);
            });
        }
    }

    // Modal Control wrappers with safe guards
    if (closeModalBtn) {
        closeModalBtn.addEventListener("click", () => {
            closeModal();
            if (currentModalConfirmCallback) {
                const cb = currentModalConfirmCallback;
                currentModalConfirmCallback = null;
                cb();
            }
        });
    }

    function openModal() {
        const authErrorText = document.getElementById("authErrorText");
        if (authErrorText) {
            authErrorText.style.display = "none";
            authErrorText.textContent = "";
        }
        currentModalConfirmCallback = null;
        if (authModal) {
            authModal.classList.remove("hidden");
            setTimeout(() => authModal.classList.add("show-modal"), 10);
        }
    }

    function closeModal() {
        if (authModal) {
            authModal.classList.remove("show-modal");
            setTimeout(() => authModal.classList.add("hidden"), 300);
        }
    }

    function showNoticeModal(icon, title, message, titleColor = "", confirmCallback = null) {
        if (modalContentForm) modalContentForm.style.display = "none";
        if (modalContentNotice) modalContentNotice.style.display = "block";

        if (modalIcon) modalIcon.innerHTML = icon;
        if (modalTitle) {
            modalTitle.textContent = title;
            modalTitle.style.color = titleColor || "var(--text-primary)";
        }
        if (modalMessage) modalMessage.innerHTML = message;

        currentModalConfirmCallback = confirmCallback;

        openModal();
    }

    function showDeniedModal(message) {
        showNoticeModal("🔒", "Access Denied", message, "#ef4444");
    }

    // Helper to get loaded bcrypt library instance
    function getBcrypt() {
        if (typeof bcrypt !== 'undefined') return bcrypt;
        if (typeof dcodeIO !== 'undefined' && dcodeIO.bcrypt) return dcodeIO.bcrypt;
        return null;
    }

    // Handle Form Submit (Supabase Login / Sign Up Operations)
    if (authForm) {
        authForm.addEventListener("submit", async (e) => {
            e.preventDefault();

            const regNameEl = document.getElementById("regName");
            const authEmailEl = document.getElementById("authEmail");
            const authPasswordEl = document.getElementById("authPassword");
            const authErrorText = document.getElementById("authErrorText");

            if (authErrorText) {
                authErrorText.style.display = "none";
                authErrorText.textContent = "";
            }

            const name = regNameEl ? regNameEl.value.trim() : "";
            const email = authEmailEl ? authEmailEl.value.trim() : "";
            const password = authPasswordEl ? authPasswordEl.value : "";

            const originalBtnText = submitAuthBtn ? submitAuthBtn.textContent : "Submit";
            if (submitAuthBtn) {
                submitAuthBtn.disabled = true;
                submitAuthBtn.textContent = isSignUpMode ? "Registering..." : "Authenticating...";
            }

            if (!isSupabaseReady) {
                if (authErrorText) {
                    authErrorText.textContent = "Authentication service is currently unavailable. Please check your connection.";
                    authErrorText.style.display = "block";
                }
                if (submitAuthBtn) {
                    submitAuthBtn.disabled = false;
                    submitAuthBtn.textContent = originalBtnText;
                }
                return;
            }

            try {
                const bcryptLib = getBcrypt();
                if (!bcryptLib) {
                    throw new Error("Bcrypt library loading failed. Please check network connection.");
                }

                if (isSignUpMode) {
                    // 1. Register user via actual Supabase Auth
                    const { data: authData, error: signUpError } = await supabase.auth.signUp({
                        email,
                        password,
                        options: {
                            data: {
                                full_name: name,
                                name: name
                            }
                        }
                    });

                    if (signUpError) throw signUpError;

                    // 2. Hash Password and save to custom users table for backwards-compatibility
                    try {
                        const salt = bcryptLib.genSaltSync(8);
                        const hashedPassword = bcryptLib.hashSync(password, salt);
                        await supabase
                            .from("users")
                            .insert([{ name, email, password: hashedPassword }]);
                    } catch (dbErr) {
                        console.warn("Could not insert user to legacy users table:", dbErr);
                    }

                    // 3. Immediately log them in / set active session
                    let session = authData.session;
                    if (!session && authData.user) {
                        // Fallback manual sign-in just in case signUp session wasn't auto-returned
                        const { data: signInData, error: signInError } = await supabase.auth.signInWithPassword({
                            email,
                            password
                        });
                        if (!signInError) {
                            session = signInData.session;
                        }
                    }

                    if (session && session.user) {
                        isLoggedIn = true;
                        localStorage.setItem("isLoggedIn", "true");
                        localStorage.setItem("userEmail", session.user.email);
                        const finalName = name || getNameFromEmail(session.user.email);
                        localStorage.setItem("userName", finalName);
                        localStorage.setItem("authProvider", "email");
                        localStorage.removeItem("userAvatar");

                        authForm.reset();
                        updateLoginButton();

                        showNoticeModal(
                            "🎉",
                            "Login Successful",
                            `Welcome, ${finalName}! Registration successful.`,
                            "#10B981",
                            () => {
                                window.location.href = "builder.html";
                            }
                        );
                    } else {
                        // In case of required email verification
                        showNoticeModal("📧", "Verification Required", "Registration succeeded, but email verification may be required. Please check your inbox.", "#3b82f6");
                    }

                } else {
                    // 1. Attempt standard Supabase Auth Login
                    let authData = null;
                    let authError = null;
                    try {
                        const { data, error } = await supabase.auth.signInWithPassword({
                            email,
                            password
                        });
                        authData = data;
                        authError = error;
                    } catch (e) {
                        authError = e;
                    }

                    // 2. If Supabase Auth fails, auto-migrate legacy users from users table
                    if (authError) {
                        const { data: dbUsers, error: dbError } = await supabase
                            .from("users")
                            .select("*")
                            .eq("email", email);

                        if (!dbError && dbUsers && dbUsers.length > 0) {
                            const dbUser = dbUsers[0];
                            let passwordMatch = false;
                            if (dbUser.password.startsWith("$2a$") || dbUser.password.startsWith("$2b$")) {
                                passwordMatch = bcryptLib.compareSync(password, dbUser.password);
                            } else {
                                passwordMatch = (password === dbUser.password);
                            }

                            if (passwordMatch) {
                                // Password matches database custom record! Auto-create Supabase Auth account.
                                const { data: signUpData, error: signUpError } = await supabase.auth.signUp({
                                    email,
                                    password,
                                    options: {
                                        data: {
                                            full_name: dbUser.name
                                        }
                                    }
                                });

                                if (!signUpError) {
                                    authData = signUpData;
                                    authError = null;

                                    // If signUp does not give a session, sign in manually
                                    if (!authData.session) {
                                        const { data: signInData, error: signInError } = await supabase.auth.signInWithPassword({
                                            email,
                                            password
                                        });
                                        if (!signInError) {
                                            authData = signInData;
                                        } else {
                                            authError = signInError;
                                        }
                                    }
                                } else {
                                    authError = signUpError;
                                }
                            }
                        }
                    }

                    if (authError) {
                        if (authErrorText) {
                            authErrorText.textContent = "Invalid email or password";
                            authErrorText.style.display = "block";
                        }
                        return;
                    }

                    // Success login
                    const session = authData.session;
                    if (session && session.user) {
                        isLoggedIn = true;
                        localStorage.setItem("isLoggedIn", "true");
                        localStorage.setItem("userEmail", session.user.email);
                        localStorage.setItem("authProvider", "email");

                        const metadata = session.user.user_metadata || {};
                        const nameVal = metadata.full_name || metadata.name || name || getNameFromEmail(session.user.email);
                        const avatarUrl = metadata.avatar_url || "";

                        localStorage.setItem("userName", nameVal);
                        if (avatarUrl) {
                            localStorage.setItem("userAvatar", avatarUrl);
                        } else {
                            localStorage.removeItem("userAvatar");
                        }

                        updateLoginButton();
                        authForm.reset();

                        showNoticeModal(
                            "🎉",
                            "Login Successful",
                            `Welcome back, ${nameVal}!`,
                            "#10B981",
                            () => {
                                window.location.href = "builder.html";
                            }
                        );
                    }
                }
            } catch (err) {
                console.error("Database Auth Error:", err);
                if (authErrorText) {
                    authErrorText.textContent = err.message || "An error occurred during authentication.";
                    authErrorText.style.display = "block";
                } else {
                    showNoticeModal("❌", "Error Occurred", err.message || "An error occurred during authentication.", "#ef4444");
                }
            } finally {
                if (submitAuthBtn) {
                    submitAuthBtn.disabled = false;
                    submitAuthBtn.textContent = originalBtnText;
                }
            }
        });
    }
    // Resume Builder Router Link
    if (goToBuilder) {
        goToBuilder.addEventListener("click", () => {
            if (!isLoggedIn) {
                showDeniedModal("Before Accessing the AI Career Builder and Guidance You need to signup/signin first");
            } else {
                window.location.href = "https://gpt-career.netlify.app/profile";
            }
        });
    }

    // Career Guidance Router Link
    if (goToGuidance) {
        goToGuidance.addEventListener("click", () => {
            if (!isLoggedIn) {
                showDeniedModal("Before Accessing the AI Career Builder and Guidance You need to signup/signin first");
            } else {
                window.location.href = "https://gpt-career.netlify.app/profile";
            }
        });
    }

    if (navHome) {
        navHome.addEventListener("click", (e) => {
            e.preventDefault();
            closeModal();
        });
    }
});

// Safe template preview helper in case script.js is loaded on builder views
window.openPreviewFromScript = async function (index) {
    const cards = document.querySelectorAll(".template-card");
    if (cards.length === 0) return;
    const current = index % cards.length;
    const card = cards[current];

    const previewImage = document.getElementById("previewImage");
    if (previewImage && card) {
        const img = card.querySelector(".resume-preview img");
        if (img) previewImage.src = img.src;
    }

    const title = document.getElementById("templateTitle");
    if (title && card) {
        title.textContent = card.dataset.name || (card.querySelector("h3") ? card.querySelector("h3").textContent : "");
    }

    const featureList = document.getElementById("templateFeatures");
    if (featureList && card) {
        featureList.innerHTML = "";
        const features = (card.dataset.features || "").split("|");
        features.forEach(feature => {
            if (feature.trim() !== "") {
                const li = document.createElement("li");
                li.innerHTML = "✔ " + feature;
                featureList.appendChild(li);
            }
        });
    }
};
