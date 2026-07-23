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
        const { data, error } = await supabase.auth.signInWithOAuth({
            provider: 'google',
            options: {
                redirectTo: window.location.origin + '/builder.html',
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
                isLoggedIn = true;
                updateLoginButton();
            } else if (event === 'SIGNED_OUT') {
                localStorage.removeItem("isLoggedIn");
                localStorage.removeItem("userEmail");
                localStorage.removeItem("userName");
                localStorage.removeItem("userAvatar");
                localStorage.removeItem("authProvider");
                if (isLoggedIn) {
                    isLoggedIn = false;
                    updateLoginButton();
                }
            }
        });
    }

    // Dynamic Login/Logout Button and User Badge Handler (dropdown lists/menus are strictly banned)
    function updateLoginButton() {
        const navActions = document.querySelector(".nav-actions");
        if (!navActions) return;

        if (isLoggedIn) {
            const userEmail = localStorage.getItem("userEmail") || "User";
            const userName = localStorage.getItem("userName") || "";
            const userAvatar = localStorage.getItem("userAvatar");

            let avatarHtml = "";
            if (userAvatar) {
                avatarHtml = `<img src="${userAvatar}" alt="Profile" class="user-avatar-img">`;
            } else {
                const initials = getInitials(userName, userEmail);
                avatarHtml = `<span class="user-avatar-initials">${initials}</span>`;
            }

            // Check if provider is email/password or google
            const provider = localStorage.getItem("authProvider") || "email";
            let uploadHtml = "";
            if (provider !== "google") {
                uploadHtml = `
                    <input type="file" id="avatarUploadInput" accept="image/*" style="display:none;">
                    <button type="button" class="btn-login" style="background:rgba(56, 189, 248, 0.15); color:var(--accent-blue); border:1px solid rgba(56, 189, 248, 0.4); margin-right:10px; font-size:12px; padding:6px 12px;" id="uploadAvatarBtn">Upload Photo</button>
                `;
            }

            navActions.innerHTML = `
                <div style="display:flex; align-items:center; gap:10px;">
                    ${uploadHtml}
                    <div class="user-avatar-circle" style="cursor:default;">
                        ${avatarHtml}
                    </div>
                    <button class="btn-login" id="signOutBtn" style="background:#ef4444; color:#fff; font-size:13px; padding:8px 16px;">Sign Out</button>
                </div>
            `;

            // Upload Avatar triggers
            const uploadAvatarBtn = document.getElementById("uploadAvatarBtn");
            const avatarUploadInput = document.getElementById("avatarUploadInput");
            if (uploadAvatarBtn && avatarUploadInput) {
                uploadAvatarBtn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    avatarUploadInput.click();
                });
            }

            if (avatarUploadInput) {
                avatarUploadInput.addEventListener("change", async (e) => {
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

                        // Save url in user metadata in Supabase
                        try {
                            const { error: metadataError } = await supabase.auth.updateUser({
                                data: { avatar_url: publicUrl }
                            });
                            if (metadataError) throw metadataError;
                        } catch (metaErr) {
                            console.warn("Could not save avatar url to Supabase user metadata:", metaErr);
                        }

                        localStorage.setItem("userAvatar", publicUrl);
                        updateLoginButton();
                        alert("Profile photo updated successfully!");

                    } catch (err) {
                        console.error("Avatar upload issue:", err);
                        alert("Failed to process photo upload: " + err.message);
                    }
                });
            }

            // Sign out logic
            const signOutBtn = document.getElementById("signOutBtn");
            if (signOutBtn) {
                signOutBtn.addEventListener("click", (e) => {
                    e.stopPropagation();
                    handleSignOut(e);
                });
            }
        } else {
            navActions.innerHTML = `
                <button class="btn-login" id="loginBtn" style="background:var(--accent-blue); color:#000;">Sign In</button>
            `;
        }
        
        // Re-attach listener after updating innerHTML
        const loginBtn = document.getElementById("loginBtn");
        if (loginBtn) {
            loginBtn.addEventListener("click", handleLoginClick);
        }
    }

    // Handle Sign Out Click
    async function handleSignOut(event) {
        if (event) event.stopPropagation();
        localStorage.removeItem("isLoggedIn");
        localStorage.removeItem("userEmail");
        localStorage.removeItem("userName");
        localStorage.removeItem("userAvatar");
        localStorage.removeItem("authProvider");
        if (isSupabaseReady) {
            try {
                await supabase.auth.signOut();
            } catch (err) {
                console.error("Sign out session error:", err);
            }
        }
        window.location.href = "index.html";
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

    function setAuthMode(signUp) {
        isSignUpMode = signUp;

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
        closeModalBtn.addEventListener("click", closeModal);
    }

    function openModal() {
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

    function showDeniedModal(message) {
        if (modalContentForm) modalContentForm.style.display = "none";
        if (modalContentNotice) modalContentNotice.style.display = "block";

        if (modalIcon) modalIcon.innerHTML = "🔒";
        if (modalTitle) {
            modalTitle.textContent = "Access Denied";
            modalTitle.style.color = "#ef4444";
        }
        if (modalMessage) modalMessage.innerHTML = message;

        openModal();
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

            const name = regNameEl ? regNameEl.value.trim() : "";
            const email = authEmailEl ? authEmailEl.value.trim() : "";
            const password = authPasswordEl ? authPasswordEl.value : "";

            const originalBtnText = submitAuthBtn ? submitAuthBtn.textContent : "Submit";
            if (submitAuthBtn) {
                submitAuthBtn.disabled = true;
                submitAuthBtn.textContent = isSignUpMode ? "Registering..." : "Authenticating...";
            }

            if (!isSupabaseReady) {
                alert("Authentication service is currently unavailable. Please check your connection.");
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
                    // Check if email already exists
                    const { data: existingUsers, error: checkError } = await supabase
                        .from("users")
                        .select("id")
                        .eq("email", email);

                    if (checkError) throw checkError;

                    if (existingUsers && existingUsers.length > 0) {
                        alert("❌ This email address is already registered.");
                        return;
                    }

                    // Hash Password client-side using bcryptjs
                    const salt = bcryptLib.genSaltSync(8);
                    const hashedPassword = bcryptLib.hashSync(password, salt);

                    // Write User Record to Supabase
                    const { error: insertError } = await supabase
                        .from("users")
                        .insert([{ name, email, password: hashedPassword }]);

                    if (insertError) throw insertError;

                    authForm.reset();
                    if (modalContentForm) modalContentForm.style.display = "none";
                    if (modalContentNotice) modalContentNotice.style.display = "block";

                    if (modalIcon) modalIcon.innerHTML = "✅";
                    if (modalTitle) {
                        modalTitle.textContent = "Registered Successfully";
                        modalTitle.style.color = "#22c55e";
                    }
                    if (modalMessage) modalMessage.innerHTML = "Your account has been created. You can now Log In.";
                    openModal();
                    setAuthMode(false);

                } else {
                    // Check if email exists
                    const { data: users, error: queryError } = await supabase
                        .from("users")
                        .select("*")
                        .eq("email", email);

                    if (queryError) throw queryError;

                    if (!users || users.length === 0) {
                        alert("❌ Invalid email matching profile signature or wrong password.");
                        return;
                    }

                    const user = users[0];

                    // Compare Passwords
                    let passwordMatch = false;
                    if (user.password.startsWith("$2a$") || user.password.startsWith("$2b$")) {
                        passwordMatch = bcryptLib.compareSync(password, user.password);
                    } else {
                        passwordMatch = (password === user.password);
                    }

                    if (!passwordMatch) {
                        alert("❌ Invalid email matching profile signature or wrong password.");
                        return;
                    }

                    // Success Authenticated Session
                    isLoggedIn = true;
                    localStorage.setItem("isLoggedIn", "true");
                    localStorage.setItem("userEmail", user.email);
                    localStorage.setItem("userName", user.name || getNameFromEmail(user.email));
                    localStorage.setItem("authProvider", "email");

                    updateLoginButton();
                    authForm.reset();

                    if (modalContentForm) modalContentForm.style.display = "none";
                    if (modalContentNotice) modalContentNotice.style.display = "block";

                    if (modalIcon) modalIcon.innerHTML = "✅";
                    if (modalTitle) {
                        modalTitle.textContent = "Login Successful";
                        modalTitle.style.color = "#22c55e";
                    }
                    if (modalMessage) modalMessage.innerHTML = "You can now access AI Resume Builder and AI Career Guidance.";
                    openModal();
                }
            } catch (err) {
                console.error("Database Auth Error:", err);
                alert("❌ An error occurred: " + (err.message || "Unknown database validation issue."));
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
                showDeniedModal("AI Resume Builder ni access cheyyalante First Login kani Signup kani avvali.");
            } else {
                window.location.href = "builder.html";
            }
        });
    }

    // Career Guidance Router Link
    if (goToGuidance) {
        goToGuidance.addEventListener("click", () => {
            if (!isLoggedIn) {
                showDeniedModal("AI Career Guidance system ni access cheyyalante First Login kani Signup kani avvali.");
            } else {
                window.location.href = "guidance.html";
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
window.openPreviewFromScript = async function(index) {
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
