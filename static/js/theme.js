// Apply theme immediately to prevent flash
(function () {
    const saved = localStorage.getItem("theme");
    if (saved === "dark" || (!saved && window.matchMedia("(prefers-color-scheme: dark)").matches)) {
        document.documentElement.classList.add("dark");
    }
})();

document.addEventListener("DOMContentLoaded", function () {
    const toggle = document.getElementById("theme-toggle");
    const iconLight = document.getElementById("theme-icon-light");
    const iconDark = document.getElementById("theme-icon-dark");

    function updateIcons() {
        const isDark = document.documentElement.classList.contains("dark");
        // Show sun icon in dark mode (click to go light), moon icon in light mode (click to go dark)
        iconLight.classList.toggle("hidden", !isDark);
        iconDark.classList.toggle("hidden", isDark);
    }

    updateIcons();

    toggle.addEventListener("click", function () {
        const isDark = document.documentElement.classList.toggle("dark");
        localStorage.setItem("theme", isDark ? "dark" : "light");
        updateIcons();
    });
});
