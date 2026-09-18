// RESUME STATE & DEFAULT DATA DEFINITION
let pm_resume_data = {
    name: "",
    role: "Project Manager",
    phone: "123-456-7890",
    email: "hello@reallygreatsite.com",
    address: "123 Anywhere St., Any City",
    website: "reallygreatsite.com",
    summary: "I am a qualified and professional web developer with five years of experience in database administration and website design. Strong creative and analytical skills. Team player with an eye for detail.",
    skills: ["Web Design", "Design Thinking", "Wireframe Creation", "Front End Coding", "Problem-Solving", "Computer Literacy", "Project Management Tools", "Strong Communication"],
    languages: ["English", "Spanish"],
    education: [
        {
            id: "edu-1",
            degree: "Secondary School",
            school: "Really Great High School",
            date: "2010 - 2014"
        },
        {
            id: "edu-2",
            degree: "Bachelor of Technology",
            school: "Really Great University",
            date: "2014 - 2016"
        }
    ],
    experience: [
        {
            id: "exp-1",
            title: "APPLICATIONS DEVELOPER",
            company: "Arowwai Industries",
            date: "2016 - Present",
            bullets: "Database administration and website design\nBuilt the logic for a streamlined ad-serving platform that scaled\nEducational institutions and online classroom management"
        },
        {
            id: "exp-2",
            title: "WEB CONTENT MANAGER",
            company: "Ginyard International Co.",
            date: "2014 - 2016",
            bullets: "Database administration and website design\nBuilt the logic for a streamlined ad-serving platform that scaled\nEducational institutions and online classroom management"
        },
        {
            id: "exp-3",
            title: "ANALYSIS CONTENT",
            company: "Aldenaire & Partners",
            date: "2010 - 2014",
            bullets: "Database administration and website design\nBuilt the logic for a streamlined ad-serving platform that scaled\nEducational institutions and online classroom management"
        }
    ]
};

// HELPER: Generate Safe IDs
function generateSafeId(prefix = "id") {
    return prefix + "-" + Math.random().toString(36).substr(2, 9);
}

// HELPER: Escape HTML
function escapeHTML(str) {
    if (!str) return "";
    return str
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// COLOR THEME SWITCHER & STEP NAVIGATION CONTROLS
let currentStep = 1;
const totalSteps = 5;

window.changeTheme = function (color) {
    document.documentElement.style.setProperty('--theme-color', color);
    const previewRole = document.getElementById("previewRole");
    if (previewRole) previewRole.style.color = color;

    document.querySelectorAll('.color-swatch').forEach(swatch => {
        swatch.classList.toggle('active', swatch.getAttribute('onclick')?.includes(color));
    });
};

window.updateStepperUI = function () {
    // Toggle active step panel
    for (let i = 1; i <= totalSteps; i++) {
        const stepEl = document.getElementById(`step${i}`);
        if (stepEl) stepEl.classList.toggle("active", i === currentStep);
    }
    // Update top progress nodes
    document.querySelectorAll(".step-node").forEach(node => {
        const stepNum = parseInt(node.getAttribute("data-step"));
        node.classList.toggle("active", stepNum <= currentStep);
    });
    // Update progress bar fill line width
    const fill = document.getElementById("stepperProgressFill");
    if (fill) fill.style.width = `${((currentStep - 1) / (totalSteps - 1)) * 100}%`;
};

window.nextStep = function () {
    if (currentStep < totalSteps) {
        currentStep++;
        window.updateStepperUI();
    }
};

window.prevStep = function () {
    if (currentStep > 1) {
        currentStep--;
        window.updateStepperUI();
    }
};

// PDF Download Generation
function downloadPDF() {
    if (document.activeElement) document.activeElement.blur();
    window.print();
}

// ==========================================
// TOAST NOTIFICATIONS UTILITY
// ==========================================
function showToast(message, type = "info") {
    console.log(`[Toast - ${type}] ${message}`);
    let container = document.getElementById("toastContainer");
    if (!container) {
        container = document.createElement("div");
        container.id = "toastContainer";
        container.style.cssText = "position: fixed; bottom: 25px; right: 25px; z-index: 10000; display: flex; flex-direction: column; gap: 10px;";
        document.body.appendChild(container);
    }
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
        buttonElement.classList.add("loading");
        buttonElement.innerHTML = `<i class="fa-solid fa-spinner fa-spin"></i> Generating...`;
        await actionCallback();
    } catch (err) {
        console.error("Error in executeWithLoadingState:", err);
        showToast(`AI Generation failed: ${err.message}`, "error");
    } finally {
        buttonElement.disabled = false;
        buttonElement.classList.remove("loading");
        buttonElement.innerHTML = originalText;
    }
}
async function generateAiSummary() {
    const summaryInput = document.getElementById("summaryInput");
    if (!summaryInput) return;
    const button = document.getElementById("aiSummaryBtn");

    await executeWithLoadingState(button, async () => {
        const response = await fetch(getResumeApiUrl('generate-summary'), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ user_input: summaryInput.value })
        });

        if (!response.ok) {
            const errDetail = await response.json().catch(() => ({}));
            throw new Error(errDetail.detail || response.statusText || "Backend failure");
        }

        const data = await response.json();
        const cleanSummary = data.summary || data.text || data.skills || "";
        if (cleanSummary) {
            summaryInput.value = cleanSummary;
            pm_resume_data.summary = cleanSummary;
            renderPreview();
            showToast("Summary updated via Python Backend!", "success");
        } else {
            showToast("No summary returned by backend.", "warning");
        }
    });
}
async function generateAiSkills() {
    const skillsInput = document.getElementById("skillsInput");
    const chipsContainer = document.getElementById("suggestedSkillChips");
    if (!skillsInput) return;
    const button = document.getElementById("aiSkillsBtn");

    await executeWithLoadingState(button, async () => {
        const response = await fetch(getResumeApiUrl('generate-section'), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_input: skillsInput.value || "Project Manager",
                section_type: "skills"
            })
        });

        if (!response.ok) {
            const errDetail = await response.json().catch(() => ({}));
            throw new Error(errDetail.detail || response.statusText || "Backend failure");
        }

        const data = await response.json();
        const cleanSkills = data.text || data.summary || data.skills || "";

        if (cleanSkills) {
            skillsInput.value = cleanSkills;
            pm_resume_data.skills = cleanSkills.split(",").map(s => s.trim()).filter(s => s !== "");
            renderPreview();

            if (chipsContainer) {
                chipsContainer.innerHTML = "";
                pm_resume_data.skills.forEach(skillText => {
                    const chip = document.createElement("span");
                    chip.className = "skill-chip";
                    chip.setAttribute("data-skill", skillText);
                    chip.innerText = skillText;

                    chip.addEventListener("click", function () {
                        const currentVal = skillsInput.value.trim();
                        const list = currentVal ? currentVal.split(",").map(s => s.trim()) : [];
                        if (!list.map(s => s.toLowerCase()).includes(skillText.toLowerCase())) {
                            list.push(skillText);
                            skillsInput.value = list.join(", ");
                            pm_resume_data.skills = list;
                            renderPreview();
                            showToast(`Added skill: ${skillText}`, "success");
                        }
                    });
                    chipsContainer.appendChild(chip);
                });
            }

            showToast("Skills generated successfully!", "success");
        } else {
            showToast("No skills returned by backend.", "warning");
        }
    });
}

window.generateAiExperienceForCard = async function (id) {
    const exp = pm_resume_data.experience.find(e => e.id === id);
    if (!exp) return;
    const textarea = document.getElementById(`exp-desc-${id}`);
    const button = document.getElementById(`ai-btn-${id}`);
    if (!textarea || !button) return;

    await executeWithLoadingState(button, async () => {
        const response = await fetch(getResumeApiUrl('generate-section'), {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                user_input: textarea.value,
                section_type: "experience_bullets",
                job_title: exp.title || "Project Manager"
            })
        });

        if (!response.ok) {
            const errDetail = await response.json().catch(() => ({}));
            throw new Error(errDetail.detail || response.statusText || "Backend failure");
        }

        const data = await response.json();
        const cleanBullets = data.text || data.summary || data.skills || "";
        if (cleanBullets) {
            textarea.value = cleanBullets;
            exp.bullets = cleanBullets;
            renderPreview();
            showToast("Experience bullets updated via Python Backend!", "success");
        } else {
            showToast("No experience bullets returned by backend.", "warning");
        }
    });
};

// ==========================================
// DYNAMIC COMPONENT RENDERING
// ==========================================
function renderEducationCards() {
    const container = document.getElementById("educationInputsContainer");
    if (!container) return;
    container.innerHTML = "";
    pm_resume_data.education.forEach((edu, index) => {
        const card = document.createElement("div");
        card.className = "dynamic-card";

        const degreeVal = escapeHTML(edu.degree);
        const schoolVal = escapeHTML(edu.school);
        const dateVal = escapeHTML(edu.date);
        const idVal = escapeHTML(edu.id);

        card.innerHTML = `
            <div class="card-header-actions">
                <span class="card-item-title">Education #${index + 1}</span>
                <button type="button" class="btn-remove-item" onclick="deleteEducation('${idVal}')"><i class="fa-solid fa-trash"></i> Remove</button>
            </div>
            <div class="input-group">
                <label>Title / Degree</label>
                <input type="text" value="${degreeVal}" placeholder="e.g. Bachelor of Technology" oninput="updateEducation('${idVal}', 'degree', this.value)">
            </div>
            <div class="input-group">
                <label>School / University</label>
                <input type="text" value="${schoolVal}" placeholder="e.g. Really Great University" oninput="updateEducation('${idVal}', 'school', this.value)">
            </div>
            <div class="input-group">
                <label>Date Range</label>
                <input type="text" value="${dateVal}" placeholder="e.g. 2014 - 2016" oninput="updateEducation('${idVal}', 'date', this.value)">
            </div>
        `;
        container.appendChild(card);
    });
}

function renderExperienceCards() {
    const container = document.getElementById("experienceInputsContainer");
    if (!container) return;
    container.innerHTML = "";
    pm_resume_data.experience.forEach((exp, index) => {
        const card = document.createElement("div");
        card.className = "dynamic-card";

        const titleVal = escapeHTML(exp.title);
        const companyVal = escapeHTML(exp.company);
        const dateVal = escapeHTML(exp.date);
        const bulletsVal = escapeHTML(exp.bullets);
        const idVal = escapeHTML(exp.id);

        card.innerHTML = `
            <div class="card-header-actions">
                <span class="card-item-title">Experience #${index + 1}</span>
                <button type="button" class="btn-remove-item" onclick="deleteExperience('${idVal}')"><i class="fa-solid fa-trash"></i> Remove</button>
            </div>
            <div class="input-group">
                <label>Job Title</label>
                <input type="text" value="${titleVal}" placeholder="e.g. Applications Developer" oninput="updateExperience('${idVal}', 'title', this.value)">
            </div>
            <div class="input-group">
                <label>Company Name</label>
                <input type="text" value="${companyVal}" placeholder="e.g. Arowwai Industries" oninput="updateExperience('${idVal}', 'company', this.value)">
            </div>
            <div class="input-group">
                <label>Date Range</label>
                <input type="text" value="${dateVal}" placeholder="e.g. 2016 - Present" oninput="updateExperience('${idVal}', 'date', this.value)">
            </div>
            <div class="input-group">
                <label>Experience Bullets (One per line)</label>
                <div class="textarea-ai-wrapper">
                    <textarea id="exp-desc-${idVal}" placeholder="Describe your achievements..." oninput="updateExperience('${idVal}', 'bullets', this.value)">${bulletsVal}</textarea>
                    <button type="button" id="ai-btn-${idVal}" class="btn-ai-action" onclick="generateAiExperienceForCard('${idVal}')">✨ Ai generated Bullet Points</button>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

// ==========================================
// FORM STATE UPDATERS & SYNC
// ==========================================
window.updateEducation = function (id, field, value) {
    const edu = pm_resume_data.education.find(e => e.id === id);
    if (edu) {
        edu[field] = value;
        renderPreview();
    }
};

window.deleteEducation = function (id) {
    pm_resume_data.education = pm_resume_data.education.filter(e => e.id !== id);
    renderEducationCards();
    renderPreview();
};

window.updateExperience = function (id, field, value) {
    const exp = pm_resume_data.experience.find(e => e.id === id);
    if (exp) {
        exp[field] = value;
        renderPreview();
    }
};

window.deleteExperience = function (id) {
    pm_resume_data.experience = pm_resume_data.experience.filter(e => e.id !== id);
    renderExperienceCards();
    renderPreview();
};

function syncStateToForm() {
    document.getElementById("nameInput").value = pm_resume_data.name || "";
    document.getElementById("roleInput").value = pm_resume_data.role || "";
    document.getElementById("phoneInput").value = pm_resume_data.phone || "";
    document.getElementById("emailInput").value = pm_resume_data.email || "";
    document.getElementById("addressInput").value = pm_resume_data.address || "";
    document.getElementById("websiteInput").value = pm_resume_data.website || "";
    document.getElementById("summaryInput").value = pm_resume_data.summary || "";
    document.getElementById("skillsInput").value = pm_resume_data.skills.join(", ");
    document.getElementById("langInput").value = pm_resume_data.languages.join(", ");
}

// ==========================================
// DYNAMIC PREVIEW CANVAS SYNC
// ==========================================
function renderPreview() {
    // 1. Basic details
    const previewName = document.getElementById("previewName");
    if (previewName) {
        const nameVal = pm_resume_data.name || "YOUR NAME";
        previewName.innerText = nameVal.toUpperCase();
    }

    const previewRole = document.getElementById("previewRole");
    if (previewRole) previewRole.innerText = (pm_resume_data.role || "PROJECT MANAGER").toUpperCase();

    const previewPhone = document.getElementById("previewPhone");
    if (previewPhone) previewPhone.innerText = pm_resume_data.phone || "123-456-7890";

    const previewEmail = document.getElementById("previewEmail");
    if (previewEmail) previewEmail.innerText = pm_resume_data.email || "hello@reallygreatsite.com";

    const previewAddress = document.getElementById("previewAddress");
    if (previewAddress) previewAddress.innerText = pm_resume_data.address || "123 Anywhere St., Any City";

    const previewWebsite = document.getElementById("previewWebsite");
    if (previewWebsite) previewWebsite.innerText = pm_resume_data.website || "reallygreatsite.com";

    const previewSummary = document.getElementById("previewSummary");
    if (previewSummary) previewSummary.innerText = pm_resume_data.summary || "I am a qualified and professional web developer with five years of experience in database administration and website design. Strong creative and analytical skills. Team player with an eye for detail.";

    // 2. Skills
    const previewSkills = document.getElementById("previewSkills");
    if (previewSkills) {
        previewSkills.innerHTML = "";
        pm_resume_data.skills.forEach(skill => {
            if (skill.trim() !== "") {
                const li = document.createElement("li");
                li.setAttribute("contenteditable", "true");
                li.innerText = skill.trim();
                previewSkills.appendChild(li);
            }
        });
    }

    // 3. Languages
    const previewLanguages = document.getElementById("previewLanguages");
    if (previewLanguages) {
        previewLanguages.innerHTML = "";
        pm_resume_data.languages.forEach(lang => {
            if (lang.trim() !== "") {
                const div = document.createElement("div");
                div.className = "lang-text";
                div.setAttribute("contenteditable", "true");
                div.innerText = lang.trim();
                previewLanguages.appendChild(div);
            }
        });
    }

    // 4. Education
    const previewEducationContainer = document.getElementById("previewEducationContainer");
    if (previewEducationContainer) {
        previewEducationContainer.innerHTML = "";
        pm_resume_data.education.forEach(edu => {
            const eduItem = document.createElement("div");
            eduItem.className = "edu-item";
            eduItem.innerHTML = `
                <div class="edu-degree" contenteditable="true">${edu.degree || "Degree Title"}</div>
                <div class="edu-school" contenteditable="true">${edu.school || "School / University"}</div>
                <div class="edu-date" contenteditable="true">${edu.date || "Date Range"}</div>
            `;
            previewEducationContainer.appendChild(eduItem);
        });
    }

    // 5. Experience
    const previewExperience = document.getElementById("previewExperience");
    if (previewExperience) {
        previewExperience.innerHTML = "";
        pm_resume_data.experience.forEach(exp => {
            const jobItem = document.createElement("div");
            jobItem.className = "job-item";

            let bulletsHtml = "";
            if (exp.bullets) {
                exp.bullets.split("\n").forEach(b => {
                    if (b.trim() !== "") {
                        bulletsHtml += `<li contenteditable="true">${b.replace(/^[•\-\*]\s*/, '').trim()}</li>`;
                    }
                });
            }

            jobItem.innerHTML = `
                <div class="job-node"></div>
                <div class="job-title" contenteditable="true">${(exp.title || "Job Title").toUpperCase()}</div>
                <div class="job-company" contenteditable="true">${exp.company || "Company Name"}</div>
                <div class="job-date" contenteditable="true">${exp.date || "Date Range"}</div>
                <ul class="main-bullet-list">
                    ${bulletsHtml}
                </ul>
            `;
            previewExperience.appendChild(jobItem);
        });
    }
}

// Expose PDF Download
window.downloadPDF = downloadPDF;

document.addEventListener("DOMContentLoaded", () => {
    // Render initial dynamic input lists and preview canvas
    renderEducationCards();
    renderExperienceCards();
    renderPreview();
    syncStateToForm();
    window.updateStepperUI();

    // Bind static text field handlers
    const bindHelper = (id, prop) => {
        const el = document.getElementById(id);
        if (el) {
            const handler = (e) => {
                pm_resume_data[prop] = e.target.value;
                renderPreview();
            };
            el.addEventListener("input", handler);
            el.addEventListener("keyup", handler);
        }
    };

    bindHelper("nameInput", "name");
    bindHelper("roleInput", "role");
    bindHelper("phoneInput", "phone");
    bindHelper("emailInput", "email");
    bindHelper("addressInput", "address");
    bindHelper("websiteInput", "website");
    bindHelper("summaryInput", "summary");

    // Bind Skills & Languages fields
    const skillsInput = document.getElementById("skillsInput");
    if (skillsInput) {
        skillsInput.addEventListener("input", (e) => {
            pm_resume_data.skills = e.target.value.split(",").map(s => s.trim()).filter(s => s !== "");
            renderPreview();
        });
    }

    const langInput = document.getElementById("langInput");
    if (langInput) {
        langInput.addEventListener("input", (e) => {
            pm_resume_data.languages = e.target.value.split(",").map(s => s.trim()).filter(s => s !== "");
            renderPreview();
        });
    }

    // Bind AI Buttons
    const aiSummaryBtn = document.getElementById("aiSummaryBtn");
    if (aiSummaryBtn) aiSummaryBtn.addEventListener("click", generateAiSummary);

    const aiSkillsBtn = document.getElementById("aiSkillsBtn");
    if (aiSkillsBtn) aiSkillsBtn.addEventListener("click", generateAiSkills);

    // Dynamic "+ Add" Buttons
    const addEduBtn = document.getElementById("addEduBtn");
    if (addEduBtn) {
        addEduBtn.addEventListener("click", () => {
            pm_resume_data.education.push({
                id: generateSafeId("edu"),
                degree: "",
                school: "",
                date: ""
            });
            renderEducationCards();
            renderPreview();
        });
    }

    const addExpBtn = document.getElementById("addExpBtn");
    if (addExpBtn) {
        addExpBtn.addEventListener("click", () => {
            pm_resume_data.experience.push({
                id: generateSafeId("exp"),
                title: "",
                company: "",
                date: "",
                bullets: ""
            });
            renderExperienceCards();
            renderPreview();
        });
    }

    // Dynamic Font Selector Handler
    const fontSelector = document.getElementById("fontSelector");
    if (fontSelector) {
        fontSelector.addEventListener("change", function () {
            const font = this.value;
            const targetCanvas = document.getElementById("resume-pdf-target");
            if (targetCanvas) {
                targetCanvas.style.fontFamily = `'${font}', sans-serif`;
            }
        });
    }

    // Photo Upload Handler
    const photoInput = document.getElementById("photoInput");
    if (photoInput) {
        photoInput.addEventListener("change", function (e) {
            const file = e.target.files[0];
            if (file) {
                const previewPhoto = document.getElementById("previewPhoto");
                if (previewPhoto) previewPhoto.src = URL.createObjectURL(file);
            }
        });
    }

    // Skill chips triggers
    document.querySelectorAll(".skill-chip").forEach(chip => {
        chip.addEventListener("click", function () {
            const skillName = this.getAttribute("data-skill");
            const skillsVal = skillsInput.value.trim();
            const list = skillsVal ? skillsVal.split(",").map(s => s.trim()) : [];

            if (!list.map(s => s.toLowerCase()).includes(skillName.toLowerCase())) {
                list.push(skillName);
                skillsInput.value = list.join(", ");
                pm_resume_data.skills = list;
                renderPreview();
                showToast(`Added skill: ${skillName}`, "success");
            } else {
                showToast(`Skill already added: ${skillName}`, "warning");
            }
        });
    });
});
