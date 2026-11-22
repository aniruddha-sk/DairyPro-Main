
/* =========================================================
   DairyMitr SuperAdmin
   File: static/js/main.js
   Common UI Interactions
========================================================= */

"use strict";


/* =========================================================
   DOM READY
========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    initializeSidebar();
    initializeProfileDropdown();
    initializePasswordToggle();
    initializeFlashMessages();
    initializeSearchClear();
    initializeCurrentYear();
    initializeTooltips();
    initializeConfirmActions();
    initializeFormLoading();

});


/* =========================================================
   SIDEBAR
========================================================= */

function initializeSidebar() {

    const appWrapper = document.getElementById("appWrapper");
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("sidebarOverlay");

    const toggleBtn = document.getElementById("sidebarToggleBtn");
    const closeBtn = document.getElementById("sidebarCloseBtn");

    if (!sidebar || !appWrapper) return;


    function openSidebar() {

        appWrapper.classList.add("sidebar-open");
        sidebar.classList.add("active");

        if (overlay) {
            overlay.classList.add("show");
        }

        document.body.classList.add("sidebar-active");

    }


    function closeSidebar() {

        appWrapper.classList.remove("sidebar-open");
        sidebar.classList.remove("active");

        if (overlay) {
            overlay.classList.remove("show");
        }

        document.body.classList.remove("sidebar-active");

    }


    if (toggleBtn) {
        toggleBtn.addEventListener("click", function () {

            const isOpen = appWrapper.classList.contains("sidebar-open");

            if (isOpen) {
                closeSidebar();
            } else {
                openSidebar();
            }

        });
    }


    if (closeBtn) {
        closeBtn.addEventListener("click", closeSidebar);
    }


    if (overlay) {
        overlay.addEventListener("click", closeSidebar);
    }


    // Close sidebar after selecting a navigation link on mobile.

    sidebar.querySelectorAll(".sidebar-nav a").forEach(function (link) {

        link.addEventListener("click", function () {

            if (window.innerWidth <= 992) {
                closeSidebar();
            }

        });

    });


    // Close sidebar using Escape key.

    document.addEventListener("keydown", function (event) {

        if (event.key === "Escape") {
            closeSidebar();
        }

    });


    // Reset mobile sidebar when switching to desktop.

    window.addEventListener("resize", function () {

        if (window.innerWidth > 992) {
            closeSidebar();
        }

    });

}


/* =========================================================
   PROFILE DROPDOWN
========================================================= */

function initializeProfileDropdown() {

    const dropdownBtn = document.getElementById("profileDropdownBtn");
    const dropdownMenu = document.getElementById("profileDropdownMenu");

    if (!dropdownBtn || !dropdownMenu) return;


    function closeDropdown() {

        dropdownMenu.classList.remove("show");
        dropdownBtn.setAttribute("aria-expanded", "false");

    }


    dropdownBtn.addEventListener("click", function (event) {

        event.stopPropagation();

        const isOpen = dropdownMenu.classList.contains("show");

        if (isOpen) {

            closeDropdown();

        } else {

            dropdownMenu.classList.add("show");
            dropdownBtn.setAttribute("aria-expanded", "true");

        }

    });


    document.addEventListener("click", function (event) {

        if (
            !dropdownMenu.contains(event.target) &&
            !dropdownBtn.contains(event.target)
        ) {
            closeDropdown();
        }

    });


    document.addEventListener("keydown", function (event) {

        if (event.key === "Escape") {
            closeDropdown();
        }

    });

}


/* =========================================================
   PASSWORD SHOW / HIDE
========================================================= */

function initializePasswordToggle() {

    const passwordInput = document.getElementById("loginPassword");
    const toggleBtn = document.getElementById("loginPasswordToggle");
    const toggleIcon = document.getElementById("passwordToggleIcon");

    if (!passwordInput || !toggleBtn) return;


    toggleBtn.addEventListener("click", function () {

        const isPassword = passwordInput.type === "password";

        passwordInput.type = isPassword ? "text" : "password";


        if (toggleIcon) {

            toggleIcon.classList.toggle("bi-eye", !isPassword);
            toggleIcon.classList.toggle("bi-eye-slash", isPassword);

        }


        toggleBtn.setAttribute(
            "aria-label",
            isPassword ? "Hide password" : "Show password"
        );

    });

}


/* =========================================================
   FLASH MESSAGES
========================================================= */

function initializeFlashMessages() {

    const flashContainer = document.getElementById("flashMessageContainer");

    if (!flashContainer) return;


    const alerts = flashContainer.querySelectorAll(".alert");


    alerts.forEach(function (alert) {

        const closeBtn = alert.querySelector(".btn-close");

        if (closeBtn) {

            closeBtn.addEventListener("click", function () {
                alert.remove();
            });

        }


        // Automatically remove flash messages after 5 seconds.

        setTimeout(function () {

            if (!alert.isConnected) return;

            alert.classList.add("fade-out");

            setTimeout(function () {

                if (alert.isConnected) {
                    alert.remove();
                }

            }, 400);

        }, 5000);

    });

}


/* =========================================================
   SEARCH INPUT CLEAR
========================================================= */

function initializeSearchClear() {

    const searchForms = document.querySelectorAll(".search-form");


    searchForms.forEach(function (form) {

        const searchInput = form.querySelector(".search-input");
        const clearBtn = form.querySelector(".search-clear-btn");

        if (!searchInput || !clearBtn) return;


        function updateClearButton() {

            clearBtn.style.display = searchInput.value.trim()
                ? "inline-flex"
                : "none";

        }


        searchInput.addEventListener("input", updateClearButton);


        clearBtn.addEventListener("click", function () {

            searchInput.value = "";

            updateClearButton();

            searchInput.focus();

            // Submit form to reset search results.

            form.submit();

        });


        updateClearButton();

    });

}


/* =========================================================
   CURRENT YEAR
========================================================= */

function initializeCurrentYear() {

    const yearElements = document.querySelectorAll(".current-year");

    yearElements.forEach(function (element) {

        element.textContent = new Date().getFullYear();

    });

}


/* =========================================================
   BOOTSTRAP TOOLTIPS
========================================================= */

function initializeTooltips() {

    if (typeof bootstrap === "undefined") return;

    const tooltipElements = document.querySelectorAll(
        '[data-bs-toggle="tooltip"]'
    );


    tooltipElements.forEach(function (element) {

        new bootstrap.Tooltip(element);

    });

}


/* =========================================================
   CONFIRM ACTIONS
========================================================= */

function initializeConfirmActions() {

    const confirmButtons = document.querySelectorAll("[data-confirm]");


    confirmButtons.forEach(function (button) {

        button.addEventListener("click", function (event) {

            const message = button.dataset.confirm ||
                "Are you sure you want to continue?";


            if (!window.confirm(message)) {

                event.preventDefault();
                event.stopPropagation();

            }

        });

    });

}


/* =========================================================
   FORM SUBMIT LOADING
========================================================= */

function initializeFormLoading() {

    const forms = document.querySelectorAll("form[data-loading]");


    forms.forEach(function (form) {

        form.addEventListener("submit", function (event) {

            if (!form.checkValidity()) {
                return;
            }

            const submitBtn = form.querySelector(
                'button[type="submit"], input[type="submit"]'
            );

            if (!submitBtn) return;


            if (submitBtn.dataset.loadingActive === "true") {

                event.preventDefault();
                return;

            }


            submitBtn.dataset.loadingActive = "true";
            submitBtn.disabled = true;


            if (submitBtn.tagName === "BUTTON") {

                submitBtn.dataset.originalText = submitBtn.innerHTML;

                submitBtn.innerHTML = `
                    <span class="spinner-border spinner-border-sm me-2"
                          role="status"
                          aria-hidden="true"></span>
                    Please wait...
                `;

            }

        });

    });

}


/* =========================================================
   GLOBAL SIDEBAR HELPER
========================================================= */

window.DairyMitrAdmin = {

    openSidebar: function () {

        const appWrapper = document.getElementById("appWrapper");

        if (appWrapper) {
            appWrapper.classList.add("sidebar-open");
        }

    },


    closeSidebar: function () {

        const appWrapper = document.getElementById("appWrapper");
        const sidebar = document.getElementById("sidebar");
        const overlay = document.getElementById("sidebarOverlay");

        if (appWrapper) {
            appWrapper.classList.remove("sidebar-open");
        }

        if (sidebar) {
            sidebar.classList.remove("active");
        }

        if (overlay) {
            overlay.classList.remove("show");
        }

    },


    showNotification: function (message, type = "success") {

        const container = document.getElementById(
            "flashMessageContainer"
        );

        if (!container) return;


        const allowedTypes = [
            "success",
            "danger",
            "warning",
            "info"
        ];

        if (!allowedTypes.includes(type)) {
            type = "info";
        }


        const alert = document.createElement("div");

        alert.className = `alert alert-${type} alert-dismissible fade show`;

        alert.setAttribute("role", "alert");
        alert.textContent = message;


        const closeButton = document.createElement("button");

        closeButton.type = "button";
        closeButton.className = "btn-close";
        closeButton.setAttribute("aria-label", "Close");

        closeButton.addEventListener("click", function () {
            alert.remove();
        });


        alert.appendChild(closeButton);
        container.appendChild(alert);


        setTimeout(function () {

            if (alert.isConnected) {
                alert.remove();
            }

        }, 5000);

    }

};
