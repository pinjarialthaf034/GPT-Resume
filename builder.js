// Auth Route Guard: Verify login session before page initialization
document.addEventListener("DOMContentLoaded", async () => {
    const supabase = window.supabase;
    let isLoggedIn = false;
    let userEmail = "";
    let userName = "";
    let userAvatar = "";
    let provider = "email";

    if (supabase && typeof supabase.auth !== 'undefined') {
        try {
            // Wait for Supabase to resolve the session
            const { data: { session }, error } = await supabase.auth.getSession();
            if (session && session.user) {
                isLoggedIn = true;
                const userObj = session.user;
                const metadata = userObj.user_metadata || {};
                userEmail = userObj.email;
                userName = metadata.full_name || metadata.name || (userObj.email ? userObj.email.split('@')[0] : "User");
                provider = userObj.app_metadata?.provider || (userObj.identities && userObj.identities[0]?.provider) || 'email';
                userAvatar = metadata.avatar_url || "";

                localStorage.setItem("isLoggedIn", "true");
                localStorage.setItem("userEmail", userEmail);
                localStorage.setItem("userName", userName);
                localStorage.setItem("authProvider", provider);
                if (userAvatar) {
                    localStorage.setItem("userAvatar", userAvatar);
                } else {
                    localStorage.removeItem("userAvatar");
                }
            }
        } catch (err) {
            console.error("Auth session retrieval error:", err);
        }
    }

    // Check localStorage fallback if Supabase check bypassed
    if (!isLoggedIn) {
        isLoggedIn = localStorage.getItem("isLoggedIn") === "true";
        userEmail = localStorage.getItem("userEmail") || "";
        userName = localStorage.getItem("userName") || "";
        userAvatar = localStorage.getItem("userAvatar") || "";
        provider = localStorage.getItem("authProvider") || "email";
    }

    if (!isLoggedIn) {
        // Silently redirect back without alert boxes
        window.location.href = "index.html";
        return;
    }

    // Populate header badge inside builder page
    updateBuilderHeaderBadge(userName, userEmail, userAvatar, provider, supabase);

    // Initialize page features
    initializeBuilderPage();
});

// Helper to extract 2-letter initials
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

// Render clean avatar display and Sign Out button next to it (NO dropdown list)
function updateBuilderHeaderBadge(userName, userEmail, userAvatar, provider, supabase) {
    const builderNavActions = document.getElementById("builderNavActions");
    if (!builderNavActions) return;

    let avatarHtml = "";
    if (userAvatar) {
        avatarHtml = `<img src="${userAvatar}" alt="Profile" class="user-avatar-img">`;
    } else {
        const initials = getInitials(userName, userEmail);
        avatarHtml = `<span class="user-avatar-initials">${initials}</span>`;
    }

    let uploadHtml = "";
    if (provider !== "google") {
        uploadHtml = `
            <input type="file" id="builderAvatarUploadInput" accept="image/*" style="display:none;">
            <button type="button" class="btn-login" style="background:rgba(56, 189, 248, 0.15); color:var(--accent-blue); border:1px solid rgba(56, 189, 248, 0.4); margin-right:10px; font-size:12px; padding:6px 12px;" id="builderUploadAvatarBtn">Upload Photo</button>
        `;
    }

    builderNavActions.innerHTML = `
        <div style="display:flex; align-items:center; gap:10px;">
            ${uploadHtml}
            <div class="user-avatar-circle" style="cursor:default;">
                ${avatarHtml}
            </div>
            <button class="btn-login" id="builderSignOutBtn" style="background:#ef4444; color:#fff; font-size:13px; padding:8px 16px;">Sign Out</button>
        </div>
    `;

    // Sign out logic
    const builderSignOutBtn = document.getElementById("builderSignOutBtn");
    if (builderSignOutBtn) {
        builderSignOutBtn.addEventListener("click", async (e) => {
            e.stopPropagation();
            localStorage.removeItem("isLoggedIn");
            localStorage.removeItem("userEmail");
            localStorage.removeItem("userName");
            localStorage.removeItem("userAvatar");
            localStorage.removeItem("authProvider");
            if (supabase && typeof supabase.auth !== 'undefined') {
                try {
                    await supabase.auth.signOut();
                } catch (err) {
                    console.error("Sign out error:", err);
                }
            }
            window.location.href = "index.html";
        });
    }

    // Avatar upload triggers
    const builderUploadAvatarBtn = document.getElementById("builderUploadAvatarBtn");
    const builderAvatarUploadInput = document.getElementById("builderAvatarUploadInput");
    if (builderUploadAvatarBtn && builderAvatarUploadInput) {
        builderUploadAvatarBtn.addEventListener("click", (e) => {
            e.stopPropagation();
            builderAvatarUploadInput.click();
        });
    }

    if (builderAvatarUploadInput) {
        builderAvatarUploadInput.addEventListener("change", async (e) => {
            e.stopPropagation();
            const file = e.target.files[0];
            if (!file) return;

            try {
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

                try {
                    await supabase.auth.updateUser({
                        data: { avatar_url: publicUrl }
                    });
                } catch (metaErr) {
                    console.warn("Could not save avatar url to Supabase user metadata:", metaErr);
                }

                localStorage.setItem("userAvatar", publicUrl);
                updateBuilderHeaderBadge(userName, userEmail, publicUrl, provider, supabase);
                alert("Profile photo updated successfully!");

            } catch (err) {
                console.error("Avatar upload issue:", err);
                alert("Failed to process photo upload: " + err.message);
            }
        });
    }
}

function initializeBuilderPage() {
    const headshotFilter = document.getElementById("headshotFilter");
    const graphicsFilter = document.getElementById("graphicsFilter");
    const columnsFilter = document.getElementById("columnsFilter");
    const experienceFilter = document.getElementById("experienceFilter");

    if (headshotFilter) headshotFilter.addEventListener("change", filterTemplates);
    if (graphicsFilter) graphicsFilter.addEventListener("change", filterTemplates);
    if (columnsFilter) columnsFilter.addEventListener("change", filterTemplates);
    if (experienceFilter) experienceFilter.addEventListener("change", filterTemplates);

    function filterTemplates() {
        const headshot = headshotFilter.value;
        const graphics = graphicsFilter.value;
        const columns = columnsFilter.value;
        const experience = experienceFilter.value;

        document.querySelectorAll(".template-card").forEach(card => {
            let show = true;
            if (headshot && card.dataset.headshot !== headshot) show = false;
            if (graphics && card.dataset.graphics !== graphics) show = false;
            if (columns && card.dataset.columns !== columns) show = false;
            if (experience && card.dataset.experience !== experience) show = false;
            card.style.display = show ? "block" : "none";
        });
    }

    const cards = document.querySelectorAll(".template-card");
    const modal = document.getElementById("previewModal");
    const previewImage = document.getElementById("previewImage");
    const title = document.getElementById("templateTitle");
    const featureList = document.getElementById("templateFeatures");
    let current = 0;

    async function openPreview(index) {
        current = index;
        const card = cards[current];
        if (previewImage && card) {
            const img = card.querySelector(".resume-preview img");
            if (img) previewImage.src = img.src;
        }
        if (title && card) {
            title.textContent = card.dataset.name || (card.querySelector("h3") ? card.querySelector("h3").textContent : "");
        }
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

        if (modal) modal.style.display = "flex";
    }

    cards.forEach((card, index) => {
        card.addEventListener("click", function (e) {
            if (e.target.classList.contains("choose-btn")) {
                e.stopPropagation();
                const templateId = card.getAttribute("data-template-id");
                if (templateId === "Facility Property Manager" || templateId === "facility_property_manager") {
                    window.location.href = "templates/facility-builder.html?template_id=facility_property_manager";
                } else if (templateId === "PhotoGrapher" || templateId === "photographer") {
                    window.location.href = "templates/Photographer.html?template_id=photographer";
                }
                return;
            }
            openPreview(index);
        });
    });

    const closePreviewBtn = document.querySelector(".close-preview");
    if (closePreviewBtn) {
        closePreviewBtn.onclick = function () {
            if (modal) modal.style.display = "none";
        };
    }

    const prevBtn = document.querySelector(".prev");
    if (prevBtn) {
        prevBtn.onclick = function () {
            current--;
            if (current < 0) current = cards.length - 1;
            openPreview(current);
        };
    }

    const nextBtn = document.querySelector(".next");
    if (nextBtn) {
        nextBtn.onclick = function () {
            current++;
            if (current >= cards.length) current = 0;
            openPreview(current);
        };
    }

    window.onclick = function (e) {
        if (e.target === modal) {
            if (modal) modal.style.display = "none";
        }
    };

    document.addEventListener("keydown", function (e) {
        if (e.key === "Escape") {
            if (modal) modal.style.display = "none";
        }
    });

    const chooseTemplateBtn = document.getElementById("chooseTemplateBtn");
    if (chooseTemplateBtn) {
        chooseTemplateBtn.onclick = function () {
            const card = cards[current];
            if (card) {
                const btn = card.querySelector(".choose-btn");
                if (btn) btn.click();
            }
        };
    }

    const backBtn = document.querySelector(".back-btn");
    if (backBtn) {
        backBtn.addEventListener("click", () => {
            window.location.href = "index.html";
        });
    }
}