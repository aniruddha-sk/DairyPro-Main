
/* =========================================================
   DairyMitr SuperAdmin
   File: charts.js
   Dashboard Charts
========================================================= */

"use strict";


/* =========================================================
   DOM READY
========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    if (typeof Chart === "undefined") {
        console.error("Chart.js is not loaded.");
        return;
    }

    initializeMilkCollectionChart();
    initializeDairyVerificationChart();

});


/* =========================================================
   CHART DEFAULT CONFIGURATION
========================================================= */

Chart.defaults.font.family = "'Inter', sans-serif";
Chart.defaults.font.size = 12;
Chart.defaults.color = "#64748b";

Chart.defaults.plugins.legend.labels.usePointStyle = true;
Chart.defaults.plugins.legend.labels.boxWidth = 8;
Chart.defaults.plugins.legend.labels.padding = 18;


/* =========================================================
   MILK COLLECTION CHART
========================================================= */

function initializeMilkCollectionChart() {

    const canvas = document.getElementById("dashboardMilkChart");

    if (!canvas) return;


    const chartData = window.DairyMitrDashboardData || {};

    const milkData = Array.isArray(chartData.milk)
        ? chartData.milk
        : [];


    if (milkData.length === 0) {

        showMilkChartEmptyState(
            "No milk collection data available yet."
        );

        return;

    }


    const labels = milkData.map(function (item) {

        return item.date || item.label || "";

    });


    const values = milkData.map(function (item) {

        const value = Number(item.quantity ?? item.total ?? 0);

        return Number.isFinite(value) ? value : 0;

    });


    new Chart(canvas, {

        type: "line",

        data: {

            labels: labels,

            datasets: [{

                label: "Milk Collection",

                data: values,

                borderColor: "#2563eb",

                backgroundColor: "rgba(37, 99, 235, 0.10)",

                borderWidth: 2.5,

                fill: true,

                tension: 0.35,

                pointRadius: 3,

                pointHoverRadius: 6,

                pointBackgroundColor: "#2563eb",

                pointBorderColor: "#ffffff",

                pointBorderWidth: 2

            }]

        },


        options: {

            responsive: true,

            maintainAspectRatio: false,

            interaction: {
                intersect: false,
                mode: "index"
            },

            plugins: {

                legend: {
                    display: false
                },

                tooltip: {

                    backgroundColor: "#0f172a",

                    padding: 12,

                    cornerRadius: 8,

                    callbacks: {

                        label: function (context) {

                            return (
                                " Milk: " +
                                formatChartNumber(context.parsed.y) +
                                " L"
                            );

                        }

                    }

                }

            },


            scales: {

                x: {

                    grid: {
                        display: false
                    },

                    border: {
                        display: false
                    },

                    ticks: {
                        maxRotation: 0,
                        autoSkip: true,
                        maxTicksLimit: 8
                    }

                },


                y: {

                    beginAtZero: true,

                    border: {
                        display: false,
                        dash: [4, 4]
                    },

                    grid: {
                        color: "rgba(148, 163, 184, 0.15)"
                    },

                    ticks: {

                        precision: 0,

                        callback: function (value) {
                            return formatChartNumber(value) + " L";
                        }

                    }

                }

            }

        }

    });

}


/* =========================================================
   DAIRY VERIFICATION DOUGHNUT CHART
========================================================= */

function initializeDairyVerificationChart() {

    const canvas = document.getElementById("dairyVerificationChart");

    if (!canvas) return;


    const chartData = window.DairyMitrDashboardData || {};

    const verification = chartData.verification || {};


    const verified = Math.max(
        0,
        Number(verification.verified) || 0
    );

    const unverified = Math.max(
        0,
        Number(verification.unverified) || 0
    );


    if (verified + unverified === 0) {

        showVerificationEmptyState(
            "No dairy verification data available."
        );

        return;

    }


    new Chart(canvas, {

        type: "doughnut",

        data: {

            labels: [
                "Verified",
                "Unverified"
            ],

            datasets: [{

                data: [
                    verified,
                    unverified
                ],

                backgroundColor: [
                    "#16a34a",
                    "#f59e0b"
                ],

                borderColor: [
                    "#ffffff",
                    "#ffffff"
                ],

                borderWidth: 4,

                hoverOffset: 7,

                borderRadius: 5

            }]

        },


        options: {

            responsive: true,

            maintainAspectRatio: false,

            cutout: "72%",


            plugins: {

                legend: {
                    display: false
                },

                tooltip: {

                    backgroundColor: "#0f172a",

                    padding: 12,

                    cornerRadius: 8,

                    callbacks: {

                        label: function (context) {

                            const total = verified + unverified;

                            const percentage = total > 0
                                ? (
                                    context.parsed / total * 100
                                ).toFixed(1)
                                : 0;


                            return (
                                " " +
                                context.label +
                                ": " +
                                formatChartNumber(context.parsed) +
                                " (" +
                                percentage +
                                "%)"
                            );

                        }

                    }

                }

            }

        }

    });

}


/* =========================================================
   MILK CHART EMPTY STATE
========================================================= */

function showMilkChartEmptyState(message) {

    const container = document.getElementById("dashboardMilkEmpty");

    const canvas = document.getElementById("dashboardMilkChart");

    if (canvas) {
        canvas.style.display = "none";
    }

    if (!container) return;


    container.style.display = "flex";

    container.innerHTML = `
        <div class="empty-icon">
            <i class="bi bi-bar-chart-line"></i>
        </div>
        <p>${escapeChartHTML(message)}</p>
    `;

}


/* =========================================================
   VERIFICATION CHART EMPTY STATE
========================================================= */

function showVerificationEmptyState(message) {

    const canvas = document.getElementById("dairyVerificationChart");

    if (!canvas) return;


    const parent = canvas.parentElement;

    canvas.style.display = "none";


    const emptyState = document.createElement("div");

    emptyState.className = "chart-empty-state";

    emptyState.innerHTML = `
        <div class="empty-icon">
            <i class="bi bi-pie-chart"></i>
        </div>
        <p>${escapeChartHTML(message)}</p>
    `;


    parent.appendChild(emptyState);

}


/* =========================================================
   NUMBER FORMATTING
========================================================= */

function formatChartNumber(value) {

    const number = Number(value);

    if (!Number.isFinite(number)) {
        return "0";
    }

    return new Intl.NumberFormat("en-IN", {

        maximumFractionDigits: 2

    }).format(number);

}


/* =========================================================
   HTML ESCAPING
========================================================= */

function escapeChartHTML(value) {

    return String(value).replace(/[&<>"']/g, function (character) {

        const entities = {

            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"

        };

        return entities[character];

    });

}
