// Centralized AI Service Utilities for Resume Builders (ai-service.js)
(function () {
    // Unified global toast fallback
    function showToast(message, type = "info") {
        let container = document.getElementById("toastContainer");
        if (!container) {
            container = document.createElement("div");
            container.id = "toastContainer";
            container.style.position = "fixed";
            container.style.bottom = "24px";
            container.style.right = "24px";
            container.style.zIndex = "9999999";
            container.style.display = "flex";
            container.style.flexDirection = "column";
            container.style.gap = "12px";
            document.body.appendChild(container);
        }

        const toast = document.createElement("div");
        toast.style.padding = "14px 22px";
        toast.style.borderRadius = "10px";
        toast.style.color = "#ffffff";
        toast.style.fontSize = "0.875rem";
        toast.style.fontWeight = "600";
        toast.style.boxShadow = "0 10px 15px -3px rgba(0, 0, 0, 0.2)";
        toast.style.display = "flex";
        toast.style.alignItems = "center";
        toast.style.gap = "10px";
        toast.style.animation = "slideInToast 0.3s cubic-bezier(0.16, 1, 0.3, 1), fadeOutToast 0.3s ease 2.7s forwards";
        toast.style.fontFamily = '"Plus Jakarta Sans", "Inter", sans-serif';

        let icon = "ℹ️";
        let bg = "#2563eb";
        if (type === "success") {
            bg = "#059669";
            icon = "✅";
        } else if (type === "error") {
            bg = "#dc2626";
            icon = "❌";
        } else if (type === "warning") {
            bg = "#d97706";
            icon = "⚠️";
        }

        toast.style.backgroundColor = bg;
        toast.innerHTML = `<span style="font-size: 1.1rem;">${icon}</span> <span>${message}</span>`;

        if (!document.getElementById('ai-toast-animation-styles')) {
            const styleSheet = document.createElement('style');
            styleSheet.id = 'ai-toast-animation-styles';
            styleSheet.innerText = `
                @keyframes slideInToast {
                    from { transform: translateY(20px) scale(0.95); opacity: 0; }
                    to { transform: translateY(0) scale(1); opacity: 1; }
                }
                @keyframes fadeOutToast {
                    from { opacity: 1; }
                    to { opacity: 0; }
                }
            `;
            document.head.appendChild(styleSheet);
        }

        container.appendChild(toast);
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }

    // Set globally
    window.showToast = window.showToast || showToast;
})();
