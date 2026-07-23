// ==========================================
// TEMPLATE METADATA REGISTRATION
// ==========================================
const templateMetadata = {
    id: "photographer",
    name: "Photo Grapher",
    hasPhoto: true,
    sections: ["contact", "summary", "education", "assistant", "skills", "experience"]
};

// ==========================================
// RESUME STATE & DEFAULT DATA DEFINITION
// ==========================================
let photographer_resume_data = {
    name: "",
    role: "",
    phone: "",
    email: "",
    linkedin: "",
    address: "",
    summary: "",
    assistant: "",
    experience: [],
    education: [],
    skills: [],
    accentTheme: "deep-blue",
    fontFace: "Segoe UI"
};

// ==========================================
// INITIAL EVENT HANDLERS BINDINGS
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
    // 1. Text Inputs Binding
    document.getElementById("nameInput").addEventListener("input", (e) => { photographer_resume_data.name = e.target.value; renderPreview(); triggerAutosave(); });
    document.getElementById("roleInput").addEventListener("input", (e) => { photographer_resume_data.role = e.target.value; renderPreview(); triggerAutosave(); });
    document.getElementById("phoneInput").addEventListener("input", (e) => { photographer_resume_data.phone = e.target.value; renderPreview(); triggerAutosave(); });
    document.getElementById("emailInput").addEventListener("input", (e) => { photographer_resume_data.email = e.target.value; renderPreview(); triggerAutosave(); });
    document.getElementById("linkedinInput").addEventListener("input", (e) => { photographer_resume_data.linkedin = e.target.value; renderPreview(); triggerAutosave(); });
    document.getElementById("addressInput").addEventListener("input", (e) => { photographer_resume_data.address = e.target.value; renderPreview(); triggerAutosave(); });
    document.getElementById("summaryInput").addEventListener("input", (e) => { photographer_resume_data.summary = e.target.value; renderPreview(); triggerAutosave(); });
    document.getElementById("assistantInput").addEventListener("input", (e) => { photographer_resume_data.assistant = e.target.value; renderPreview(); triggerAutosave(); });

    document.getElementById("skillsInput").addEventListener("input", (e) => {
        photographer_resume_data.skills = e.target.value.split(",").map(s => s.trim()).filter(s => s !== "");
        renderPreview();
        triggerAutosave();
    });

    // 2. Photo Upload Binding
    const photoInput = document.getElementById("photoInput");
    if (photoInput) {
        photoInput.addEventListener("change", (e) => {
            const file = e.target.files[0];
            if (file) {
                const imageURL = URL.createObjectURL(file);
                document.getElementById("previewPhoto").src = imageURL;
            }
        });
    }

    // 3. Repeatable Fields Buttons Bindings
    document.getElementById("addExperienceBtn").addEventListener("click", () => {
        photographer_resume_data.experience.push({
            id: "exp-" + Date.now(),
            title: "",
            company: "",
            dates: "",
            desc: ""
        });
        renderExperienceCards();
        renderPreview();
        triggerAutosave();
    });

    document.getElementById("addEducationBtn").addEventListener("click", () => {
        photographer_resume_data.education.push({
            id: "edu-" + Date.now(),
            degree: "",
            institution: "",
            dates: "",
            desc: ""
        });
        renderEducationCards();
        renderPreview();
        triggerAutosave();
    });

    // 4. Customizer Theme Swatches binding
    const swatches = document.querySelectorAll(".color-swatch");
    swatches.forEach(swatch => {
        swatch.addEventListener("click", () => {
            swatches.forEach(s => s.classList.remove("active"));
            swatch.classList.add("active");
            const color = swatch.getAttribute("data-color");
            applyHeaderColor(color);
        });
    });

    // 5. Customizer Font Switcher binding
    const fontSelector = document.getElementById("fontSelector");
    if (fontSelector) {
        fontSelector.addEventListener("change", (e) => {
            const font = e.target.value;
            applyFont(font);
        });
    }

    // 6. Stepper Circle Clicks for Direct Navigation
    const stepNodes = document.querySelectorAll(".step-node");
    stepNodes.forEach(node => {
        node.addEventListener("click", () => {
            const stepNum = parseInt(node.getAttribute("data-step"));
            jumpToStep(stepNum);
        });
    });

    // 7. AI Tools Bindings
    document.getElementById("aiGenerateSummaryBtn").addEventListener("click", handleAISummary);
    document.getElementById("aiSuggestAssistantBulletsBtn").addEventListener("click", handleAIAssistant);

    // Skill Chips Click Bindings (Preventing Duplicates)
    document.querySelectorAll(".skill-chip").forEach(chip => {
        chip.addEventListener("click", () => {
            const skillName = chip.getAttribute("data-skill").trim();
            const normalizedSkills = photographer_resume_data.skills.map(s => s.trim().toLowerCase());

            if (!normalizedSkills.includes(skillName.toLowerCase())) {
                photographer_resume_data.skills.push(skillName);
                document.getElementById("skillsInput").value = photographer_resume_data.skills.join(", ");
                renderPreview();
                triggerAutosave();
            }
        });
    });

    // Load drafts or defaults
    loadSavedResume().then(() => {
        if (!photographer_resume_data.experience.length && !photographer_resume_data.education.length) {
            loadSampleData();
        } else {
            syncStateToForm();
            renderExperienceCards();
            renderEducationCards();
            renderPreview();
        }
    });

    updateStepperUI();
});

// ==========================================
// TOAST NOTIFICATIONS UTILITY
// ==========================================
function showToast(message, type = "info") {
    const container = document.getElementById("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${type}`;

    let icon = "fa-info-circle";
    if (type === "warning") icon = "fa-exclamation-triangle";
    else if (type === "error") icon = "fa-times-circle";
    else if (type === "success") icon = "fa-check-circle";

    toast.innerHTML = `<i class="fa-solid ${icon}"></i> <span>${message}</span>`;
    container.appendChild(toast);

    // Trigger transition
    toast.offsetHeight;
    toast.classList.add("show");

    setTimeout(() => {
        toast.classList.remove("show");
        setTimeout(() => toast.remove(), 300);
    }, 4500);
}

// ==========================================
// DYNAMIC COMPONENT RENDER ENGINE
// ==========================================
function renderPreview() {
    // 1. Contact info
    document.getElementById("previewName").textContent = photographer_resume_data.name || "Full Name";
    document.getElementById("previewRole").textContent = photographer_resume_data.role || "Job Role";
    document.getElementById("previewPhone").textContent = photographer_resume_data.phone || "Phone";
    document.getElementById("previewEmail").textContent = photographer_resume_data.email || "Email";
    document.getElementById("previewLinkedin").textContent = photographer_resume_data.linkedin || "LinkedIn";
    document.getElementById("previewAddress").textContent = photographer_resume_data.address || "Address";

    // 2. Summary
    document.getElementById("previewSummary").textContent = photographer_resume_data.summary || "Summary";

    // 3. Assistant Highlights
    const previewAssistant = document.getElementById("previewAssistant");
    if (previewAssistant) {
        if (photographer_resume_data.assistant) {
            const lines = photographer_resume_data.assistant.split("\n").filter(l => l.trim() !== "");
            previewAssistant.innerHTML = "<ul>" + lines.map(line => `<li>${line.replace(/^[•\-\*]\s*/, '')}</li>`).join("") + "</ul>";
        } else {
            previewAssistant.innerHTML = "Assistant details.";
        }
    }

    // 4. Education (Dynamic list)
    const eduPreview = document.getElementById("previewEducation");
    eduPreview.innerHTML = "";
    if (photographer_resume_data.education.length > 0) {
        photographer_resume_data.education.forEach(edu => {
            const item = document.createElement("div");
            item.className = "preview-item";

            let descHtml = "";
            if (edu.desc) {
                descHtml = `<div class="preview-item-desc">${edu.desc}</div>`;
            }

            item.innerHTML = `
                <div class="preview-item-header">
                    <span class="preview-item-title">${edu.degree || "Degree / Certificate"}</span>
                    <span class="preview-item-meta">${edu.dates || "Dates"}</span>
                </div>
                <div class="preview-item-org-row">
                    <span class="preview-item-org">${edu.institution || "Institution / School"}</span>
                </div>
                ${descHtml}
            `;
            eduPreview.appendChild(item);
        });
    } else {
        eduPreview.innerHTML = "Education details.";
    }

    // 5. Skills (Exploded inline tags list)
    const skillsList = document.getElementById("previewSkills");
    skillsList.innerHTML = "";
    if (photographer_resume_data.skills.length > 0) {
        photographer_resume_data.skills.forEach(skill => {
            if (skill.trim() !== "") {
                const li = document.createElement("li");
                li.textContent = "• " + skill.trim();
                skillsList.appendChild(li);
            }
        });
    }

    // 6. Experience (Dynamic list)
    const expPreview = document.getElementById("previewExperience");
    expPreview.innerHTML = "";
    if (photographer_resume_data.experience.length > 0) {
        photographer_resume_data.experience.forEach(exp => {
            const item = document.createElement("div");
            item.className = "preview-item";

            let bulletsHtml = "";
            if (exp.desc) {
                const lines = exp.desc.split("\n").filter(l => l.trim() !== "");
                bulletsHtml = "<div class=\"preview-item-desc\"><ul>" + lines.map(line => `<li>${line.replace(/^[•\-\*]\s*/, '')}</li>`).join("") + "</ul></div>";
            }

            item.innerHTML = `
                <div class="preview-item-header">
                    <span class="preview-item-title">${exp.title || "Job Title"}</span>
                    <span class="preview-item-meta">${exp.dates || "Dates"}</span>
                </div>
                <div class="preview-item-org-row">
                    <span class="preview-item-org">${exp.company || "Company / Organization"}</span>
                </div>
                ${bulletsHtml}
            `;
            expPreview.appendChild(item);
        });
    } else {
        expPreview.innerHTML = "Experience details.";
    }
}

function renderExperienceCards() {
    const container = document.getElementById("experienceContainer");
    container.innerHTML = "";
    photographer_resume_data.experience.forEach((exp, index) => {
        const card = document.createElement("div");
        card.className = "repeatable-card";
        card.innerHTML = `
            <div class="repeatable-card-header">
                <span class="repeatable-card-title">Experience #${index + 1}</span>
                <button type="button" class="card-delete-btn" onclick="deleteExperience('${exp.id}')">Delete</button>
            </div>
            <div class="row-2">
                <div class="input-group">
                    <label>Job Title</label>
                    <input type="text" id="exp-title-${exp.id}" value="${exp.title || ''}" placeholder="e.g. Lead Photographer" oninput="updateExperience('${exp.id}', 'title', this.value)">
                </div>
                <div class="input-group">
                    <label>Company / Organization</label>
                    <input type="text" id="exp-company-${exp.id}" value="${exp.company || ''}" placeholder="e.g. Studio Vista" oninput="updateExperience('${exp.id}', 'company', this.value)">
                </div>
            </div>
            <div class="input-group">
                <label>Start & End Dates / Year</label>
                <input type="text" value="${exp.dates || ''}" placeholder="e.g. 2018 - Present" oninput="updateExperience('${exp.id}', 'dates', this.value)">
            </div>
            <div class="input-group">
                <label>Description / Bullet Points</label>
                <div class="textarea-ai-wrapper">
                    <textarea id="exp-desc-${exp.id}" placeholder="• Accomplishment 1&#10;• Accomplishment 2" style="height: 80px;" oninput="updateExperience('${exp.id}', 'desc', this.value)">${exp.desc || ''}</textarea>
                    <button type="button" id="ai-btn-${exp.id}" class="btn-ai-action" onclick="handleAIExperience('${exp.id}')">✨ AI Suggest Action Bullets</button>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

function renderEducationCards() {
    const container = document.getElementById("educationContainer");
    container.innerHTML = "";
    photographer_resume_data.education.forEach((edu, index) => {
        const card = document.createElement("div");
        card.className = "repeatable-card";
        card.innerHTML = `
            <div class="repeatable-card-header">
                <span class="repeatable-card-title">Education #${index + 1}</span>
                <button type="button" class="card-delete-btn" onclick="deleteEducation('${edu.id}')">Delete</button>
            </div>
            <div class="row-2">
                <div class="input-group">
                    <label>Title / Degree</label>
                    <input type="text" value="${edu.degree || ''}" placeholder="e.g. Bachelor of Fine Arts" oninput="updateEducation('${edu.id}', 'degree', this.value)">
                </div>
                <div class="input-group">
                    <label>Company / Institution</label>
                    <input type="text" value="${edu.institution || ''}" placeholder="e.g. Academy of Art" oninput="updateEducation('${edu.id}', 'institution', this.value)">
                </div>
            </div>
            <div class="input-group">
                <label>Dates / Year</label>
                <input type="text" value="${edu.dates || ''}" placeholder="e.g. 2012 - 2016" oninput="updateEducation('${edu.id}', 'dates', this.value)">
            </div>
            <div class="input-group">
                <label>Description / Details</label>
                <textarea placeholder="Specialized in portrait and lighting styles..." style="height: 60px;" oninput="updateEducation('${edu.id}', 'desc', this.value)">${edu.desc || ''}</textarea>
            </div>
        `;
        container.appendChild(card);
    });
}

// ==========================================
// FORM STATE UPDATERS & SYNC
// ==========================================
window.updateExperience = function (id, field, value) {
    const exp = photographer_resume_data.experience.find(e => e.id === id);
    if (exp) {
        exp[field] = value;
        renderPreview();
        triggerAutosave();
    }
};

window.deleteExperience = function (id) {
    photographer_resume_data.experience = photographer_resume_data.experience.filter(e => e.id !== id);
    renderExperienceCards();
    renderPreview();
    triggerAutosave();
};

window.updateEducation = function (id, field, value) {
    const edu = photographer_resume_data.education.find(e => e.id === id);
    if (edu) {
        edu[field] = value;
        renderPreview();
        triggerAutosave();
    }
};

window.deleteEducation = function (id) {
    photographer_resume_data.education = photographer_resume_data.education.filter(e => e.id !== id);
    renderEducationCards();
    renderPreview();
    triggerAutosave();
};

function syncStateToForm() {
    document.getElementById("nameInput").value = photographer_resume_data.name || "";
    document.getElementById("roleInput").value = photographer_resume_data.role || "";
    document.getElementById("phoneInput").value = photographer_resume_data.phone || "";
    document.getElementById("emailInput").value = photographer_resume_data.email || "";
    document.getElementById("linkedinInput").value = photographer_resume_data.linkedin || "";
    document.getElementById("addressInput").value = photographer_resume_data.address || "";
    document.getElementById("summaryInput").value = photographer_resume_data.summary || "";
    document.getElementById("assistantInput").value = photographer_resume_data.assistant || "";
    document.getElementById("skillsInput").value = photographer_resume_data.skills.join(", ");
}

// ==========================================
// LIVE LLM API CONNECTION LOGIC
// ==========================================
async function callLiveAPI(promptText) {
    // 1. ఇక్కడ మీ Google Gemini API Key పెట్టండి
    const GEMINI_API_KEY = "";

    // మోడల్ నేమ్ ని స్థిరమైన 'gemini-2.0-flash' కి మార్చాం
    const endpoint = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=${GEMINI_API_KEY}`;

    const response = await fetch(endpoint, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            contents: [{
                parts: [{ text: "You are a professional resume writer specializing in high-impact photography portfolios. " + promptText }]
            }]
        })
    });

    if (!response.ok) {
        const err = await response.json();
        throw new Error(`Gemini API Error: ${err.error?.message || response.statusText}`);
    }

    const data = await response.json();

    if (data.candidates && data.candidates[0] && data.candidates[0].content) {
        return data.candidates[0].content.parts[0].text.trim();
    }

    throw new Error("Invalid response format from Gemini API");
}

// ==========================================
// BUTTON SPINNER UTILITY wrapper
// ==========================================
async function executeWithLoadingState(buttonEl, asyncAction) {
    if (!buttonEl || buttonEl.classList.contains("loading")) return;

    const originalHtml = buttonEl.innerHTML;
    buttonEl.classList.add("loading");
    buttonEl.disabled = true;
    buttonEl.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Processing with AI...`;

    try {
        await asyncAction();
    } finally {
        buttonEl.classList.remove("loading");
        buttonEl.disabled = false;
        buttonEl.innerHTML = originalHtml;
    }
}
// ==========================================
// SMART CONTEXT-AWARE AI CHATGPT TRIGGERS
// ==========================================
async function handleAISummary() {
    const button = document.getElementById("aiGenerateSummaryBtn");
    const summaryInput = document.getElementById("summaryInput");
    const userText = summaryInput.value.trim();

    await executeWithLoadingState(button, async () => {
        const name = photographer_resume_data.name || "Rufus Stewart";
        const role = photographer_resume_data.role || "Photographer";
        const skills = photographer_resume_data.skills.join(", ") || "Studio Lighting, Adobe Lightroom";
        const expDetails = photographer_resume_data.experience.map(e => `${e.title} at ${e.company} (${e.dates}): ${e.desc}`).filter(t => t.trim()).join("; ");

        try {
            let result = "";
            if (userText !== "") {
                // Enhance Prompt
                const prompt = `You are a professional resume editor. Rewrite and polish this photographer summary to make it compelling, high-impact, and articulate without adding false details.
Context:
Name: ${name}
Job Role: ${role}
Skills: ${skills}
Experience: ${expDetails}

Draft Summary to Enhance:
"${userText}"`;
                result = await callLiveAPI(prompt);
                showToast("Summary enhanced successfully via OpenAI GPT!", "success");
            } else {
                // Generate Prompt
                const prompt = `You are a professional resume writer. Generate a unique, tailored, highly professional resume summary (maximum of 3 sentences) for a Photographer named ${name} specializing in ${skills} (${role}) with experience in ${expDetails}. Focus on visual storytelling, lighting expertise, and client engagement. Return only the final summary text without placeholders.`;
                result = await callLiveAPI(prompt);
                showToast("Fresh summary generated via OpenAI GPT!", "success");
            }
            summaryInput.value = result;
            photographer_resume_data.summary = result;
            renderPreview();
            triggerAutosave();
        } catch (error) {
            console.error("OpenAI API Failure:", error);
            showToast(`API Failed: ${error.message}`, "error");
        }
    });
}

async function handleAIAssistant() {
    const button = document.getElementById("aiSuggestAssistantBulletsBtn");
    const input = document.getElementById("assistantInput");
    const userText = input.value.trim();

    await executeWithLoadingState(button, async () => {
        const name = photographer_resume_data.name || "Rufus Stewart";
        const role = photographer_resume_data.role || "Photographer";
        const skills = photographer_resume_data.skills.join(", ") || "Studio Lighting, Adobe Lightroom";

        try {
            let result = "";
            if (userText !== "") {
                // Enhance bullets
                const prompt = `You are an expert resume writer. Rewrite and polish these photographer assistant bullet points into professional accomplishments, maintaining raw bullet formatting:
Context:
Name: ${name}
Role: ${role}
Skills: ${skills}

Draft Bullet Points to Enhance:
\n${userText}`;
                result = await callLiveAPI(prompt);
                showToast("Assistant bullets enhanced successfully via OpenAI GPT!", "success");
            } else {
                // Generate bullets
                const prompt = `You are an expert resume writer. Generate 3 unique, high-impact action bullet points using strong action verbs for an Event Photography Assistant role. Context: Name: ${name}, Role: ${role}, Skills: ${skills}. Focus on photography workflows, lighting, post-processing, and client relations. Prefix with a bullet mark (•). Do not include any introduction.`;
                result = await callLiveAPI(prompt);
                showToast("Fresh assistant bullets generated via OpenAI GPT!", "success");
            }
            input.value = result;
            photographer_resume_data.assistant = result;
            renderPreview();
            triggerAutosave();
        } catch (error) {
            console.error("OpenAI API Failure:", error);
            showToast(`API Failed: ${error.message}`, "error");
        }
    });
}

window.handleAIExperience = async function (id) {
    const button = document.getElementById(`ai-btn-${id}`);
    const input = document.getElementById(`exp-desc-${id}`);
    const userText = input.value.trim();

    await executeWithLoadingState(button, async () => {
        const exp = photographer_resume_data.experience.find(e => e.id === id);
        if (exp) {
            const name = photographer_resume_data.name || "Rufus Stewart";
            const role = photographer_resume_data.role || "Photographer";
            const skills = photographer_resume_data.skills.join(", ") || "Studio Lighting, Adobe Lightroom";
            const jobTitle = exp.title || "Photographer";
            const company = exp.company || "Creative Agency";

            try {
                let result = "";
                if (userText !== "") {
                    // Enhance bullets
                    const prompt = `You are an expert resume writer. Rewrite and polish these professional experience bullet points to elevate their impact, starting with strong action verbs:
Context:
Job Title: ${jobTitle} at ${company}
Resume Owner Name: ${name}
Core Role: ${role}
Skills: ${skills}

Draft Bullet Points to Enhance:
\n${userText}`;
                    result = await callLiveAPI(prompt);
                    showToast("Accomplishment bullets enhanced successfully via OpenAI GPT!", "success");
                } else {
                    // Generate bullets
                    const prompt = `You are an expert resume writer. Generate 3 unique, high-impact action bullet points using strong action verbs for a ${jobTitle} at ${company} focusing on photography workflows, lighting, post-processing, and client relations. Context: Name: ${name}, Skills: ${skills}. Prefix with bullet marks (•).`;
                    result = await callLiveAPI(prompt);
                    showToast("Fresh experience bullets generated via OpenAI GPT!", "success");
                }
                exp.desc = result;
                input.value = result;
                renderExperienceCards();
                renderPreview();
                triggerAutosave();
            } catch (error) {
                console.error("OpenAI API Failure:", error);
                showToast(`API Failed: ${error.message}`, "error");
            }
        }
    });
};

// ==========================================
// LIVE CUSTOMIZER TOOLBAR OPTIONS
// ==========================================
function applyHeaderColor(colorName) {
    let hex = "#243447"; // deep blue (default)
    if (colorName === "charcoal") hex = "#1f2937";
    else if (colorName === "royal-navy") hex = "#1e3a8a";
    else if (colorName === "emerald") hex = "#0f766e";
    else if (colorName === "wine-red") hex = "#881337";

    const header = document.getElementById("resumeHeader");
    if (header) {
        header.style.setProperty('--header-bg', hex);
    }

    photographer_resume_data.accentTheme = colorName;
    triggerAutosave();
}

function applyFont(fontName) {
    const preview = document.getElementById("resume-pdf-target");
    if (preview) {
        preview.style.fontFamily = fontName;
        preview.querySelectorAll("*").forEach(el => {
            el.style.fontFamily = fontName;
        });
    }
    photographer_resume_data.fontFace = fontName;
    triggerAutosave();
}

// ==========================================
// INTERACTIVE STEP ROUTING & PROGRESS BAR
// ==========================================
let currentStep = 1;
const totalSteps = 6;

window.nextStep = function () {
    if (currentStep >= totalSteps) return;
    document.getElementById("step" + currentStep).classList.remove("active");
    currentStep++;
    document.getElementById("step" + currentStep).classList.add("active");
    updateStepperUI();
    triggerAutosave();
};

window.prevStep = function () {
    if (currentStep <= 1) return;
    document.getElementById("step" + currentStep).classList.remove("active");
    currentStep--;
    document.getElementById("step" + currentStep).classList.add("active");
    updateStepperUI();
};

window.jumpToStep = function (stepNum) {
    if (stepNum < 1 || stepNum > totalSteps) return;
    document.getElementById("step" + currentStep).classList.remove("active");
    currentStep = stepNum;
    document.getElementById("step" + currentStep).classList.add("active");
    updateStepperUI();
};

function updateStepperUI() {
    const progressFill = document.getElementById("stepperProgressFill");
    const percent = ((currentStep - 1) / 5) * 100;
    progressFill.style.width = percent + "%";

    const steps = document.querySelectorAll(".step-node");
    steps.forEach(node => {
        const stepNum = parseInt(node.getAttribute("data-step"));
        if (stepNum === currentStep) {
            node.classList.add("active");
            node.classList.remove("completed");
        } else if (stepNum < currentStep) {
            node.classList.remove("active");
            node.classList.add("completed");
        } else {
            node.classList.remove("active");
            node.classList.remove("completed");
        }
    });
}

window.finishBuild = function () {
    saveResumeToSupabase().then(() => {
        alert("🎉 Resume draft has been successfully saved to database! Returning to Templates.");
        window.location.href = "../builder.html";
    });
};

// ==========================================
// DEBOUNCED AUTOMATED SUPABASE PERSISTENCE
// ==========================================
let autosaveTimeout = null;

function triggerAutosave() {
    if (autosaveTimeout) clearTimeout(autosaveTimeout);
    autosaveTimeout = setTimeout(saveResumeToSupabase, 1000);
}

async function saveResumeToSupabase() {
    const userEmail = localStorage.getItem("userEmail");
    if (!userEmail) return;

    const supabase = window.supabase;
    if (!supabase || typeof supabase.from === 'undefined') return;

    try {
        const { error } = await supabase
            .from("resumes")
            .upsert({
                email: userEmail,
                template_id: "photographer",
                resume_data: photographer_resume_data,
                updated_at: new Date()
            }, { onConflict: ["email", "template_id"] });

        if (error) {
            console.warn("Supabase autosave check failed. Please ensure the 'resumes' table is created under your account.", error);
        } else {
            console.log("Supabase synced silently: Photographer resume draft saved.");
        }
    } catch (err) {
        console.error("Autosave database error:", err);
    }
}

async function loadSavedResume() {
    const userEmail = localStorage.getItem("userEmail");
    if (!userEmail) return;

    const supabase = window.supabase;
    if (!supabase || typeof supabase.from === 'undefined') return;

    try {
        const { data, error } = await supabase
            .from("resumes")
            .select("resume_data")
            .eq("email", userEmail)
            .eq("template_id", "photographer")
            .maybeSingle();

        if (data && data.resume_data) {
            photographer_resume_data = data.resume_data;

            // Sync customizer UI controls
            if (photographer_resume_data.accentTheme) {
                const swatch = document.querySelector(`.color-swatch[data-color="${photographer_resume_data.accentTheme}"]`);
                if (swatch) {
                    document.querySelectorAll(".color-swatch").forEach(s => s.classList.remove("active"));
                    swatch.classList.add("active");
                    applyHeaderColor(photographer_resume_data.accentTheme);
                }
            }
            if (photographer_resume_data.fontFace) {
                document.getElementById("fontSelector").value = photographer_resume_data.fontFace;
                applyFont(photographer_resume_data.fontFace);
            }

            console.log("Loaded existing photographer draft from Supabase database.");
        }
    } catch (err) {
        console.error("Supabase load error:", err);
    }
}

// ==========================================
// PRE-POPULATE DEMO DATA ENGINE
// ==========================================
function loadSampleData() {
    photographer_resume_data = {
        name: "Rufus Stewart",
        role: "Photographer",
        phone: "123-456-7890",
        email: "hello@reallygreatsite.com",
        linkedin: "www.reallygreatsite.com",
        address: "123 Anywhere Street, St., Any City",
        summary: "My name is Rufus Stewart. I am born in California on 10 oct 1991, I am a professional photographer who have been working in several different companies. I love to travel and capture stories.",
        assistant: "• Assisted photographers to capture numerous live events, including sports games, concerts, expos, and stand-up comedy\n• Monitored setup and teardown of studio equipment\n• Implemented a new system to schedule meetings with clients, which led to a 10% increase in monthly bookings",
        education: [
            {
                id: "edu-1",
                degree: "Bachelor of Art and Design",
                institution: "Borcelle University",
                dates: "2005 - 2009",
                desc: "Specialized in Creative Media and Digital Photography."
            },
            {
                id: "edu-2",
                degree: "Master of Art and Design",
                institution: "Rimberio Co",
                dates: "2012 - 2015",
                desc: "Focus on photojournalism and advanced lighting."
            }
        ],
        experience: [
            {
                id: "exp-1",
                title: "Senior Photographer",
                company: "Thynk Unlimited",
                dates: "2009 - 2014",
                desc: "• Managed photography schedules matching corporate requests."
            },
            {
                id: "exp-2",
                title: "Senior Photographer",
                company: "Fauget & Co.",
                dates: "2014 - 2016",
                desc: "• Delivered high-quality prints and handled post-production."
            }
        ],
        skills: ["Studio Lighting", "Adobe Lightroom", "Image Editing", "Font Design", "Marketing & Brand Strategy"],
        accentTheme: "deep-blue",
        fontFace: "Segoe UI"
    };

    syncStateToForm();
    renderExperienceCards();
    renderEducationCards();
    renderPreview();

    // Apply defaults to layout
    applyHeaderColor("deep-blue");
    applyFont("Segoe UI");
}

// ==========================================
// HIGH-FIDELITY PDF RENDERING EXPORT
// ==========================================
window.downloadPDF = function () {
    const element = document.getElementById("resume-pdf-target");
    const name = photographer_resume_data.name || "Resume";

    const options = {
        margin: 0,
        filename: `${name.replace(/\s+/g, '_')}_Resume.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: {
            scale: 2.5,        // Prevents text pixelation
            useCORS: true,      // Allows cross-origin photos to render safely
            letterRendering: true
        },
        jsPDF: { unit: 'px', format: [794, 1123], orientation: 'portrait' }
    };

    html2pdf().set(options).from(element).save();
};