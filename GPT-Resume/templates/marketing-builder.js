// Default Avatar Constant (SVG Data URI)
const DEFAULT_AVATAR = "data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='%23cbd5e1'><path d='M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 4c1.93 0 3.5 1.57 3.5 3.5S13.93 13 12 13s-3.5-1.57-3.5-3.5S10.07 6 12 6zm0 14c-2.03 0-3.8-.85-5.05-2.2.03-1.68 3.37-2.6 5.05-2.6s5.02.92 5.05 2.6C15.8 19.15 14.03 20 12 20z'/></svg>";

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
    const skillsInputEl = document.getElementById("skillsInput");
    if (skillsInputEl) {
        skillsInputEl.addEventListener("input", (e) => {
            resumeState.skills = e.target.value.split(",").map(s => s.trim()).filter(s => s !== "");
            renderPreview();
        });
    }

    const langInputEl = document.getElementById("langInput");
    if (langInputEl) {
        langInputEl.addEventListener("input", (e) => {
            resumeState.languages = e.target.value.split(",").map(l => l.trim()).filter(l => l !== "");
            renderPreview();
        });
    }

    // Reference inputs binding
    bindInput("ref1Name", "previewRef1Name", "ref1Name");
    bindInput("ref1Sub", "previewRef1Sub", "ref1Sub");
    bindInput("ref1Meta", "previewRef1Meta", "ref1Meta");
    bindInput("ref2Name", "previewRef2Name", "ref2Name");
    bindInput("ref2Sub", "previewRef2Sub", "ref2Sub");
    bindInput("ref2Meta", "previewRef2Meta", "ref2Meta");

    // 2. Photo Upload Handler
    const photoInput = document.getElementById("photoInput");
    if (photoInput) {
        photoInput.addEventListener("change", function (e) {
            const file = e.target.files[0];
            if (file) {
                const reader = new FileReader();
                reader.onload = function (evt) {
                    const base64 = evt.target.result;
                    resumeState.photo = base64;
                    document.getElementById("previewPhoto").src = base64;
                };
                reader.readAsDataURL(file);
            }
        });
    }

    // 3. Repeatable Fields Buttons Bindings
    const addExpBtn = document.getElementById("addExperienceBtn");
    if (addExpBtn) {
        addExpBtn.addEventListener("click", () => {
            resumeState.experience.push({
                id: "exp-" + Date.now(),
                title: "",
                company: "",
                dates: "",
                desc: ""
            });
            renderExperienceCards();
            renderPreview();
        });
    }

    const addEduBtn = document.getElementById("addEducationBtn");
    if (addEduBtn) {
        addEduBtn.addEventListener("click", () => {
            resumeState.education.push({
                id: "edu-" + Date.now(),
                degree: "",
                institution: "",
                dates: ""
            });
            renderEducationCards();
            renderPreview();
        });
    }

    // 4. Load Initial Demo Data if empty
    if (!resumeState.experience.length && !resumeState.education.length) {
        loadSampleData();
    } else {
        syncStateToForm();
        renderExperienceCards();
        renderEducationCards();
        renderPreview();
    }
});

// Helper for basic text fields syncing
function bindInput(inputId, previewId, stateKey) {
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);

    if (input && preview) {
        input.addEventListener("input", () => {
            preview.innerText = input.value;
            resumeState[stateKey] = input.value;
        });
    }
}

// ==========================================
// DYNAMIC COMPONENT RENDER ENGINE
// ==========================================
function renderPreview() {
    document.getElementById("previewName").innerText = resumeState.name || "Olivia Wilson";
    document.getElementById("previewRole").innerText = resumeState.role || "Marketing Manager";
    document.getElementById("previewEmail").innerText = resumeState.email || "hello@reallygreatsite.com";
    document.getElementById("previewPhone").innerText = resumeState.phone || "+123-456-7890";
    document.getElementById("previewAddress").innerText = resumeState.address || "123 Anywhere St., Any City";
    document.getElementById("previewWebsite").innerText = resumeState.website || "reallygreatsite.com";

    const photoEl = document.getElementById("previewPhoto");
    if (resumeState.photo) {
        photoEl.src = resumeState.photo;
    } else {
        photoEl.src = DEFAULT_AVATAR;
    }

    document.getElementById("previewSummary").innerText = resumeState.summary || "Summary text";

    // Work Experience List
    const expList = document.getElementById("previewExperienceList");
    if (expList) {
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
    }

    // Education List
    const eduList = document.getElementById("previewEducationList");
    if (eduList) {
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
    }

    // Skills
    const skillsList = document.getElementById("previewSkills");
    if (skillsList) {
        skillsList.innerHTML = "";
        resumeState.skills.forEach(skill => {
            if (skill.trim() !== "") {
                const li = document.createElement("li");
                li.setAttribute("contenteditable", "true");
                li.innerText = skill.trim();
                skillsList.appendChild(li);
            }
        });
    }

    // Languages
    const langContainer = document.getElementById("previewLanguages");
    if (langContainer) {
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
    }
}

function renderExperienceCards() {
    const container = document.getElementById("experienceContainer");
    if (!container) return;
    container.innerHTML = "";
    resumeState.experience.forEach((exp, idx) => {
        const card = document.createElement("div");
        card.className = "repeatable-card exp-entry";
        card.innerHTML = `
            <div class="repeatable-card-header">
                <span class="repeatable-card-title">Experience #${idx + 1}</span>
                <button type="button" class="btn-delete-card" onclick="deleteExperience('${exp.id}')">Delete</button>
            </div>
            <div class="row-2">
                <div class="input-group">
                    <label>Job Title</label>
                    <input type="text" class="job-role-input exp-title" value="${exp.title || ''}" placeholder="Marketing Manager" oninput="updateExperience('${exp.id}', 'title', this.value)">
                </div>
                <div class="input-group">
                    <label>Company / Sub</label>
                    <input type="text" class="job-sub-input exp-company" value="${exp.company || ''}" placeholder="Timmerman Industries" oninput="updateExperience('${exp.id}', 'company', this.value)">
                </div>
            </div>
            <div class="input-group">
                <label>Date Range</label>
                <input type="text" class="exp-dates" value="${exp.dates || ''}" placeholder="e.g. Aug 2018 - present" oninput="updateExperience('${exp.id}', 'dates', this.value)">
            </div>
            <div class="input-group">
                <label>Responsibilities & Bullet Points</label>
                <div class="textarea-ai-wrapper">
                    <textarea class="job-bullets-input exp-desc" id="exp-desc-${exp.id}" placeholder="Type key highlights or notes here..." oninput="updateExperience('${exp.id}', 'desc', this.value)">${exp.desc || ''}</textarea>
                    <button type="button" class="btn-ai-action" onclick="enhanceExpAI(this)">
                        <i class="fa-solid fa-wand-magic-sparkles"></i> ✨ AI Generate Bullet Points
                    </button>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

function renderEducationCards() {
    const container = document.getElementById("educationContainer");
    if (!container) return;
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

window.updateExperience = function (id, field, value) {
    const exp = resumeState.experience.find(e => e.id === id);
    if (exp) {
        exp[field] = value;
        renderPreview();
    }
};

window.deleteExperience = function (id) {
    resumeState.experience = resumeState.experience.filter(e => e.id !== id);
    renderExperienceCards();
    renderPreview();
};

window.updateEducation = function (id, field, value) {
    const edu = resumeState.education.find(e => e.id === id);
    if (edu) {
        edu[field] = value;
        renderPreview();
    }
};

window.deleteEducation = function (id) {
    resumeState.education = resumeState.education.filter(e => e.id !== id);
    renderEducationCards();
    renderPreview();
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
}

function loadSampleData() {
    resumeState.name = "Olivia Wilson";
    resumeState.role = "Marketing Manager";
    resumeState.email = "hello@reallygreatsite.com";
    resumeState.phone = "+123-456-7890";
    resumeState.address = "123 Anywhere St., Any City";
    resumeState.website = "reallygreatsite.com";
    resumeState.summary = "Passionate Marketing Manager with over 8 years of experience leading multichannel digital campaigns, product promotion, and brand development strategies.";
    resumeState.skills = ["ROI Calculations", "Social Media Marketing", "Marketing Strategy", "Product Promotion"];
    resumeState.languages = ["English", "French"];

    resumeState.experience.push({
        id: "exp-1",
        title: "Marketing Manager",
        company: "Wardiere Inc.",
        dates: "2020 - Present",
        desc: "• Spearheaded digital marketing strategies yielding 35% growth in ROI.\n• Managed cross-functional teams to launch seasonal product campaigns."
    });

    resumeState.education.push({
        id: "edu-1",
        degree: "Master of Business Administration",
        institution: "Wardiere University",
        dates: "2015 - 2017"
    });

    syncStateToForm();
    renderExperienceCards();
    renderEducationCards();
    renderPreview();
}

// ==========================================
// REAL AI INTEGRATION FUNCTIONS WITH LOADING SPINNERS & CHIPS
// ==========================================

// 1. GENERATE EXECUTIVE SUMMARY WITH AI
async function enhanceSummaryAI(btn) {
    const summaryInput = document.getElementById("summaryInput");
    const userVal = summaryInput.value.trim();
    if (!userVal) {
        alert("Please enter some keywords or notes into the summary box first!");
        summaryInput.focus();
        return;
    }

    const origText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Generating...`;

    const host = window.location.hostname || "127.0.0.1";
    try {
        const res = await fetch(getResumeApiUrl('generate-summary'), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_input: userVal,
                job_title: resumeState.role || "Marketing Manager"
            })
        });

        if (res.ok) {
            const data = await res.json();
            const resultText = data.summary || data.text || "";
            if (resultText) {
                summaryInput.value = resultText;
                resumeState.summary = resultText;
                renderPreview();
            }
        } else {
            alert("Failed to generate summary from backend server.");
        }
    } catch (err) {
        alert("API Connection Error: Ensure FastAPI server is running on ${getResumeApiUrl('')}");
    } finally {
        btn.disabled = false;
        btn.innerHTML = origText;
    }
}

// 2. GENERATE EXPERIENCE BULLET POINTS WITH AI
async function enhanceExpAI(btn) {
    const card = btn.closest('.exp-entry');
    const roleInput = card.querySelector('.job-role-input');
    const subInput = card.querySelector('.job-sub-input');
    const bulletsInput = card.querySelector('.job-bullets-input');

    const jobRole = roleInput.value.trim() || "Marketing Manager";
    const jobSub = subInput.value.trim() || "";
    const userVal = bulletsInput.value.trim();

    const origText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Generating...`;

    const host = window.location.hostname || "127.0.0.1";
    try {
        const res = await fetch(getResumeApiUrl('generate-section'), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_input: userVal || `Key duties and achievements for ${jobRole} at ${jobSub}`,
                section_type: "experience_bullets",
                job_title: jobRole
            })
        });

        if (res.ok) {
            const data = await res.json();
            const rawResult = data.bullets || data.text || data.summary || "";

            let bulletLines = Array.isArray(rawResult)
                ? rawResult
                : rawResult.split(/[\n]+/).map(s => s.replace(/^[-•*#\d.\s]+/, "").trim()).filter(Boolean);

            if (bulletLines.length > 0) {
                bulletsInput.value = bulletLines.join("\n");
                // Update corresponding experience object in state
                const expDescId = bulletsInput.id.replace("exp-desc-", "");
                const expObj = resumeState.experience.find(e => e.id === expDescId);
                if (expObj) {
                    expObj.desc = bulletsInput.value;
                }
                renderPreview();
            }
        } else {
            alert("Failed to generate bullet points from backend server.");
        }
    } catch (err) {
        alert("API Connection Error: Ensure FastAPI server is running on ${getResumeApiUrl('')}");
    } finally {
        btn.disabled = false;
        btn.innerHTML = origText;
    }
}

// 3. GENERATE SKILLS WITH AI & SUGGESTION CHIPS
async function generateSkillsAI(btn) {
    const skillsInput = document.getElementById("skillsInput");
    const wrap = document.getElementById("aiSuggestionsWrapper");
    const chipsContainer = document.getElementById("suggestedSkillChips");

    const userVal = skillsInput.value.trim();
    const origText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Generating...`;

    const host = window.location.hostname || "127.0.0.1";
    try {
        const res = await fetch(getResumeApiUrl('generate-section'), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_input: userVal || "Core marketing skills",
                section_type: "skills",
                job_title: resumeState.role || "Marketing Manager"
            })
        });

        if (res.ok) {
            const data = await res.json();
            let rawSkills = data.skills || data.text || "";
            let skillList = Array.isArray(rawSkills)
                ? rawSkills
                : rawSkills.split(",").map(s => s.replace(/^[-•*#\d.\s]+/, "").trim()).filter(Boolean);

            chipsContainer.innerHTML = "";
            skillList.forEach(skill => {
                const chip = document.createElement("button");
                chip.type = "button";
                chip.className = "ai-suggestion-chip";
                chip.innerHTML = `<i class="fa-solid fa-plus" style="font-size: 9px;"></i> ${skill}`;

                chip.onclick = () => {
                    let current = skillsInput.value.trim();
                    skillsInput.value = current ? `${current}, ${skill}` : skill;
                    resumeState.skills = skillsInput.value.split(",").map(s => s.trim()).filter(Boolean);
                    renderPreview();
                    chip.remove();
                    if (chipsContainer.children.length === 0 && wrap) {
                        wrap.style.display = "none";
                    }
                };
                chipsContainer.appendChild(chip);
            });

            if (wrap) wrap.style.display = "block";
        } else {
            alert("Failed to generate skills from backend server.");
        }
    } catch (err) {
        alert("API Connection Error: Ensure FastAPI server is running on ${getResumeApiUrl('')}");
    } finally {
        btn.disabled = false;
        btn.innerHTML = origText;
    }
}

// STEPPER & PDF DOWNLOAD UTILITIES
let currentStep = 1;
function nextStep() {
    if (currentStep < 5) {
        document.getElementById("step" + currentStep).classList.remove("active");
        currentStep++;
        document.getElementById("step" + currentStep).classList.add("active");
        updateStepperUI();
    }
}

function prevStep() {
    if (currentStep > 1) {
        document.getElementById("step" + currentStep).classList.remove("active");
        currentStep--;
        document.getElementById("step" + currentStep).classList.add("active");
        updateStepperUI();
    }
}

function updateStepperUI() {
    document.querySelectorAll('.step-node').forEach((node, idx) => {
        if (idx + 1 <= currentStep) {
            node.classList.add('active');
        } else {
            node.classList.remove('active');
        }
    });
}

function downloadPDF() {
    window.print();
}

function finishBuild() {
    alert("Resume configuration successfully saved!");
}