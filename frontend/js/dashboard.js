/**
 * ============================================================
 * dashboard.js — Professional EV Fleet AI Command Center
 * ============================================================
 */

const API_BASE = "http://127.0.0.1:5000"; 
let energyChart = null;
let statusChart = null;

document.addEventListener("DOMContentLoaded", () => {
    // Ensure smooth entry for the dashboard UI
    const dashboardContent = document.getElementById("dashboardContent");
    if (dashboardContent) dashboardContent.style.opacity = "1";

    // Initial Data Fetch
    fetchDashboardMetrics();
    
    // Auto-refresh every 15 seconds for a high-performance "live" feel
    setInterval(fetchDashboardMetrics, 15000);
});

/**
 * Main Controller: Fetches data from Flask API and dispatches to UI
 */
async function fetchDashboardMetrics() {
    try {
        const res = await fetch(`${API_BASE}/api/dashboard/kpis`);
        const json = await res.json();

        if (!res.ok || !json.success) {
            console.warn("⚠️ API Connectivity Issue:", json.error || "Remote server unreachable");
            showDashboardFallback();
            return;
        }

        const metrics = json.data || {};

        // 1. Update Core Numeric KPIs
        safeUpdateText("avgSoc", `${metrics.avg_soc || 0}%`);
        safeUpdateText("avgSoh", `${metrics.avg_soh || 0}%`);
        safeUpdateText("energy", `${metrics.total_energy || 0} kWh`);
        safeUpdateText("fleetReadiness", `${metrics.fleet_readiness || 0}%`);

        // 2. Update Sustainability Metric (Green Metric)
        // Ensure you have an element with id="co2Savings" in your HTML
        safeUpdateText("co2Savings", `${metrics.co2_savings || 0} kg`);

        // 3. Update Visual Components
        updateAlerts(metrics.alerts || []);
        updateEnergyChart(metrics.energy_history || []);
        updateStatusChart(metrics.status_counts || {});

    } catch (err) {
        console.error("❌ Fatal Dashboard Error:", err);
        showDashboardFallback();
    }
}

/**
 * Severity-aware Alert Processor
 */
function updateAlerts(alerts) {
    const alertsList = document.getElementById("alerts");
    const alertsState = document.getElementById("alertsState");
    if (!alertsList || !alertsState) return;

    alertsList.innerHTML = "";
    
    if (alerts && alerts.length > 0) {
        alertsState.style.display = "none";
        alerts.forEach(a => {
            const li = document.createElement("li");
            
            // Severity logic mapped to professional color palette
            const isCritical = a.level === "critical" || a.issue.toLowerCase().includes("degradation");
            const color = isCritical ? "#ef4444" : "#f59e0b";
            const bg = isCritical ? "rgba(239, 68, 68, 0.08)" : "rgba(245, 158, 11, 0.05)";

            li.className = "alert-item";
            li.style.cssText = `
                padding: 14px;
                margin-bottom: 12px;
                border-radius: 12px;
                list-style: none;
                background: ${bg};
                border-left: 4px solid ${color};
                animation: fadeIn 0.4s ease-out;
            `;
            
            li.innerHTML = `
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <strong style="color:${color}; font-size: 0.9rem;">Bus ${a.bus_id}</strong>
                    <span style="height: 6px; width: 6px; border-radius: 50%; background: ${color}; box-shadow: 0 0 8px ${color};"></span>
                </div>
                <div style="font-size: 0.82rem; color: #cbd5e1; margin-top: 6px; line-height: 1.4;">${a.issue}</div>
            `;
            alertsList.appendChild(li);
        });
    } else {
        alertsState.style.display = "block";
        alertsState.innerHTML = `<span style="color: #10b981; font-weight: 600;">✔ Fleet Status Optimal</span>`;
    }
}

/**
 * Time-Series Data Visualizer (Energy Trend)
 */
function updateEnergyChart(history) {
    const canvas = document.getElementById("energyChart");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    const labels = history.map(e => e.timestamp);
    const values = history.map(e => e.value);

    if (energyChart) {
        energyChart.data.labels = labels;
        energyChart.data.datasets[0].data = values;
        energyChart.update('none'); // Update without animation for performance
    } else {
        energyChart = new Chart(ctx, {
            type: "line",
            data: {
                labels,
                datasets: [{
                    label: "Voltage Usage",
                    data: values,
                    borderColor: "#3b82f6",
                    backgroundColor: "rgba(59, 130, 246, 0.05)",
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0, // Cleaner look for high-density data
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { color: "#94a3b8", maxRotation: 0 } },
                    y: { 
                        beginAtZero: false, 
                        grid: { color: "rgba(255,255,255,0.03)" }, 
                        ticks: { color: "#94a3b8" } 
                    }
                }
            }
        });
    }
}

/**
 * Fleet Distribution Doughnut (Status Groups)
 */
function updateStatusChart(counts) {
    const canvas = document.getElementById("statusChart");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    const dataValues = [
        counts.active || 0, 
        counts.idle || 0, 
        counts.critical || 0
    ];

    if (statusChart) {
        statusChart.data.datasets[0].data = dataValues;
        statusChart.update();
    } else {
        statusChart = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: ["Active", "Idle", "Critical"],
                datasets: [{
                    data: dataValues,
                    backgroundColor: ["#10b981", "#334155", "#ef4444"],
                    borderWidth: 0,
                    hoverOffset: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "80%",
                plugins: {
                    legend: { 
                        position: "right", 
                        labels: { color: "#94a3b8", usePointStyle: true, font: { size: 11 } } 
                    }
                }
            }
        });
    }
}

/**
 * Fallback mechanism for lost API connectivity
 */
function showDashboardFallback() {
    ["avgSoc", "avgSoh", "energy", "fleetReadiness", "co2Savings"].forEach(id => {
        safeUpdateText(id, "SYNCING...");
    });
}

/**
 * Safe DOM Update Utility
 */
function safeUpdateText(id, text) {
    const el = document.getElementById(id);
    if (el) el.innerText = text;
}