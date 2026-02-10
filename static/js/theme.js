// Theme toggle setup (dark class is applied inline in base.html to prevent flash)
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
