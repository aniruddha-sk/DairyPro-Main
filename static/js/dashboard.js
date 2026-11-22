
/* =========================================================
   DairyMitr SuperAdmin
   File: dashboard.js
   Dashboard Interactions
========================================================= */

"use strict";


/* =========================================================
   DOM READY
========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    initializeDashboardDate();
    initializeDashboardRefresh();
    initializeDashboardChartData();
    initializeDashboardQuickAccess();

});


/* =========================================================
   DASHBOARD DATE
========================================================= */

function initializeDashboardDate() {

    const dateElement = document.getElementById("currentDashboardDate");

    if (!dateElement) return;


    const today = new Date();

    const options = {
        weekday: "long",
        day: "numeric",
        month: "long",
        year: "numeric"
    };


    dateElement.textContent = today.toLocaleDateString(
        "en-IN",
        options
    );


    const dashboardDate = document.getElementById("dashboardDate");

    if (dashboardDate) {

        dashboardDate.textContent = today.toLocaleDateString(
            "en-IN",
            options
        );

    }

}


/* =========================================================
   DASHBOARD REFRESH BUTTON
========================================================= */

function initializeDashboardRefresh() {

    const refreshBtn = document.getElementById("refreshDashboardBtn");

    if (!refreshBtn) return;


    refreshBtn.addEventListener("click", function () {

        if (refreshBtn.disabled) return;


        const originalContent = refreshBtn.innerHTML;

        refreshBtn.disabled = true;

        refreshBtn.classList.add("is-loading");

        refreshBtn.innerHTML = `
            <span class="spinner-border spinner-border-sm me-2"
                  role="status"
                  aria-hidden="true"></span>
            Refreshing...
        `;


        // Reload current dashboard data from the server.

        window.location.reload();

    });

}


/* =========================================================
   DASHBOARD CHART DATA
========================================================= */

function initializeDashboardChartData() {

    const dataElement = document.getElementById("dashboardChartData");

    if (!dataElement) return;


    try {

        const chartData = JSON.parse(dataElement.textContent || "{}");


        // Make data available to dashboard chart script.

        window.DairyMitrDashboardData = {

            milk: Array.isArray(chartData.milk)
                ? chartData.milk
                : [],

            verification: chartData.verification || {
                verified: 0,
                unverified: 0
            }

        };


    } catch (error) {

        console.error("Dashboard chart data parsing failed:", error);


        window.DairyMitrDashboardData = {

            milk: [],

            verification: {
                verified: 0,
                unverified: 0
            }

        };

    }

}


/* =========================================================
   DASHBOARD QUICK ACCESS
========================================================= */

function initializeDashboardQuickAccess() {

    const cards = document.querySelectorAll(".quick-access-card");


    cards.forEach(function (card) {

        card.addEventListener("keydown", function (event) {

            if (
                event.key === "Enter" ||
                event.key === " "
            ) {

                const link = card.querySelector("a");

                if (link) {

                    event.preventDefault();
                    link.click();

                }

            }

        });

    });

}


/* =========================================================
   DASHBOARD NUMBER FORMATTING
========================================================= */

window.formatDashboardNumber = function (value) {

    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "0";
    }

    return new Intl.NumberFormat("en-IN", {
        maximumFractionDigits: 2
    }).format(number);

};


/* =========================================================
   DASHBOARD EMPTY STATE
========================================================= */

window.showDashboardEmptyState = function (
    containerId,
    message = "No data available"
) {

    const container = document.getElementById(containerId);

    if (!container) return;


    container.innerHTML = "";


    const emptyState = document.createElement("div");

    emptyState.className = "chart-empty-state";


    const icon = document.createElement("div");

    icon.className = "empty-icon";
    icon.innerHTML = '<i class="bi bi-bar-chart"></i>';


    const text = document.createElement("p");

    text.textContent = message;


    emptyState.appendChild(icon);
    emptyState.appendChild(text);

    container.appendChild(emptyState);

};


/* =========================================================
   DASHBOARD ERROR HANDLING
========================================================= */

window.handleDashboardError = function (error) {

    console.error("Dashboard error:", error);


    if (
        window.DairyMitrAdmin &&
        typeof window.DairyMitrAdmin.showNotification === "function"
    ) {

        window.DairyMitrAdmin.showNotification(
            "Unable to load dashboard information.",
            "danger"
        );

    }

};
