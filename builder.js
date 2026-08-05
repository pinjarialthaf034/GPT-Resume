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

    // Initialize page features
    initializeBuilderPage();
});

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
                
                if (templateId === "Senior Project Manager") {
                    window.location.href = "templates/seniorprojectmanager.html";
                    return;
                }

                if (templateId === "Facility Property Manager" || templateId === "facility_property_manager") {
                    window.location.href = "templates/facility-builder.html?template_id=facility_property_manager";
                } else if (templateId === "PhotoGrapher" || templateId === "photographer") {
                    window.location.href = "templates/Photographer.html?template_id=photographer";
                } else if (templateId === "Marketing Manager" || templateId === "marketing_manager") {
                    window.location.href = "templates/marketing-builder.html?template_id=marketing_manager";
                } else if (templateId === "Project Manager" || templateId === "project_manager") {
                    window.location.href = "templates/project-manager.html?template_id=project_manager";
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
                if (card.getAttribute("data-template-id") === "Senior Project Manager") {
                    window.location.href = "templates/seniorprojectmanager.html";
                    return;
                }
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