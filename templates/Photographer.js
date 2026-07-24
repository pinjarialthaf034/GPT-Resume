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
// INITIAL EVENT HANDLERS BINDINGS
// ==========================================
// ==========================================
// PRE-POPULATE DEMO DATA ENGINE / FALLBACKS
// ==========================================
function populateDefaultValuesIfEmpty() {
    try {
        const previewName = document.getElementById("previewName")?.textContent.trim();
        const previewRole = document.getElementById("previewRole")?.textContent.trim();
        const previewSummary = document.getElementById("previewSummary")?.textContent.trim();

        if (!photographer_resume_data.name) {
            photographer_resume_data.name = (previewName && previewName !== "Full Name" && previewName !== "Name") ? previewName : "Rufus Stewart";
        }
        if (!photographer_resume_data.role) {
            photographer_resume_data.role = (previewRole && previewRole !== "Job Role" && previewRole !== "Role") ? previewRole : "Photographer";
        }
        if (!photographer_resume_data.summary) {
            photographer_resume_data.summary = (previewSummary && previewSummary !== "Summary") ? previewSummary : "My name is Rufus Stewart. I am born in California on 10 oct 1991, I am a professional photographer who have been working in several different companies. I love to travel and capture stories.";
        }
        if (!photographer_resume_data.skills || photographer_resume_data.skills.length === 0) {
            photographer_resume_data.skills = ["Studio Lighting", "Adobe Lightroom", "Image Editing", "Font Design", "Marketing & Brand Strategy"];
        }
        if (!photographer_resume_data.experience || photographer_resume_data.experience.length === 0) {
            photographer_resume_data.experience = [
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
            ];
        }
        if (!photographer_resume_data.education || photographer_resume_data.education.length === 0) {
            photographer_resume_data.education = [
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
            ];
        }
    } catch (e) {
        console.error("Error populating default values:", e);
    }
}

function prefillFormInputs() {
    try {
        const fields = [
            { id: "nameInput", value: "Rufus Stewart", prop: "name" },
            { id: "roleInput", value: "Photographer", prop: "role" },
            { id: "phoneInput", value: "+1 234 567 890", prop: "phone" },
            { id: "emailInput", value: "rufus@example.com", prop: "email" },
            { id: "linkedinInput", value: "linkedin.com/in/rufus", prop: "linkedin" },
            { id: "addressInput", value: "California, USA", prop: "address" }
        ];

        fields.forEach(field => {
            const input = document.getElementById(field.id);
            if (input) {
                if (!input.value.trim()) {
                    input.value = field.value;
                }
                photographer_resume_data[field.prop] = input.value;

                // Trigger the input event to render on preview
                const event = new Event("input", { bubbles: true });
                input.dispatchEvent(event);
            }
        });
    } catch (e) {
        console.error("Error prefilling form inputs:", e);
    }
}

document.addEventListener("DOMContentLoaded", () => {
    // 1. Text Inputs Binding (Safe check + dual keyup/input listeners wrapped in try-catch)
    const bindHelper = (id, prop) => {
        try {
            const el = document.getElementById(id);
            if (el) {
                const handler = (e) => {
                    try {
                        photographer_resume_data[prop] = e.target.value;
                        debouncedRenderPreview();
                        triggerAutosave();
                    } catch (err) {
                        console.error(`Error in event listener handler for ${id}:`, err);
                    }
                };
                el.addEventListener("input", handler);
                el.addEventListener("keyup", handler);
            }
        } catch (err) {
            console.error(`Error setting up event listener for ${id}:`, err);
        }
    };

    bindHelper("nameInput", "name");
    bindHelper("roleInput", "role");
    bindHelper("phoneInput", "phone");
    bindHelper("emailInput", "email");
    bindHelper("linkedinInput", "linkedin");
    bindHelper("addressInput", "address");
    bindHelper("summaryInput", "summary");
    bindHelper("assistantInput", "assistant");

    try {
        const skillsInput = document.getElementById("skillsInput");
        if (skillsInput) {
            const handler = (e) => {
                try {
                    photographer_resume_data.skills = e.target.value.split(",").map(s => s.trim()).filter(s => s !== "");
                    debouncedRenderPreview();
                    triggerAutosave();
                } catch (err) {
                    console.error("Error in skillsInput handler:", err);
                }
            };
            skillsInput.addEventListener("input", handler);
            skillsInput.addEventListener("keyup", handler);
        }
    } catch (err) {
        console.error("Error setting up skillsInput listener:", err);
    }

    // 2. Photo Upload Binding
    try {
        const photoInput = document.getElementById("photoInput");
        if (photoInput) {
            photoInput.addEventListener("change", (e) => {
                try {
                    const file = e.target.files[0];
                    if (file) {
                        const imageURL = URL.createObjectURL(file);
                        const previewPhoto = document.getElementById("previewPhoto");
                        if (previewPhoto) {
                            previewPhoto.onload = () => {
                                URL.revokeObjectURL(imageURL);
                            };
                            previewPhoto.src = imageURL;
                        }
                    }
                } catch (err) {
                    console.error("Error in photoInput change handler:", err);
                }
            });
        }
    } catch (err) {
        console.error("Error setting up photoInput listener:", err);
    }

    // 3. Repeatable Fields Buttons Bindings
    try {
        const addExperienceBtn = document.getElementById("addExperienceBtn");
        if (addExperienceBtn) {
            addExperienceBtn.addEventListener("click", () => {
                try {
                    photographer_resume_data.experience.push({
                        id: generateSafeId("exp"),
                        title: "",
                        company: "",
                        dates: "",
                        desc: ""
                    });
                    renderExperienceCards();
                    renderPreview();
                    triggerAutosave();
                } catch (err) {
                    console.error("Error adding experience:", err);
                }
            });
        }
    } catch (err) {
        console.error("Error setting up addExperienceBtn listener:", err);
    }

    try {
        const addEducationBtn = document.getElementById("addEducationBtn");
        if (addEducationBtn) {
            addEducationBtn.addEventListener("click", () => {
                try {
                    photographer_resume_data.education.push({
                        id: generateSafeId("edu"),
                        degree: "",
                        institution: "",
                        dates: "",
                        desc: ""
                    });
                    renderEducationCards();
                    renderPreview();
                    triggerAutosave();
                } catch (err) {
                    console.error("Error adding education:", err);
                }
            });
        }
    } catch (err) {
        console.error("Error setting up addEducationBtn listener:", err);
    }

    // 4. Customizer Theme Swatches binding
    try {
        const swatches = document.querySelectorAll(".color-swatch");
        swatches.forEach(swatch => {
            swatch.addEventListener("click", () => {
                try {
                    swatches.forEach(s => s.classList.remove("active"));
                    swatch.classList.add("active");
                    const color = swatch.getAttribute("data-color");
                    applyHeaderColor(color);
                } catch (err) {
                    console.error("Error in color swatch click handler:", err);
                }
            });
        });
    } catch (err) {
        console.error("Error setting up swatches listeners:", err);
    }

    // 5. Customizer Font Switcher binding
    try {
        const fontSelector = document.getElementById("fontSelector");
        if (fontSelector) {
            fontSelector.addEventListener("change", (e) => {
                try {
                    const font = e.target.value;
                    applyFont(font);
                } catch (err) {
                    console.error("Error in fontSelector change handler:", err);
                }
            });
        }
    } catch (err) {
        console.error("Error setting up fontSelector listener:", err);
    }

    // 6. Stepper Circle Clicks for Direct Navigation
    try {
        const stepNodes = document.querySelectorAll(".step-node");
        stepNodes.forEach(node => {
            node.addEventListener("click", () => {
                try {
                    const stepNum = parseInt(node.getAttribute("data-step"));
                    jumpToStep(stepNum);
                } catch (err) {
                    console.error("Error in stepNode click handler:", err);
                }
            });
        });
    } catch (err) {
        console.error("Error setting up stepNodes listeners:", err);
    }

    // 7. AI Tools Bindings
    try {
        const aiGenerateSummaryBtn = document.getElementById("aiGenerateSummaryBtn");
        if (aiGenerateSummaryBtn) {
            aiGenerateSummaryBtn.addEventListener("click", handleAISummary);
        }
    } catch (err) {
        console.error("Error setting up aiGenerateSummaryBtn listener:", err);
    }

    try {
        const aiSuggestAssistantBulletsBtn = document.getElementById("aiSuggestAssistantBulletsBtn");
        if (aiSuggestAssistantBulletsBtn) {
            aiSuggestAssistantBulletsBtn.addEventListener("click", handleAIAssistant);
        }
    } catch (err) {
        console.error("Error setting up aiSuggestAssistantBulletsBtn listener:", err);
    }

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
            suggestBtn.addEventListener("click", window.generateAISkills);
            chipsWrapper.appendChild(suggestBtn);
        }
    } catch (err) {
        console.error("Error setting up suggestBtn wrapper:", err);
    }

    // Load drafts or defaults
    loadSavedResume().then(() => {
        try {
            populateDefaultValuesIfEmpty();
            syncStateToForm();
            prefillFormInputs();
            renderExperienceCards();
            renderEducationCards();
            renderPreview();
        } catch (err) {
            console.error("Error during loadSavedResume follow-up sequence:", err);
        }
    }).catch(err => {
        console.error("Error in loadSavedResume promise rejection:", err);
    });

    try {
        updateStepperUI();
    } catch (err) {
        console.error("Error running updateStepperUI during load:", err);
    }

    // Force attach click event listener to EVERY button containing 'Continue', 'Next', or having navigation classes
    try {
        document.querySelectorAll('button').forEach(btn => {
            const btnText = btn.textContent.trim().toLowerCase();
            const hasNextClass = btn.classList.contains('next-btn') || btn.classList.contains('continue-btn') || btn.classList.contains('btn-next');
            if (btnText.includes('continue') || btnText.includes('next') || hasNextClass) {
                btn.type = 'button';
                btn.removeAttribute('onclick');
                btn.addEventListener('click', (e) => {
                    try {
                        e.preventDefault();
                        e.stopPropagation();
                        window.nextStep();
                    } catch (err) {
                        console.error("Error in brute force next step click listener:", err);
                    }
                });
            }

            const hasBackClass = btn.classList.contains('back-btn') || btn.classList.contains('btn-back');
            if (btnText.includes('back') || hasBackClass) {
                btn.type = 'button';
                btn.removeAttribute('onclick');
                btn.addEventListener('click', (e) => {
                    try {
                        e.preventDefault();
                        e.stopPropagation();
                        window.prevStep();
                    } catch (err) {
                        console.error("Error in brute force back click listener:", err);
                    }
                });
            }
        });
    } catch (e) {
        console.error("Error binding brute force button listeners:", e);
    }
});

// ==========================================
// SECURITY & DATA INTEGRITY HELPERS
// ==========================================
function escapeHTML(str) {
    if (typeof str !== 'string') return str || '';
    return str.replace(/[&<>'"]/g, 
        tag => ({
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            "'": '&#39;',
            '"': '&quot;'
        }[tag] || tag)
    );
}

function debounce(func, wait) {
    let timeout;
    return function (...args) {
        const context = this;
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(context, args), wait);
    };
}

const debouncedRenderPreview = debounce(renderPreview, 150);

function isValidEmail(email) {
    if (!email) return true;
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function isValidPhone(phone) {
    if (!phone) return true;
    return /^\+?[0-9\s\-()]{7,20}$/.test(phone);
}

function isValidURL(url) {
    if (!url) return true;
    try {
        const formatted = url.match(/^https?:\/\//) ? url : 'http://' + url;
        new URL(formatted);
        return true;
    } catch (_) {
        return false;
    }
}

function generateSafeId(prefix) {
    if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
        return prefix + "-" + crypto.randomUUID();
    }
    return prefix + "-" + Math.random().toString(36).substr(2, 9);
}

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

    toast.innerHTML = `<i class="fa-solid ${escapeHTML(icon)}"></i> <span>${escapeHTML(message)}</span>`;
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
    try {
        // 1. Contact info with safe check
        const previewName = document.getElementById("previewName");
        if (previewName) previewName.textContent = photographer_resume_data.name || "Full Name";

        const previewRole = document.getElementById("previewRole");
        if (previewRole) previewRole.textContent = photographer_resume_data.role || "Job Role";

        const previewPhone = document.getElementById("previewPhone");
        if (previewPhone) previewPhone.textContent = photographer_resume_data.phone || "Phone";

        const previewEmail = document.getElementById("previewEmail");
        if (previewEmail) previewEmail.textContent = photographer_resume_data.email || "Email";

        const previewLinkedin = document.getElementById("previewLinkedin");
        if (previewLinkedin) previewLinkedin.textContent = photographer_resume_data.linkedin || "LinkedIn";

        const previewAddress = document.getElementById("previewAddress");
        if (previewAddress) previewAddress.textContent = photographer_resume_data.address || "Address";

        // 2. Summary
        const previewSummary = document.getElementById("previewSummary");
        if (previewSummary) previewSummary.textContent = photographer_resume_data.summary || "Summary";

        // 3. Assistant Highlights (Using DOM elements to prevent XSS)
        const previewAssistant = document.getElementById("previewAssistant");
        if (previewAssistant) {
            previewAssistant.innerHTML = "";
            if (photographer_resume_data.assistant) {
                const lines = photographer_resume_data.assistant.split("\n").filter(l => l.trim() !== "");
                const ul = document.createElement("ul");
                lines.forEach(line => {
                    const li = document.createElement("li");
                    li.textContent = line.replace(/^[•\-\*]\s*/, '').trim();
                    ul.appendChild(li);
                });
                previewAssistant.appendChild(ul);
            } else {
                previewAssistant.textContent = "Assistant details.";
            }
        }

        // 4. Education (Dynamic list using textContent for security)
        const eduPreview = document.getElementById("previewEducation");
        if (eduPreview) {
            eduPreview.innerHTML = "";
            if (photographer_resume_data.education && photographer_resume_data.education.length > 0) {
                photographer_resume_data.education.forEach(edu => {
                    const item = document.createElement("div");
                    item.className = "preview-item";

                    const header = document.createElement("div");
                    header.className = "preview-item-header";
                    
                    const titleSpan = document.createElement("span");
                    titleSpan.className = "preview-item-title";
                    titleSpan.textContent = edu.degree || "Degree / Certificate";
                    
                    const metaSpan = document.createElement("span");
                    metaSpan.className = "preview-item-meta";
                    metaSpan.textContent = edu.dates || "Dates";
                    
                    header.appendChild(titleSpan);
                    header.appendChild(metaSpan);
                    item.appendChild(header);

                    const orgRow = document.createElement("div");
                    orgRow.className = "preview-item-org-row";
                    
                    const orgSpan = document.createElement("span");
                    orgSpan.className = "preview-item-org";
                    orgSpan.textContent = edu.institution || "Institution / School";
                    
                    orgRow.appendChild(orgSpan);
                    item.appendChild(orgRow);

                    if (edu.desc) {
                        const descDiv = document.createElement("div");
                        descDiv.className = "preview-item-desc";
                        descDiv.textContent = edu.desc;
                        item.appendChild(descDiv);
                    }

                    eduPreview.appendChild(item);
                });
            } else {
                eduPreview.textContent = "Education details.";
            }
        }

        // 5. Skills
        const skillsList = document.getElementById("previewSkills");
        if (skillsList) {
            skillsList.innerHTML = "";
            if (photographer_resume_data.skills && photographer_resume_data.skills.length > 0) {
                photographer_resume_data.skills.forEach(skill => {
                    if (skill.trim() !== "") {
                        const li = document.createElement("li");
                        li.textContent = "• " + skill.trim();
                        skillsList.appendChild(li);
                    }
                });
            }
        }

        // 6. Experience (Dynamic list using DOM elements for safety)
        const expPreview = document.getElementById("previewExperience");
        if (expPreview) {
            expPreview.innerHTML = "";
            if (photographer_resume_data.experience && photographer_resume_data.experience.length > 0) {
                photographer_resume_data.experience.forEach(exp => {
                    const item = document.createElement("div");
                    item.className = "preview-item";

                    const header = document.createElement("div");
                    header.className = "preview-item-header";
                    
                    const titleSpan = document.createElement("span");
                    titleSpan.className = "preview-item-title";
                    titleSpan.textContent = exp.title || "Job Title";
                    
                    const metaSpan = document.createElement("span");
                    metaSpan.className = "preview-item-meta";
                    metaSpan.textContent = exp.dates || "Dates";
                    
                    header.appendChild(titleSpan);
                    header.appendChild(metaSpan);
                    item.appendChild(header);

                    const orgRow = document.createElement("div");
                    orgRow.className = "preview-item-org-row";
                    
                    const orgSpan = document.createElement("span");
                    orgSpan.className = "preview-item-org";
                    orgSpan.textContent = exp.company || "Company / Organization";
                    
                    orgRow.appendChild(orgSpan);
                    item.appendChild(orgRow);

                    if (exp.desc) {
                        const descDiv = document.createElement("div");
                        descDiv.className = "preview-item-desc";
                        
                        const lines = exp.desc.split("\n").filter(l => l.trim() !== "");
                        const ul = document.createElement("ul");
                        lines.forEach(line => {
                            const li = document.createElement("li");
                            li.textContent = line.replace(/^[•\-\*]\s*/, '').trim();
                            ul.appendChild(li);
                        });
                        descDiv.appendChild(ul);
                        item.appendChild(descDiv);
                    }

                    expPreview.appendChild(item);
                });
            } else {
                expPreview.textContent = "Experience details.";
            }
        }
    } catch (err) {
        console.error("Error in renderPreview:", err);
    }
}

function renderExperienceCards() {
    const container = document.getElementById("experienceContainer");
    if (!container) return;
    container.innerHTML = "";
    photographer_resume_data.experience.forEach((exp, index) => {
        const card = document.createElement("div");
        card.className = "repeatable-card";
        
        const titleVal = escapeHTML(exp.title);
        const companyVal = escapeHTML(exp.company);
        const datesVal = escapeHTML(exp.dates);
        const descVal = escapeHTML(exp.desc);
        const idVal = escapeHTML(exp.id);

        card.innerHTML = `
            <div class="repeatable-card-header">
                <span class="repeatable-card-title">Experience #${index + 1}</span>
                <button type="button" class="card-delete-btn" onclick="deleteExperience('${idVal}')">Delete</button>
            </div>
            <div class="row-2">
                <div class="input-group">
                    <label>Job Title</label>
                    <input type="text" id="exp-title-${idVal}" value="${titleVal}" placeholder="e.g. Lead Photographer" oninput="updateExperience('${idVal}', 'title', this.value)">
                </div>
                <div class="input-group">
                    <label>Company / Organization</label>
                    <input type="text" id="exp-company-${idVal}" value="${companyVal}" placeholder="e.g. Studio Vista" oninput="updateExperience('${idVal}', 'company', this.value)">
                </div>
            </div>
            <div class="input-group">
                <label>Start & End Dates / Year</label>
                <input type="text" value="${datesVal}" placeholder="e.g. 2018 - Present" oninput="updateExperience('${idVal}', 'dates', this.value)">
            </div>
            <div class="input-group">
                <label>Description / Bullet Points</label>
                <div class="textarea-ai-wrapper">
                    <textarea id="exp-desc-${idVal}" placeholder="• Accomplishment 1&#10;• Accomplishment 2" style="height: 80px;" oninput="updateExperience('${idVal}', 'desc', this.value)">${descVal}</textarea>
                    <button type="button" id="ai-btn-${idVal}" class="btn-ai-action" onclick="handleAIExperience('${idVal}')">✨ AI Suggest Action Bullets</button>
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
    photographer_resume_data.education.forEach((edu, index) => {
        const card = document.createElement("div");
        card.className = "repeatable-card";
        
        const degreeVal = escapeHTML(edu.degree);
        const institutionVal = escapeHTML(edu.institution);
        const datesVal = escapeHTML(edu.dates);
        const descVal = escapeHTML(edu.desc);
        const idVal = escapeHTML(edu.id);

        card.innerHTML = `
            <div class="repeatable-card-header">
                <span class="repeatable-card-title">Education #${index + 1}</span>
                <button type="button" class="card-delete-btn" onclick="deleteEducation('${idVal}')">Delete</button>
            </div>
            <div class="row-2">
                <div class="input-group">
                    <label>Title / Degree</label>
                    <input type="text" value="${degreeVal}" placeholder="e.g. Bachelor of Fine Arts" oninput="updateEducation('${idVal}', 'degree', this.value)">
                </div>
                <div class="input-group">
                    <label>Company / Institution</label>
                    <input type="text" value="${institutionVal}" placeholder="e.g. Academy of Art" oninput="updateEducation('${idVal}', 'institution', this.value)">
                </div>
            </div>
            <div class="input-group">
                <label>Dates / Year</label>
                <input type="text" value="${datesVal}" placeholder="e.g. 2012 - 2016" oninput="updateEducation('${idVal}', 'dates', this.value)">
            </div>
            <div class="input-group">
                <label>Description / Details</label>
                <textarea placeholder="Specialized in portrait and lighting styles..." style="height: 60px;" oninput="updateEducation('${idVal}', 'desc', this.value)">${descVal}</textarea>
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
// PYTHONIC TEXT SANITIZER
// ==========================================
function cleanTextResponse(rawText) {
    if (!rawText) return "";
    return rawText
        .replace(/\(.*?\)/g, "")
        .replace(/^(Here's|Here is|Sure|Certainly|Summary|Output|Based on)[^:]*:\s*/i, "")
        .replace(/^["']|["']$/g, "")
        .trim();
}

// ==========================================
// LIVE LLM API CONNECTION LOGIC (GROQ llama-3.3-70b-versatile)
// ==========================================
async function callLiveAI(promptTextOrMessages, systemContext = "", onChunk = null, temperature = 0.7, seed = null) {
    const GROQ_API_KEY = localStorage.getItem("GROQ_API_KEY") || "";
    const endpoint = "https://api.groq.com/openai/v1/chat/completions";

    let sysCtx = systemContext || "You are a direct resume-generation engine. Your ONLY output must be the final resume text. STRICT RULES: Never say 'Here is', 'Sure', 'Based on', or 'Summary:'. Never write notes in parentheses. Strip birth dates, locations, and irrelevant personal details automatically.";
    if (systemContext && !systemContext.includes("CRITICAL RULE") && !systemContext.includes("STRICT RULES")) {
        sysCtx += " STRICT RULES: Never say 'Here is', 'Sure', 'Based on', or 'Summary:'. Never write notes in parentheses. Strip birth dates, locations, and irrelevant personal details automatically.";
    }

    let messagesPayload;
    if (Array.isArray(promptTextOrMessages)) {
        messagesPayload = promptTextOrMessages;
    } else {
        const isSummaryRequest = !systemContext || systemContext.toLowerCase().includes("summary") || systemContext.toLowerCase().includes("resume writer");
        if (isSummaryRequest) {
            const userInput = promptTextOrMessages;
            messagesPayload = [
                {
                    role: "system",
                    content: "You are a professional resume parser and generator. ABSOLUTE RULES: \n1. BANNED BUZZWORDS: 'Results-driven', 'proven track record', 'passionate', 'dynamic'.\n2. OUTPUT ONLY RAW SUMMARY TEXT. Zero intros, zero quotes, zero explanations in brackets.\n3. Extract specific details (experience, tools, photography styles) and weave them into 2-3 clean, authentic sentences."
                },
                {
                    role: "user",
                    content: "Name: Rufus Stewart. Input: My name is Rufus Stewart. I am born in California on 10 oct 1991, I am a professional photographer who have been working in several different companies. I love to travel and capture stories."
                },
                {
                    role: "assistant",
                    content: "Commercial and travel photographer with extensive experience managing creative projects across diverse company environments. Specialized in location-based visual storytelling, studio lighting setups, and Adobe Lightroom post-production."
                },
                {
                    role: "user",
                    content: `User Input: '${userInput}'. Seed: ${Date.now()}. Generate an authentic, non-generic summary:`
                }
            ];
        } else {
            messagesPayload = [
                {
                    role: "system",
                    content: sysCtx
                },
                {
                    role: "user",
                    content: promptTextOrMessages
                }
            ];
        }
    }

    const response = await fetch(endpoint, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${GROQ_API_KEY}`
        },
        body: JSON.stringify({
            model: "llama-3.3-70b-versatile",
            messages: messagesPayload,
            temperature: temperature,
            max_tokens: 130,
            seed: seed !== null ? seed : undefined,
            stream: !!onChunk
        })
    });

    if (!response.ok) {
        const err = await response.json().catch(() => ({}));
        throw new Error(err.error?.message || response.statusText || "Groq API error");
    }

    if (onChunk) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder("utf-8");
        let buffer = "";
        let accumulatedText = "";

        while (true) {
            const { value, done } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop();

            for (const line of lines) {
                const cleaned = line.trim();
                if (!cleaned || !cleaned.startsWith("data: ")) continue;
                const dataStr = cleaned.slice(6).trim();
                if (dataStr === "[DONE]") continue;
                try {
                    const parsed = JSON.parse(dataStr);
                    const content = parsed.choices[0]?.delta?.content;
                    if (content) {
                        accumulatedText += content;
                        const cleanedText = cleanTextResponse(accumulatedText);
                        onChunk(cleanedText, content);
                    }
                } catch (err) {
                    // Ignore JSON parsing errors for partial lines
                }
            }
        }

        // Clean up remaining buffer
        if (buffer.trim().startsWith("data: ")) {
            const dataStr = buffer.trim().slice(6).trim();
            if (dataStr !== "[DONE]") {
                try {
                    const parsed = JSON.parse(dataStr);
                    const content = parsed.choices[0]?.delta?.content;
                    if (content) {
                        accumulatedText += content;
                        const cleanedText = cleanTextResponse(accumulatedText);
                        onChunk(cleanedText, content);
                    }
                } catch (e) { }
            }
        }
        return cleanTextResponse(accumulatedText);
    } else {
        const data = await response.json();
        if (data.choices && data.choices[0] && data.choices[0].message) {
            const rawText = data.choices[0].message.content;
            return cleanTextResponse(rawText);
        }
        throw new Error("Invalid response format from Groq API");
    }
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
// DYNAMIC AI SKILLS SUGGESTION GENERATOR
// ==========================================
async function generateAISkills() {
    const button = document.getElementById("aiSuggestSkillsBtn");
    const container = document.getElementById("suggestedSkillChips");
    if (!container) return;

    await executeWithLoadingState(button, async () => {
        const role = photographer_resume_data.role || "Photographer";
        const name = photographer_resume_data.name || "Rufus Stewart";
        const summary = photographer_resume_data.summary || "";

        try {
            const response = await fetch("http://127.0.0.1:8000/api/generate-skills", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    role: role,
                    name: name,
                    summary: summary
                })
            });

            if (!response.ok) {
                const errDetail = await response.json().catch(() => ({}));
                throw new Error(errDetail.detail || response.statusText || "Backend failure");
            }

            const data = await response.json();
            if (data.status === "success") {
                const result = data.skills;
                const skills = Array.isArray(result)
                    ? result
                    : result.split(",").map(s => s.replace(/^[-\d\.\s•\*]+/, "").trim()).filter(s => s !== "");

                if (skills.length > 0) {
                    container.innerHTML = "";
                    skills.forEach(skillName => {
                        const chip = document.createElement("span");
                        chip.className = "skill-chip";
                        chip.setAttribute("data-skill", skillName);
                        chip.textContent = skillName;
                        chip.addEventListener("click", () => {
                            const normalizedSkills = photographer_resume_data.skills.map(s => s.trim().toLowerCase());
                            if (!normalizedSkills.includes(skillName.toLowerCase())) {
                                photographer_resume_data.skills.push(skillName);
                                document.getElementById("skillsInput").value = photographer_resume_data.skills.join(", ");
                                renderPreview();
                                triggerAutosave();
                            }
                        });
                        container.appendChild(chip);
                    });
                    showToast("Skills suggestions updated via Python Backend!", "success");
                } else {
                    showToast("No skills were returned by the Backend.", "warning");
                }
            } else {
                throw new Error(data.detail || "Unexpected backend response status");
            }
        } catch (error) {
            console.error("AI Skills Suggestion Failure:", error);
            showToast(`API Failed: ${error.message}`, "error");
        }
    });
}
window.generateAISkills = generateAISkills;

// ==========================================
// SELF-CONTAINED GROQ API FALLBACK UTILITY
// ==========================================
async function callLiveAPI(promptText, sectionType = "summary") {
    const GROQ_API_KEY = localStorage.getItem("GROQ_API_KEY") || "";
    const endpoint = "https://api.groq.com/openai/v1/chat/completions";

    let section_instruction = "";
    if (sectionType === "summary") {
        section_instruction = "Generate a crisp 2-3 sentence resume summary centered strictly on the facts in the user prompt.";
    } else if (sectionType === "experience_bullets") {
        section_instruction = 
            "Convert the user prompt into 3 powerful, high-impact bullet points using strong action verbs (e.g., Developed, Managed, Spearheaded). " +
            "Output ONLY raw bullet points starting with standard dashes (e.g., - Developed...).";
    } else if (sectionType === "suggest_bullets") {
        section_instruction = 
            "Based on the role/text provided, generate 3 strategic industry-standard achievement bullets. " +
            "Output ONLY raw bullet points starting with standard dashes (e.g., - Spearheaded...).";
    } else {
        section_instruction = "Generate a professional resume summary.";
    }

    const response = await fetch(endpoint, {
        method: "POST",
        headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + GROQ_API_KEY
        },
        body: JSON.stringify({
            model: "llama-3.3-70b-versatile",
            messages: [
                {
                    role: "system",
                    content: "You are a professional resume generator. ABSOLUTE RULES: Banned words: 'Results-driven', 'proven track record', 'passionate', 'dynamic'. " +
                             "OUTPUT ONLY RAW SUMMARY TEXT. Zero intros, zero quotes, zero bracketed notes.\n\nTask: " + section_instruction
                },
                {
                    role: "user",
                    content: promptText
                }
            ],
            temperature: 0.85,
            max_tokens: 130
        })
    });

if (!response.ok) {
    const err = await response.json().catch(() => ({}));
    throw new Error(err.error?.message || response.statusText || "Groq API error");
}

const data = await response.json();
if (data.choices && data.choices[0] && data.choices[0].message) {
    const rawText = data.choices[0].message.content;

    // Full Regex text sanitization on the Groq output before returning it
    if (!rawText) return "";
    return rawText
        .replace(/\(.*?\)/g, "") // Strip bracketed explanations
        .replace(/^(Here's|Here is|Sure|Certainly|Summary|Output)[^:]*:\s*/i, "") // Strip conversational prefixes
        .replace(/^["']|["']$/g, "") // Strip leftover quote marks
        .trim();
}
throw new Error("Invalid response format from Groq API");
}

// ==========================================
// SMART CONTEXT-AWARE AI CHATGPT TRIGGERS
// ==========================================
async function handleAISummary() {
    const button = document.getElementById("aiGenerateSummaryBtn");
    const summaryInput = document.getElementById("summaryInput");
    const previewSummary = document.getElementById("previewSummary");
    const placeholderText = summaryInput.getAttribute('placeholder') || "";
    const previewText = previewSummary ? previewSummary.innerText.trim() : "";
    const promptText = summaryInput.value.trim() || placeholderText || previewText;

    await executeWithLoadingState(button, async () => {
        const originalValue = summaryInput.value;
        let cleanSummary = "";
        let usedFallback = false;

        try {
            const response = await fetch("http://127.0.0.1:8000/api/generate-summary", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    user_input: promptText,
                    section_type: "summary"
                })
            });

            if (!response.ok) {
                const errDetail = await response.json().catch(() => ({}));
                throw new Error(errDetail.detail || response.statusText || "Backend failure");
            }

            const data = await response.json();
            if (data.status === "success") {
                cleanSummary = data.summary;
                console.log("⚡ Summary generated via Python Backend");
            } else {
                throw new Error(data.detail || "Unexpected backend response status");
            }
        } catch (error) {
            console.warn("⚠️ Python Backend offline. Seamlessly falling back to Direct Groq API...", error);
            usedFallback = true;

            try {
                cleanSummary = await callLiveAPI(promptText, "summary");
            } catch (fallbackError) {
                console.error("Direct Groq Fallback Failure:", fallbackError);
                // Restore original input value so the user doesn't lose their text
                summaryInput.value = originalValue;
                showToast(`AI Generation failed: ${fallbackError.message}`, "error");
                return;
            }
        }

        // Inject the clean processed response directly into #summaryInput and #previewSummary
        summaryInput.value = cleanSummary;
        if (previewSummary) {
            previewSummary.textContent = cleanSummary;
        }

        // Sync resume state
        photographer_resume_data.summary = cleanSummary;

        const successText = usedFallback
            ? "Summary generated via direct Groq API (Python backend offline)."
            : "Summary generated successfully via Python Backend!";

        showToast(successText, usedFallback ? "warning" : "success");
        triggerAutosave();
    });
}

async function handleAIAssistant() {
    const button = document.getElementById("aiSuggestAssistantBulletsBtn");
    const input = document.getElementById("assistantInput");
    const userText = input.value.trim();
    const placeholderText = input.getAttribute('placeholder') || "";
    const promptText = userText || placeholderText;

    await executeWithLoadingState(button, async () => {
        const originalValue = input.value;
        let cleanText = "";
        let usedFallback = false;

        try {
            const response = await fetch("http://127.0.0.1:8000/api/generate-summary", {
                method: "POST",
                headers: {
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    user_input: promptText,
                    section_type: "suggest_bullets"
                })
            });

            if (!response.ok) {
                const errDetail = await response.json().catch(() => ({}));
                throw new Error(errDetail.detail || response.statusText || "Backend failure");
            }

            const data = await response.json();
            if (data.status === "success") {
                cleanText = data.summary;
                console.log("⚡ Assistant bullets generated via Python Backend");
            } else {
                throw new Error(data.detail || "Unexpected backend response status");
            }
        } catch (error) {
            console.warn("⚠️ Python Backend offline. Seamlessly falling back to Direct Groq API...", error);
            usedFallback = true;

            try {
                cleanText = await callLiveAPI(promptText, "suggest_bullets");
            } catch (fallbackError) {
                console.error("Direct Groq Fallback Failure:", fallbackError);
                input.value = originalValue;
                showToast(`AI Generation failed: ${fallbackError.message}`, "error");
                return;
            }
        }

        // Apply cleanText to the input/textarea and preview
        input.value = cleanText;
        photographer_resume_data.assistant = cleanText;
        renderPreview();

        const successText = usedFallback
            ? "Assistant bullets generated via direct Groq API (Python backend offline)."
            : "Assistant bullets generated successfully via Python Backend!";
        showToast(successText, usedFallback ? "warning" : "success");
        triggerAutosave();
    });
}

window.handleAIExperience = async function (id) {
    const button = document.getElementById(`ai-btn-${id}`);
    const input = document.getElementById(`exp-desc-${id}`);
    const userText = input.value.trim();
    const placeholderText = input.getAttribute('placeholder') || "";
    const promptText = userText || placeholderText;

    await executeWithLoadingState(button, async () => {
        const exp = photographer_resume_data.experience.find(e => e.id === id);
        if (exp) {
            const originalValue = input.value;
            let cleanText = "";
            let usedFallback = false;

            try {
                const response = await fetch("http://127.0.0.1:8000/api/generate-summary", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        user_input: promptText,
                        section_type: "experience_bullets"
                    })
                });

                if (!response.ok) {
                    const errDetail = await response.json().catch(() => ({}));
                    throw new Error(errDetail.detail || response.statusText || "Backend failure");
                }

                const data = await response.json();
                if (data.status === "success") {
                    cleanText = data.summary;
                    console.log("⚡ Experience bullets generated via Python Backend");
                } else {
                    throw new Error(data.detail || "Unexpected backend response status");
                }
            } catch (error) {
                console.warn("⚠️ Python Backend offline. Seamlessly falling back to Direct Groq API...", error);
                usedFallback = true;

                try {
                    cleanText = await callLiveAPI(promptText, "experience_bullets");
                } catch (fallbackError) {
                    console.error("Direct Groq Fallback Failure:", fallbackError);
                    input.value = originalValue;
                    showToast(`AI Generation failed: ${fallbackError.message}`, "error");
                    return;
                }
            }

            // Apply cleanText to the input/textarea and sync with preview
            input.value = cleanText;
            exp.desc = cleanText;
            renderPreview();

            const successText = usedFallback
                ? "Experience bullets generated via direct Groq API (Python backend offline)."
                : "Experience bullets generated successfully via Python Backend!";
            showToast(successText, usedFallback ? "warning" : "success");
            triggerAutosave();
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

function toggleStepVisibility() {
    try {
        for (let i = 1; i <= totalSteps; i++) {
            const stepEl = document.getElementById("step" + i);
            if (stepEl) {
                if (i === currentStep) {
                    stepEl.classList.add("active");
                    stepEl.style.display = "block";
                } else {
                    stepEl.classList.remove("active");
                    stepEl.style.display = "none";
                }
            }
        }
    } catch (e) {
        console.error("Error toggling step visibility:", e);
    }
}

window.nextStep = function () {
    try {
        if (currentStep >= totalSteps) return;
        currentStep++;
        toggleStepVisibility();
        updateStepperUI();
        triggerAutosave();
        console.log("Navigating to step:", currentStep);
    } catch (err) {
        console.error("Navigation error in nextStep:", err);
    }
};

window.prevStep = function () {
    try {
        if (currentStep <= 1) return;
        currentStep--;
        toggleStepVisibility();
        updateStepperUI();
        console.log("Navigating to step:", currentStep);
    } catch (err) {
        console.error("Navigation error in prevStep:", err);
    }
};

window.jumpToStep = function (stepNum) {
    try {
        if (stepNum < 1 || stepNum > totalSteps) return;
        currentStep = stepNum;
        toggleStepVisibility();
        updateStepperUI();
        console.log("Navigating to step:", currentStep);
    } catch (err) {
        console.error("Navigation error in jumpToStep:", err);
    }
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
    if (!supabase || typeof supabase.from === 'undefined') {
        console.warn("Supabase client is not initialized.");
        return;
    }

    // Input Format Validation Checks
    if (photographer_resume_data.email && !isValidEmail(photographer_resume_data.email)) {
        showToast("Invalid email format. Please check the email field.", "warning");
        return;
    }
    if (photographer_resume_data.phone && !isValidPhone(photographer_resume_data.phone)) {
        showToast("Invalid phone format. Please check the phone field.", "warning");
        return;
    }
    if (photographer_resume_data.linkedin && !isValidURL(photographer_resume_data.linkedin)) {
        showToast("Invalid LinkedIn URL format. Please check the LinkedIn URL field.", "warning");
        return;
    }

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
    if (typeof html2pdf === "undefined") {
        alert("The PDF export library (html2pdf) is not loaded. Please check your internet connection.");
        return;
    }
    const element = document.getElementById("resume-pdf-target");
    if (!element) {
        console.error("Resume target element not found for PDF export.");
        return;
    }
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

    try {
        html2pdf().set(options).from(element).save();
    } catch (e) {
        console.error("PDF generation failed:", e);
    }
};