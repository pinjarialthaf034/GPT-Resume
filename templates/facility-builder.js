// ==========================================
// TEMPLATE METADATA REGISTRATION
// ==========================================
const templateMetadata = {
    id: "facility_property_manager",
    name: "Facility Property Manager",
    hasPhoto: true,
    sidebarTheme: "orange-gradient",
    sections: ["contact", "education", "skills", "summary", "experience"]
};

// ==========================================
// RESUME STATE & DEFAULT DATA DEFINITION
// ==========================================

let resumeState = {
    name: "",
    role: "",
    phone: "",
    email: "",
    linkedin: "",
    address: "",
    summary: "",
    experience: [],
    education: [],
    skills: [],
    accentTheme: "orange",
    fontFace: "Plus Jakarta Sans"
};

// ==========================================
// INITIAL EVENT HANDLERS BINDINGS
// ==========================================

document.addEventListener("DOMContentLoaded", () => {
    // 1. Text Inputs Binding
    document.getElementById("nameInput").addEventListener("input", (e) => { resumeState.name = e.target.value; renderPreview(); triggerAutosave(); });
    document.getElementById("roleInput").addEventListener("input", (e) => { resumeState.role = e.target.value; renderPreview(); triggerAutosave(); });
    document.getElementById("phoneInput").addEventListener("input", (e) => { resumeState.phone = e.target.value; renderPreview(); triggerAutosave(); });
    document.getElementById("emailInput").addEventListener("input", (e) => { resumeState.email = e.target.value; renderPreview(); triggerAutosave(); });
    document.getElementById("linkedinInput").addEventListener("input", (e) => { resumeState.linkedin = e.target.value; renderPreview(); triggerAutosave(); });
    document.getElementById("addressInput").addEventListener("input", (e) => { resumeState.address = e.target.value; renderPreview(); triggerAutosave(); });
    document.getElementById("summaryInput").addEventListener("input", (e) => { resumeState.summary = e.target.value; renderPreview(); triggerAutosave(); });
    
    document.getElementById("skillsInput").addEventListener("input", (e) => {
        resumeState.skills = e.target.value.split(",").map(s => s.trim()).filter(s => s !== "");
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
        resumeState.experience.push({
            id: "exp-" + Date.now(),
            title: "",
            company: "",
            location: "",
            dates: "",
            desc: ""
        });
        renderExperienceCards();
        renderPreview();
        triggerAutosave();
    });

    document.getElementById("addEducationBtn").addEventListener("click", () => {
        resumeState.education.push({
            id: "edu-" + Date.now(),
            degree: "",
            institution: "",
            location: "",
            dates: ""
        });
        renderEducationCards();
        renderPreview();
        triggerAutosave();
    });

    // 4. Customizer Swatches binding
    const swatches = document.querySelectorAll(".color-swatch");
    swatches.forEach(swatch => {
        swatch.addEventListener("click", () => {
            swatches.forEach(s => s.classList.remove("active"));
            swatch.classList.add("active");
            const color = swatch.getAttribute("data-color");
            applyAccentTheme(color);
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

    // 6. AI Tools Bindings
    document.getElementById("aiGenerateSummaryBtn").addEventListener("click", generateSummaryWithAI);
    
    // Clear hardcoded skill chips and set up dynamic AI suggest button
    try {
        const suggestedChipsContainer = document.getElementById("suggestedSkillChips");
        if (suggestedChipsContainer) {
            suggestedChipsContainer.innerHTML = `<p style="font-size: 0.85rem; opacity: 0.7; font-style: italic; margin: 5px 0;">Click the button below to generate customized skills for your profile.</p>`;
        }
    } catch (err) {
        console.error("Error setting up suggested chips container:", err);
    }

    try {
        const chipsWrapper = document.querySelector(".ai-chips-wrapper");
        if (chipsWrapper) {
            const suggestBtn = document.createElement("button");
            suggestBtn.type = "button";
            suggestBtn.id = "aiSuggestSkillsBtn";
            suggestBtn.className = "btn-ai-action";
            suggestBtn.style.marginTop = "10px";
            suggestBtn.innerHTML = "✨ AI Generate Suggested Skills";
            suggestBtn.addEventListener("click", generateAISkills);
            chipsWrapper.appendChild(suggestBtn);
        }
    } catch (err) {
        console.error("Error setting up suggestBtn wrapper:", err);
    }

    // 7. PDF Export print binding
    document.getElementById("downloadPdfBtn").addEventListener("click", () => {
        window.print();
    });

    // Initialize/Load drafts or Sample data
    loadSavedResume().then(() => {
        if (!resumeState.experience.length && !resumeState.education.length) {
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
// DYNAMIC COMPONENT RENDER ENGINE
// ==========================================

function renderPreview() {
    // 1. Contact info
    document.getElementById("previewName").textContent = resumeState.name || "Full Name";
    document.getElementById("previewRole").textContent = resumeState.role || "Job Role";
    document.getElementById("previewPhone").textContent = resumeState.phone || "Phone";
    document.getElementById("previewEmail").textContent = resumeState.email || "Email";
    document.getElementById("previewLinkedin").textContent = resumeState.linkedin || "LinkedIn";
    document.getElementById("previewAddress").textContent = resumeState.address || "Address";
    
    // 2. Summary
    document.getElementById("previewSummary").textContent = resumeState.summary || "Summary";
    
    // 3. Experience
    const expList = document.getElementById("previewExperienceList");
    expList.innerHTML = "";
    resumeState.experience.forEach(exp => {
        const div = document.createElement("div");
        div.className = "preview-item";
        
        let bulletsHtml = "";
        if (exp.desc) {
            const lines = exp.desc.split("\n").filter(l => l.trim() !== "");
            bulletsHtml = "<ul>" + lines.map(line => `<li>${line.replace(/^[•\-\*]\s*/, '')}</li>`).join("") + "</ul>";
        }
        
        div.innerHTML = `
            <div class="preview-item-header">
                <span class="preview-item-title">${exp.title || "Job Title"}</span>
                <span class="preview-item-meta">${exp.dates || "Dates"}</span>
            </div>
            <div style="display:flex; justify-content:space-between; margin-top:2px;">
                <span class="preview-item-org">${exp.company || "Company"}</span>
                <span class="preview-item-meta" style="font-style: italic;">${exp.location || "Location"}</span>
            </div>
            <div class="preview-item-desc">${bulletsHtml}</div>
        `;
        expList.appendChild(div);
    });
    
    // 4. Education
    const eduList = document.getElementById("previewEducationList");
    eduList.innerHTML = "";
    resumeState.education.forEach(edu => {
        const div = document.createElement("div");
        div.className = "preview-item";
        div.innerHTML = `
            <div class="preview-item-header">
                <span class="preview-item-title" style="font-size: 11px;">${edu.degree || "Degree"}</span>
                <span class="preview-item-meta">${edu.dates || "Dates"}</span>
            </div>
            <div style="margin-top:1px;">
                <span class="preview-item-org" style="font-size: 10.5px;">${edu.institution || "Institution"}</span>
            </div>
        `;
        eduList.appendChild(div);
    });
    
    // 5. Skills
    const skillsList = document.getElementById("previewSkills");
    skillsList.innerHTML = "";
    resumeState.skills.forEach(skill => {
        if (skill.trim() !== "") {
            const li = document.createElement("li");
            li.textContent = skill.trim();
            skillsList.appendChild(li);
        }
    });
}

function renderExperienceCards() {
    const container = document.getElementById("experienceContainer");
    container.innerHTML = "";
    resumeState.experience.forEach((exp, index) => {
        const card = document.createElement("div");
        card.className = "repeatable-card";
        card.innerHTML = `
            <div class="repeatable-card-header">
                <span class="repeatable-card-title">Experience #${index + 1}</span>
                <button type="button" class="btn-delete-card" onclick="deleteExperience('${exp.id}')">Delete</button>
            </div>
            <div class="row-2">
                <div class="input-group">
                    <label>Job Title</label>
                    <input type="text" class="exp-title" value="${exp.title || ''}" placeholder="Job Title" oninput="updateExperience('${exp.id}', 'title', this.value)">
                </div>
                <div class="input-group">
                    <label>Facility / Company</label>
                    <input type="text" class="exp-company" value="${exp.company || ''}" placeholder="Company" oninput="updateExperience('${exp.id}', 'company', this.value)">
                </div>
            </div>
            <div class="row-2">
                <div class="input-group">
                    <label>Location</label>
                    <input type="text" class="exp-location" value="${exp.location || ''}" placeholder="Location" oninput="updateExperience('${exp.id}', 'location', this.value)">
                </div>
                <div class="input-group">
                    <label>Dates</label>
                    <input type="text" class="exp-dates" value="${exp.dates || ''}" placeholder="e.g. Feb 2017 - Present" oninput="updateExperience('${exp.id}', 'dates', this.value)">
                </div>
            </div>
            <div class="input-group">
                <label>Responsibilities & Achievements</label>
                <div class="textarea-ai-wrapper">
                    <textarea class="exp-desc" id="exp-desc-${exp.id}" style="height:80px;" placeholder="• Accomplishment 1&#10;• Accomplishment 2" oninput="updateExperience('${exp.id}', 'desc', this.value)">${exp.desc || ''}</textarea>
                    <button type="button" id="ai-btn-${exp.id}" class="btn-ai-action" onclick="aiSuggestBullets('${exp.id}')">✨ AI Suggest Action Bullets</button>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

function renderEducationCards() {
    const container = document.getElementById("educationContainer");
    container.innerHTML = "";
    resumeState.education.forEach((edu, index) => {
        const card = document.createElement("div");
        card.className = "repeatable-card";
        card.innerHTML = `
            <div class="repeatable-card-header">
                <span class="repeatable-card-title">Education #${index + 1}</span>
                <button type="button" class="btn-delete-card" onclick="deleteEducation('${edu.id}')">Delete</button>
            </div>
            <div class="row-2">
                <div class="input-group">
                    <label>Degree / Certificate</label>
                    <input type="text" class="edu-degree" value="${edu.degree || ''}" placeholder="Degree" oninput="updateEducation('${edu.id}', 'degree', this.value)">
                </div>
                <div class="input-group">
                    <label>Institution / School</label>
                    <input type="text" class="edu-institution" value="${edu.institution || ''}" placeholder="Institution" oninput="updateEducation('${edu.id}', 'institution', this.value)">
                </div>
            </div>
            <div class="row-2">
                <div class="input-group">
                    <label>Location</label>
                    <input type="text" class="edu-location" value="${edu.location || ''}" placeholder="Location" oninput="updateEducation('${edu.id}', 'location', this.value)">
                </div>
                <div class="input-group">
                    <label>Dates</label>
                    <input type="text" class="edu-dates" value="${edu.dates || ''}" placeholder="e.g. May 2013" oninput="updateEducation('${edu.id}', 'dates', this.value)">
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

// ==========================================
// FORM STATE SYNCHRONIZERS
// ==========================================

window.updateExperience = function(id, field, value) {
    const exp = resumeState.experience.find(e => e.id === id);
    if (exp) {
        exp[field] = value;
        renderPreview();
        triggerAutosave();
    }
};

window.deleteExperience = function(id) {
    resumeState.experience = resumeState.experience.filter(e => e.id !== id);
    renderExperienceCards();
    renderPreview();
    triggerAutosave();
};

window.updateEducation = function(id, field, value) {
    const edu = resumeState.education.find(e => e.id === id);
    if (edu) {
        edu[field] = value;
        renderPreview();
        triggerAutosave();
    }
};

window.deleteEducation = function(id) {
    resumeState.education = resumeState.education.filter(e => e.id !== id);
    renderEducationCards();
    renderPreview();
    triggerAutosave();
};

function syncStateToForm() {
    document.getElementById("nameInput").value = resumeState.name || "";
    document.getElementById("roleInput").value = resumeState.role || "";
    document.getElementById("phoneInput").value = resumeState.phone || "";
    document.getElementById("emailInput").value = resumeState.email || "";
    document.getElementById("linkedinInput").value = resumeState.linkedin || "";
    document.getElementById("addressInput").value = resumeState.address || "";
    document.getElementById("summaryInput").value = resumeState.summary || "";
    document.getElementById("skillsInput").value = resumeState.skills.join(", ");
}

// ==========================================
// ==========================================
// CORE UI LOADING STATE HELPER
// ==========================================
async function executeWithLoadingState(buttonElement, actionCallback) {
    if (!buttonElement) {
        await actionCallback();
        return;
    }
    const originalText = buttonElement.innerHTML;
    try {
        buttonElement.disabled = true;
        buttonElement.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Generating...`;
        await actionCallback();
    } catch (err) {
        console.error("Error in executeWithLoadingState:", err);
        showToast(`AI Generation failed: ${err.message}`, "error");
    } finally {
        buttonElement.disabled = false;
        buttonElement.innerHTML = originalText;
    }
}

// ==========================================
// REAL AI API CLIENT INTEGRATION
// ==========================================

async function generateSummaryWithAI() {
    const button = document.getElementById("aiGenerateSummaryBtn");
    const summaryInput = document.getElementById("summaryInput");
    if (!summaryInput) return;

    await executeWithLoadingState(button, async () => {
        try {
            const response = await fetch("http://127.0.0.1:8000/api/generate-summary", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    user_input: summaryInput.value
                })
            });

            if (!response.ok) {
                const errDetail = await response.json().catch(() => ({}));
                throw new Error(errDetail.detail || response.statusText || "Backend failure");
            }

            const data = await response.json();
            const cleanSummary = data.summary || data.text || "";
            if (cleanSummary) {
                summaryInput.value = cleanSummary;
                resumeState.summary = cleanSummary;
                
                // Trigger the input event for instant live preview updates
                summaryInput.dispatchEvent(new Event("input", { bubbles: true }));
                
                showToast("Summary updated via Python Backend!", "success");
            } else {
                showToast("No summary returned by backend.", "warning");
            }
        } catch (error) {
            console.error("AI Summary Generation failed:", error);
            showToast(`AI Generation failed: ${error.message}`, "error");
        }
    });
}

async function generateAISkills() {
    const button = document.getElementById("aiSuggestSkillsBtn");
    const container = document.getElementById("suggestedSkillChips");
    if (!container) return;

    await executeWithLoadingState(button, async () => {
        const roleVal = resumeState.role || "Facility Manager";

        try {
            const response = await fetch("http://127.0.0.1:8000/api/generate-section", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    user_input: roleVal,
                    section_type: "skills"
                })
            });

            if (!response.ok) {
                const errDetail = await response.json().catch(() => ({}));
                throw new Error(errDetail.detail || response.statusText || "Backend failure");
            }

            const data = await response.json();
            const rawSkills = data.text || data.summary || data.skills || "";
            if (rawSkills) {
                const skills = rawSkills.split(",").map(s => s.replace(/^[-\d\.\s•\*]+/, "").trim()).filter(s => s !== "");
                if (skills.length > 0) {
                    container.innerHTML = "";
                    skills.forEach(skillName => {
                        const chip = document.createElement("span");
                        chip.className = "skill-chip";
                        chip.setAttribute("data-skill", skillName);
                        chip.textContent = skillName;
                        chip.addEventListener("click", () => {
                            const normalizedSkills = resumeState.skills.map(s => s.trim().toLowerCase());
                            if (!normalizedSkills.includes(skillName.toLowerCase())) {
                                resumeState.skills.push(skillName);
                                document.getElementById("skillsInput").value = resumeState.skills.join(", ");
                                renderPreview();
                                triggerAutosave();
                            }
                        });
                        container.appendChild(chip);
                    });
                    showToast("Skills suggestions updated!", "success");
                } else {
                    showToast("No skills were returned by the Backend.", "warning");
                }
            } else {
                throw new Error("Unexpected backend response format");
            }
        } catch (error) {
            console.error("AI Skills Suggestion Failure:", error);
            showToast(`API Failed: ${error.message}`, "error");
        }
    });
}

window.aiSuggestBullets = async function(id) {
    const button = document.getElementById(`ai-btn-${id}`);
    const input = document.getElementById(`exp-desc-${id}`);
    if (!button || !input) return;

    const exp = resumeState.experience.find(e => e.id === id);
    if (!exp) return;

    const jobTitle = exp.title || resumeState.role || "Facility Manager";
    const userText = input.value.trim();

    await executeWithLoadingState(button, async () => {
        try {
            const response = await fetch("http://127.0.0.1:8000/api/generate-section", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    user_input: userText,
                    section_type: "experience_bullets",
                    job_title: jobTitle
                })
            });

            if (!response.ok) {
                const errDetail = await response.json().catch(() => ({}));
                throw new Error(errDetail.detail || response.statusText || "Backend failure");
            }

            const data = await response.json();
            const cleanText = data.text || data.summary || "";
            if (cleanText) {
                input.value = cleanText;
                exp.desc = cleanText;
                
                // Trigger input event
                input.dispatchEvent(new Event("input", { bubbles: true }));
                
                showToast("Suggested bullets added successfully!", "success");
            } else {
                showToast("No bullets were returned by backend.", "warning");
            }
        } catch (error) {
            console.error("AI Suggest Bullets failed:", error);
            showToast(`AI Suggest Bullets failed: ${error.message}`, "error");
        }
    });
};

// ==========================================
// LIVE CUSTOMIZER CONFIGURATION
// ==========================================

function applyAccentTheme(color) {
    const preview = document.getElementById("resumePreviewContainer");
    let primary = "#f28c1b"; // default orange
    let secondary = "#b15d05";

    if (color === "navy") {
        primary = "#1e3a8a";
        secondary = "#172554";
    } else if (color === "emerald") {
        primary = "#059669";
        secondary = "#064e3b";
    } else if (color === "charcoal") {
        primary = "#374151";
        secondary = "#111827";
    }

    preview.style.setProperty('--theme-primary', primary);
    preview.style.setProperty('--theme-secondary', secondary);
    
    // Update local state
    resumeState.accentTheme = color;
    triggerAutosave();
}

function applyFont(font) {
    const preview = document.getElementById("resumePreviewContainer");
    preview.style.fontFamily = font;
    preview.querySelectorAll("*").forEach(el => {
        el.style.fontFamily = font;
    });

    // Update local state
    resumeState.fontFace = font;
    triggerAutosave();
}

// ==========================================
// STEP NAVIGATION & STEPPER UPDATES
// ==========================================

let currentStep = 1;

window.nextStep = function() {
    if (currentStep >= 5) return;
    document.getElementById("step" + currentStep).classList.remove("active");
    currentStep++;
    document.getElementById("step" + currentStep).classList.add("active");
    updateStepperUI();
    triggerAutosave();
};

window.prevStep = function() {
    if (currentStep <= 1) return;
    document.getElementById("step" + currentStep).classList.remove("active");
    currentStep--;
    document.getElementById("step" + currentStep).classList.add("active");
    updateStepperUI();
};

function updateStepperUI() {
    const progressFill = document.getElementById("stepperProgressFill");
    const percent = ((currentStep - 1) / 4) * 100;
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

window.finishBuild = function() {
    // Perform one final sync save
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
                template_id: "facility_property_manager",
                resume_data: resumeState,
                updated_at: new Date()
            }, { onConflict: ["email", "template_id"] });

        if (error) {
            console.warn("Supabase autosave check failed. Please ensure the 'resumes' table is created under your account.", error);
        } else {
            console.log("Supabase synced silently: Resume draft saved.");
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
            .eq("template_id", "facility_property_manager")
            .maybeSingle();

        if (data && data.resume_data) {
            resumeState = data.resume_data;
            
            // Sync customizer UI controls
            if (resumeState.accentTheme) {
                const swatch = document.querySelector(`.color-swatch[data-color="${resumeState.accentTheme}"]`);
                if (swatch) {
                    document.querySelectorAll(".color-swatch").forEach(s => s.classList.remove("active"));
                    swatch.classList.add("active");
                }
            }
            if (resumeState.fontFace) {
                document.getElementById("fontSelector").value = resumeState.fontFace;
            }

            console.log("Loaded existing draft from Supabase resumes database.");
        }
    } catch (err) {
        console.error("Supabase load error:", err);
    }
}

// ==========================================
// PRE-POPULATE DEMO DATA ENGINE
// ==========================================

function loadSampleData() {
    resumeState = {
        name: "Priya Singh",
        role: "Facility Property Manager",
        phone: "(123) 456-7890",
        email: "priya.singh@example.com",
        linkedin: "linkedin.com/in/priya",
        address: "San Jose, CA 95112",
        summary: "Facility property manager with seven years of experience maintaining corporate campuses. Specializing in preventive maintenance and vendor management.",
        experience: [
            {
                id: "exp-1",
                title: "Facility Property Manager",
                company: "Silicon Valley Tech Park",
                location: "Santa Clara, CA",
                dates: "Feb 2017 - Present",
                desc: "• Managed preventive maintenance across corporate campuses.\n• Negotiated vendor contracts reducing operating costs by 15%.\n• Implemented CAFM software."
            }
        ],
        education: [
            {
                id: "edu-1",
                degree: "Bachelor's Degree in Mechanical Engineering",
                institution: "San Jose State University",
                location: "San Jose, CA",
                dates: "May 2013"
            }
        ],
        skills: ["Preventive Maintenance", "Vendor Negotiation", "CAFM Software", "OSHA Compliance"],
        accentTheme: "orange",
        fontFace: "Plus Jakarta Sans"
    };

    syncStateToForm();
    renderExperienceCards();
    renderEducationCards();
    renderPreview();
    
    // Apply defaults to layout
    applyAccentTheme("orange");
    applyFont("Plus Jakarta Sans");
}