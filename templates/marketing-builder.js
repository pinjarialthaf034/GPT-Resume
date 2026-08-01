// ==========================================
// TEMPLATE METADATA REGISTRATION
// ==========================================
const templateMetadata = {
    id: "marketing_manager",
    name: "Marketing Manager",
    hasPhoto: true,
    accentTheme: "deepblue",
    fontFace: "Plus Jakarta Sans"
};

// ==========================================
// RESUME STATE & DEFAULT DATA DEFINITION
// ==========================================
let resumeState = {
    name: "",
    role: "",
    email: "",
    phone: "",
    address: "",
    website: "",
    summary: "",
    skills: [],
    languages: [],
    experience: [],
    education: [],
    ref1Name: "",
    ref1Sub: "",
    ref1Meta: "",
    ref2Name: "",
    ref2Sub: "",
    ref2Meta: "",
    accentTheme: "deepblue",
    fontFace: "Plus Jakarta Sans",
    photo: ""
};

// ==========================================
// INITIAL EVENT HANDLERS & DOM BINDINGS
// ==========================================
document.addEventListener("DOMContentLoaded", () => {
    // 1. Text Inputs Binding
    bindInput("nameInput", "previewName", "name");
    bindInput("roleInput", "previewRole", "role");
    bindInput("emailInput", "previewEmail", "email");
    bindInput("phoneInput", "previewPhone", "phone");
    bindInput("addressInput", "previewAddress", "address");
    bindInput("websiteInput", "previewWebsite", "website");
    bindInput("summaryInput", "previewSummary", "summary");
    
    // Skills and Languages input bindings
    document.getElementById("skillsInput").addEventListener("input", (e) => {
        resumeState.skills = e.target.value.split(",").map(s => s.trim()).filter(s => s !== "");
        renderPreview();
        triggerAutosave();
    });

    document.getElementById("langInput").addEventListener("input", (e) => {
        resumeState.languages = e.target.value.split(",").map(l => l.trim()).filter(l => l !== "");
        renderPreview();
        triggerAutosave();
    });

    // Reference inputs binding
    bindInput("ref1Name", "previewRef1Name", "ref1Name");
    bindInput("ref1Sub", "previewRef1Sub", "ref1Sub");
    bindInput("ref1Meta", "previewRef1Meta", "ref1Meta");
    bindInput("ref2Name", "previewRef2Name", "ref2Name");
    bindInput("ref2Sub", "previewRef2Sub", "ref2Sub");
    bindInput("ref2Meta", "previewRef2Meta", "ref2Meta");

    // 2. Photo Upload Handler (base64 persistence)
    const photoInput = document.getElementById("photoInput");
    if (photoInput) {
        photoInput.addEventListener("change", function(e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function(evt) {
                    const base64 = evt.target.result;
                    resumeState.photo = base64;
                    document.getElementById("previewPhoto").src = base64;
                    triggerAutosave();
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // 3. Repeatable Fields Buttons Bindings
    document.getElementById("addExperienceBtn").addEventListener("click", () => {
        resumeState.experience.push({
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
        resumeState.education.push({
            id: "edu-" + Date.now(),
            degree: "",
            institution: "",
            dates: ""
        });
        renderEducationCards();
        renderPreview();
        triggerAutosave();
    });

    // 4. AI Tools Bindings
    document.getElementById("aiGenerateSummaryBtn").addEventListener("click", generateSummaryWithAI);
    setupSkillChips();

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

    // 5. Customizer Swatches & Fonts Bindings
    setupCustomizer();

    // 6. Inline Preview contenteditable listeners
    setupDynamicPreviewSync();

    // 7. Initialize/Load drafts or pre-populate demo data
    loadSavedResume().then(() => {
        if (!resumeState.experience.length && !resumeState.education.length && !resumeState.name) {
            loadSampleData();
        } else {
            syncStateToForm();
            renderExperienceCards();
            renderEducationCards();
            renderPreview();
            applyAccentTheme(resumeState.accentTheme || "deepblue");
            applyFont(resumeState.fontFace || "Plus Jakarta Sans");
        }
    });

    updateStepperUI();
});

// Helper for basic text fields syncing
function bindInput(inputId, previewId, stateKey) {
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);

    if (input && preview) {
        input.addEventListener("input", () => {
            preview.innerText = input.value;
            resumeState[stateKey] = input.value;
            triggerAutosave();
        });
    }
}

// ==========================================
// DYNAMIC COMPONENT RENDER ENGINE
// ==========================================
function renderPreview() {
    // 1. Contact details
    document.getElementById("previewName").innerText = resumeState.name || "Olivia Wilson";
    document.getElementById("previewRole").innerText = resumeState.role || "Marketing Manager";
    document.getElementById("previewEmail").innerText = resumeState.email || "hello@reallygreatsite.com";
    document.getElementById("previewPhone").innerText = resumeState.phone || "+123-456-7890";
    document.getElementById("previewAddress").innerText = resumeState.address || "123 Anywhere St., Any City";
    document.getElementById("previewWebsite").innerText = resumeState.website || "reallygreatsite.com";
    
    // Photo Sync
    const photoEl = document.getElementById("previewPhoto");
    if (resumeState.photo) {
        photoEl.src = resumeState.photo;
    } else {
        photoEl.src = "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&q=80&w=400";
    }

    // 2. Summary
    document.getElementById("previewSummary").innerText = resumeState.summary || "Summary text";

    // 3. Work Experience List
    const expList = document.getElementById("previewExperienceList");
    expList.innerHTML = "";
    resumeState.experience.forEach(exp => {
        const div = document.createElement("div");
        div.className = "job-item";
        
        let bulletsHtml = "";
        if (exp.desc) {
            const lines = exp.desc.split("\n").filter(l => l.trim() !== "");
            bulletsHtml = `<ul class="main-bullet-list">` + 
                          lines.map(line => `<li contenteditable="true">${line.replace(/^[•\-\*]\s*/, '')}</li>`).join("") + 
                          `</ul>`;
        }
        
        div.innerHTML = `
            <div class="job-date" contenteditable="true">${exp.dates || "Dates"}</div>
            <div class="job-company" contenteditable="true">${exp.company || "Company"}</div>
            <div class="job-title" contenteditable="true">${exp.title || "Job Title"}</div>
            ${bulletsHtml}
        `;
        expList.appendChild(div);
    });

    // 4. Education List
    const eduList = document.getElementById("previewEducationList");
    eduList.innerHTML = "";
    resumeState.education.forEach(edu => {
        const div = document.createElement("div");
        div.className = "edu-item";
        div.innerHTML = `
            <div class="edu-title" contenteditable="true">${edu.degree || "Degree"}</div>
            <div class="edu-sub" contenteditable="true">${edu.institution || "Institution"}</div>
            <div class="edu-date" contenteditable="true">${edu.dates || "Dates"}</div>
        `;
        eduList.appendChild(div);
    });

    // 5. Skills
    const skillsList = document.getElementById("previewSkills");
    skillsList.innerHTML = "";
    resumeState.skills.forEach(skill => {
        if (skill.trim() !== "") {
            const li = document.createElement("li");
            li.setAttribute("contenteditable", "true");
            li.innerText = skill.trim();
            skillsList.appendChild(li);
        }
    });

    // 6. Languages
    const langContainer = document.getElementById("previewLanguages");
    langContainer.innerHTML = "";
    resumeState.languages.forEach(lang => {
        if (lang.trim() !== "") {
            const div = document.createElement("div");
            div.className = "lang-text";
            div.setAttribute("contenteditable", "true");
            div.innerText = lang.trim();
            langContainer.appendChild(div);
        }
    });

    // 7. References
    document.getElementById("previewRef1Name").innerText = resumeState.ref1Name || "Estelle Darcy";
    document.getElementById("previewRef1Sub").innerText = resumeState.ref1Sub || "Wardiere Inc. / CEO";
    document.getElementById("previewRef1Meta").innerHTML = (resumeState.ref1Meta || "Phone: +123-456-7890<br>Email: hello@reallygreatsite.com").replace(/\|/g, "<br>");
    
    document.getElementById("previewRef2Name").innerText = resumeState.ref2Name || "Harper Russo";
    document.getElementById("previewRef2Sub").innerText = resumeState.ref2Sub || "Wardiere Inc. / CEO";
    document.getElementById("previewRef2Meta").innerHTML = (resumeState.ref2Meta || "Phone: +123-456-7890<br>Email: hello@reallygreatsite.com").replace(/\|/g, "<br>");
}

function renderExperienceCards() {
    const container = document.getElementById("experienceContainer");
    container.innerHTML = "";
    resumeState.experience.forEach((exp, idx) => {
        const card = document.createElement("div");
        card.className = "repeatable-card";
        card.innerHTML = `
            <div class="repeatable-card-header">
                <span class="repeatable-card-title">Experience #${idx + 1}</span>
                <button type="button" class="btn-delete-card" onclick="deleteExperience('${exp.id}')">Delete</button>
            </div>
            <div class="row-2">
                <div class="input-group">
                    <label>Job Title</label>
                    <input type="text" class="exp-title" value="${exp.title || ''}" placeholder="Marketing Manager" oninput="updateExperience('${exp.id}', 'title', this.value)">
                </div>
                <div class="input-group">
                    <label>Company</label>
                    <input type="text" class="exp-company" value="${exp.company || ''}" placeholder="Timmerman Industries" oninput="updateExperience('${exp.id}', 'company', this.value)">
                </div>
            </div>
            <div class="input-group">
                <label>Date Range</label>
                <input type="text" class="exp-dates" value="${exp.dates || ''}" placeholder="e.g. Aug 2018 - present" oninput="updateExperience('${exp.id}', 'dates', this.value)">
            </div>
            <div class="input-group">
                <label>Responsibilities (One per line)</label>
                <div class="textarea-ai-wrapper">
                    <textarea class="exp-desc" id="exp-desc-${exp.id}" placeholder="• Managed campaigns..." oninput="updateExperience('${exp.id}', 'desc', this.value)">${exp.desc || ''}</textarea>
                    <button type="button" id="ai-btn-${exp.id}" class="btn-ai-action" onclick="aiSuggestBullets('${exp.id}')">
                        <i class="fa-solid fa-wand-magic-sparkles"></i> ✨ AI Action Bullets
                    </button>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

function renderEducationCards() {
    const container = document.getElementById("educationContainer");
    container.innerHTML = "";
    resumeState.education.forEach((edu, idx) => {
        const card = document.createElement("div");
        card.className = "repeatable-card";
        card.innerHTML = `
            <div class="repeatable-card-header">
                <span class="repeatable-card-title">Education #${idx + 1}</span>
                <button type="button" class="btn-delete-card" onclick="deleteEducation('${edu.id}')">Delete</button>
            </div>
            <div class="row-2">
                <div class="input-group">
                    <label>Degree / Program</label>
                    <input type="text" class="edu-degree" value="${edu.degree || ''}" placeholder="Master of Business" oninput="updateEducation('${edu.id}', 'degree', this.value)">
                </div>
                <div class="input-group">
                    <label>Institution</label>
                    <input type="text" class="edu-institution" value="${edu.institution || ''}" placeholder="Wardiere University" oninput="updateEducation('${edu.id}', 'institution', this.value)">
                </div>
            </div>
            <div class="input-group">
                <label>Dates</label>
                <input type="text" class="edu-dates" value="${edu.dates || ''}" placeholder="e.g. 2011 - 2015" oninput="updateEducation('${edu.id}', 'dates', this.value)">
            </div>
        `;
        container.appendChild(card);
    });
}

// ==========================================
// FORM CARD UPDATE OPERATIONS
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
    document.getElementById("emailInput").value = resumeState.email || "";
    document.getElementById("phoneInput").value = resumeState.phone || "";
    document.getElementById("addressInput").value = resumeState.address || "";
    document.getElementById("websiteInput").value = resumeState.website || "";
    document.getElementById("summaryInput").value = resumeState.summary || "";
    document.getElementById("skillsInput").value = resumeState.skills.join(", ");
    document.getElementById("langInput").value = resumeState.languages.join(", ");
    document.getElementById("ref1Name").value = resumeState.ref1Name || "";
    document.getElementById("ref1Sub").value = resumeState.ref1Sub || "";
    document.getElementById("ref1Meta").value = resumeState.ref1Meta || "";
    document.getElementById("ref2Name").value = resumeState.ref2Name || "";
    document.getElementById("ref2Sub").value = resumeState.ref2Sub || "";
    document.getElementById("ref2Meta").value = resumeState.ref2Meta || "";
}

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
        window.showToast(`AI Generation failed: ${err.message}`, "error");
    } finally {
        buttonElement.disabled = false;
        buttonElement.innerHTML = originalText;
    }
}

// ==========================================
// DEEP GROQ AI ASSISTANCE
// ==========================================
async function generateSummaryWithAI() {
    const button = document.getElementById("aiGenerateSummaryBtn");
    const summaryInput = document.getElementById("summaryInput");
    if (!summaryInput) return;

    await executeWithLoadingState(button, async () => {
        try {
            const response = await fetch(`http://${window.location.hostname}:8000/api/generate-summary`, {
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
                
                // Trigger input event
                summaryInput.dispatchEvent(new Event("input", { bubbles: true }));
                
                window.showToast("Summary updated via Python Backend!", "success");
            } else {
                window.showToast("No summary returned by backend.", "warning");
            }
        } catch (error) {
            console.error("AI Summary generation failed:", error);
            window.showToast(`Generation failed: ${error.message}`, "error");
        }
    });
}

window.aiSuggestBullets = async function(id) {
    const button = document.getElementById(`ai-btn-${id}`);
    const input = document.getElementById(`exp-desc-${id}`);
    if (!button || !input) return;

    const exp = resumeState.experience.find(e => e.id === id);
    if (!exp) return;

    const title = exp.title || "Marketing Manager";
    const userText = input.value.trim();

    await executeWithLoadingState(button, async () => {
        try {
            const response = await fetch(`http://${window.location.hostname}:8000/api/generate-section`, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    user_input: userText,
                    section_type: "experience_bullets",
                    job_title: title
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
                
                window.showToast("STAR action bullets added successfully!", "success");
            } else {
                window.showToast("No bullets returned by AI Service.", "warning");
            }
        } catch (error) {
            console.error("AI Action bullets failed:", error);
            window.showToast(`Bullets failed: ${error.message}`, "error");
        }
    });
};

async function generateAISkills() {
    const button = document.getElementById("aiSuggestSkillsBtn");
    const container = document.getElementById("suggestedSkillChips");
    if (!container) return;

    await executeWithLoadingState(button, async () => {
        const roleVal = resumeState.role || "Marketing Manager";

        try {
            const response = await fetch(`http://${window.location.hostname}:8000/api/generate-section`, {
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
                    window.showToast("Skills suggestions updated!", "success");
                } else {
                    window.showToast("No skills were returned by Backend.", "warning");
                }
            } else {
                throw new Error("Unexpected backend response format");
            }
        } catch (error) {
            console.error("AI Skills Suggestion Failure:", error);
            window.showToast(`API Failed: ${error.message}`, "error");
        }
    });
}

function setupSkillChips() {
    const chips = document.querySelectorAll(".skill-chip");
    chips.forEach(chip => {
        chip.addEventListener("click", () => {
            const skillName = chip.getAttribute("data-skill");
            const exists = resumeState.skills.some(s => s.toLowerCase().trim() === skillName.toLowerCase().trim());
            if (!exists) {
                resumeState.skills.push(skillName);
                document.getElementById("skillsInput").value = resumeState.skills.join(", ");
                renderPreview();
                triggerAutosave();
                window.showToast(`Added skill: ${skillName}`, "success");
            } else {
                window.showToast(`Skill already added: ${skillName}`, "info");
            }
        });
    });
}

// ==========================================
// LIVE CUSTOMIZER CONFIGURATION
// ==========================================
function applyAccentTheme(color) {
    const preview = document.getElementById("resumePreviewContainer");
    let primary = "#1e3a8a"; // default deepblue

    if (color === "indigo") {
        primary = "#4f46e5";
    } else if (color === "emerald") {
        primary = "#059669";
    } else if (color === "slate") {
        primary = "#334155";
    }

    preview.style.setProperty('--accent-color', primary);
    
    // Update active swatch state
    document.querySelectorAll(".color-swatch").forEach(swatch => {
        if (swatch.getAttribute("data-color") === color) {
            swatch.classList.add("active");
        } else {
            swatch.classList.remove("active");
        }
    });

    resumeState.accentTheme = color;
    triggerAutosave();
}

function applyFont(font) {
    const preview = document.getElementById("resumePreviewContainer");
    preview.style.fontFamily = font;
    preview.querySelectorAll("*").forEach(el => {
        el.style.fontFamily = font;
    });

    document.getElementById("fontSelector").value = font;
    resumeState.fontFace = font;
    triggerAutosave();
}

function setupCustomizer() {
    const swatches = document.querySelectorAll(".color-swatch");
    swatches.forEach(swatch => {
        swatch.addEventListener("click", () => {
            const color = swatch.getAttribute("data-color");
            applyAccentTheme(color);
        });
    });

    const fontSelector = document.getElementById("fontSelector");
    if (fontSelector) {
        fontSelector.addEventListener("change", (e) => {
            applyFont(e.target.value);
        });
    }
}

// ==========================================
// PREVIEW EDITABLE INLINE BACK-SYNC
// ==========================================
function bindContentEditable(elementId, stateKey, inputId) {
    const element = document.getElementById(elementId);
    if (element) {
        element.addEventListener("blur", () => {
            const value = element.innerText.trim();
            resumeState[stateKey] = value;
            const input = document.getElementById(inputId);
            if (input) {
                input.value = value;
            }
            triggerAutosave();
        });
    }
}

function setupDynamicPreviewSync() {
    // 1. Text elements
    bindContentEditable("previewName", "name", "nameInput");
    bindContentEditable("previewRole", "role", "roleInput");
    bindContentEditable("previewEmail", "email", "emailInput");
    bindContentEditable("previewPhone", "phone", "phoneInput");
    bindContentEditable("previewAddress", "address", "addressInput");
    bindContentEditable("previewWebsite", "website", "websiteInput");
    bindContentEditable("previewSummary", "summary", "summaryInput");
    
    bindContentEditable("previewRef1Name", "ref1Name", "ref1Name");
    bindContentEditable("previewRef1Sub", "ref1Sub", "ref1Sub");
    bindContentEditable("previewRef1Meta", "ref1Meta", "ref1Meta");
    bindContentEditable("previewRef2Name", "ref2Name", "ref2Name");
    bindContentEditable("previewRef2Sub", "ref2Sub", "ref2Sub");
    bindContentEditable("previewRef2Meta", "ref2Meta", "ref2Meta");

    // 2. Skills list sync
    const previewSkills = document.getElementById("previewSkills");
    if (previewSkills) {
        previewSkills.addEventListener("blur", (e) => {
            if (e.target.tagName === "LI") {
                const listItems = Array.from(previewSkills.querySelectorAll("li")).map(li => li.innerText.trim()).filter(t => t !== "");
                resumeState.skills = listItems;
                document.getElementById("skillsInput").value = listItems.join(", ");
                triggerAutosave();
            }
        }, true);
    }
    
    // 3. Languages list sync
    const previewLanguages = document.getElementById("previewLanguages");
    if (previewLanguages) {
        previewLanguages.addEventListener("blur", (e) => {
            if (e.target.classList.contains("lang-text")) {
                const langItems = Array.from(previewLanguages.querySelectorAll(".lang-text")).map(div => div.innerText.trim()).filter(t => t !== "");
                resumeState.languages = langItems;
                document.getElementById("langInput").value = langItems.join(", ");
                triggerAutosave();
            }
        }, true);
    }

    // 4. Work Experience preview sync
    const previewExperienceList = document.getElementById("previewExperienceList");
    if (previewExperienceList) {
        previewExperienceList.addEventListener("blur", (e) => {
            const jobItem = e.target.closest(".job-item");
            if (jobItem) {
                const index = Array.from(previewExperienceList.querySelectorAll(".job-item")).indexOf(jobItem);
                if (index !== -1 && resumeState.experience[index]) {
                    const item = resumeState.experience[index];
                    
                    const dateEl = jobItem.querySelector(".job-date");
                    const compEl = jobItem.querySelector(".job-company");
                    const titleEl = jobItem.querySelector(".job-title");
                    
                    if (dateEl) item.dates = dateEl.innerText.trim();
                    if (compEl) item.company = compEl.innerText.trim();
                    if (titleEl) item.title = titleEl.innerText.trim();
                    
                    const bulletsList = jobItem.querySelector(".main-bullet-list");
                    if (bulletsList) {
                        const lines = Array.from(bulletsList.querySelectorAll("li")).map(li => "• " + li.innerText.trim());
                        item.desc = lines.join("\n");
                    }
                    
                    renderExperienceCards();
                    triggerAutosave();
                }
            }
        }, true);
    }

    // 5. Education preview sync
    const previewEducationList = document.getElementById("previewEducationList");
    if (previewEducationList) {
        previewEducationList.addEventListener("blur", (e) => {
            const eduItem = e.target.closest(".edu-item");
            if (eduItem) {
                const index = Array.from(previewEducationList.querySelectorAll(".edu-item")).indexOf(eduItem);
                if (index !== -1 && resumeState.education[index]) {
                    const item = resumeState.education[index];
                    
                    const titleEl = eduItem.querySelector(".edu-title");
                    const subEl = eduItem.querySelector(".edu-sub");
                    const dateEl = eduItem.querySelector(".edu-date");
                    
                    if (titleEl) item.degree = titleEl.innerText.trim();
                    if (subEl) item.institution = subEl.innerText.trim();
                    if (dateEl) item.dates = dateEl.innerText.trim();
                    
                    renderEducationCards();
                    triggerAutosave();
                }
            }
        }, true);
    }
}

// ==========================================
// STEP NAVIGATION & STEPPER UPDATES
// ==========================================
let currentStep = 1;
const totalSteps = 5;

window.nextStep = function() {
    if (currentStep >= totalSteps) return;
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
    const percent = ((currentStep - 1) / (totalSteps - 1)) * 100;
    if (progressFill) progressFill.style.width = percent + "%";
    
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
                template_id: "marketing_manager",
                resume_data: resumeState,
                updated_at: new Date()
            }, { onConflict: ["email", "template_id"] });

        if (error) {
            console.warn("Supabase autosave check failed. Please ensure the 'resumes' table is created under your account.", error);
        } else {
            console.log("Supabase synced silently: Marketing Resume draft saved.");
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
            .eq("template_id", "marketing_manager")
            .maybeSingle();

        if (data && data.resume_data) {
            resumeState = data.resume_data;
            console.log("Loaded existing Marketing Manager draft from Supabase resumes database.");
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
        name: "Olivia Wilson",
        role: "Marketing Manager",
        phone: "+123-456-7890",
        email: "hello@reallygreatsite.com",
        address: "123 Anywhere St., Any City",
        website: "reallygreatsite.com",
        summary: "An experienced Marketing Manager with exceptional skills in creating marketing plans, launching products, promoting them, and overseeing their development. Excellent knowledge of SEO, content creation, social media audience engagement, and brand management.",
        experience: [
            {
                id: "exp-1",
                title: "Marketing Manager",
                company: "Timmerman Industries",
                dates: "Aug 2018 - present",
                desc: "• Maintained and organized numerous office files\n• Constantly updated the company's contact and mailing lists\n• Monitored ongoing marketing campaigns\n• Monitored press coverage"
            },
            {
                id: "exp-2",
                title: "Marketing Assistant",
                company: "Timmerman Industries",
                dates: "Jul 2015 - Aug 2018",
                desc: "• Handled the company's online presence – regularly updated the company's website and various social media accounts\n• Monitored ongoing marketing campaigns"
            },
            {
                id: "exp-3",
                title: "Marketing Assistant",
                company: "Liceria & Co.",
                dates: "Aug 2014 - Jul 2015",
                desc: "• Handled the company's online presence – regularly updated the company's website and various social media accounts"
            }
        ],
        education: [
            {
                id: "edu-1",
                degree: "Master of Business",
                institution: "Wardiere University",
                dates: "2011 - 2015"
            },
            {
                id: "edu-2",
                degree: "BA Sales and Commerce",
                institution: "Wardiere University",
                dates: "2011 - 2015"
            }
        ],
        skills: ["ROI Calculations", "Social media marketing", "Product development lifecycle", "Marketing strategy", "Product promotion", "Value Propositions"],
        languages: ["English", "French"],
        ref1Name: "Estelle Darcy",
        ref1Sub: "Wardiere Inc. / CEO",
        ref1Meta: "Phone: +123-456-7890 | Email: hello@reallygreatsite.com",
        ref2Name: "Harper Russo",
        ref2Sub: "Wardiere Inc. / CEO",
        ref2Meta: "Phone: +123-456-7890 | Email: hello@reallygreatsite.com",
        accentTheme: "deepblue",
        fontFace: "Plus Jakarta Sans",
        photo: ""
    };

    syncStateToForm();
    renderExperienceCards();
    renderEducationCards();
    renderPreview();
    
    // Apply defaults to layout
    applyAccentTheme("deepblue");
    applyFont("Plus Jakarta Sans");
}

// ==========================================
// PDF Download Generation
// ==========================================
window.downloadPDF = function() {
    if (document.activeElement) document.activeElement.blur();
    window.print();
}
