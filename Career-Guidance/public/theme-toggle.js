document.addEventListener("DOMContentLoaded", () => {
    const themeToggleBtn = document.getElementById("themeToggle");

    function applyTheme(theme) {
        document.documentElement.setAttribute("data-theme", theme);
        if (document.body) {
            document.body.setAttribute("data-theme", theme);
        }
        localStorage.setItem("theme", theme);
        
        if (themeToggleBtn) {
            if (theme === "dark") {
                themeToggleBtn.innerHTML = "☀️ Light";
                themeToggleBtn.classList.add("dark");
            } else {
                themeToggleBtn.innerHTML = "🌙 Dark";
                themeToggleBtn.classList.remove("dark");
            }
        }
    }

    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
        const newTheme = currentTheme === "dark" ? "light" : "dark";
        applyTheme(newTheme);
    }

    if (themeToggleBtn) {
        themeToggleBtn.addEventListener("click", toggleTheme);
    }

    // Initialize theme based on localStorage, default to light
    const savedTheme = localStorage.getItem("theme") || "light";
    applyTheme(savedTheme);
});
