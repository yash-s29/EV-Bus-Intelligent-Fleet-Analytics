/**
 * ============================================================
 * PREDICTION.JS - Professional EV Fleet Logic
 * ============================================================
 */

const API_BASE = "http://127.0.0.1:5000";
let predictionChart = null;

// UI Element Selectors
const routeInput = document.getElementById("routeId");
const passengersInput = document.getElementById("passengers");
const weatherSelect = document.getElementById("weather");
const endSocEl = document.getElementById("endSoc");
const riskEl = document.getElementById("risk");
const speedEl = document.getElementById("speed");
const messageEl = document.getElementById("predictionMessage");
const predictBtn = document.getElementById("predictBtn");

/**
 * Main Predictor Function
 */
async function predictTrip() {
    // 1. Prepare Data Payload
    const payload = {
        route_id: routeInput.value.trim(),
        passenger_load: parseFloat(passengersInput.value),
        weather: weatherSelect.value,
        bus_id: "EV-COMMANDER", // Identifier for logging
        current_soc: 95.0       // Starting SOC assumption
    };

    // 2. Client-side Validation
    if (!payload.route_id || isNaN(payload.passenger_load) || !payload.weather) {
        showFeedback("Please fill all fields (Route, Load, and Weather).", "error");
        return;
    }

    setLoadingState(true);

    try {
        // 3. API Request
        const res = await fetch(`${API_BASE}/api/prediction/predict`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });

        const json = await res.json();

        if (!res.ok || !json.success) {
            throw new Error(json.error || "Prediction engine error");
        }

        const result = json.data;

        // 4. Update UI Components
        updateKPIs(result);
        renderPredictionChart(result.energy_curve);
        showFeedback("AI Prediction Successful.", "success");

    } catch (err) {
        console.error("❌ Prediction Error:", err);
        showFeedback(err.message, "error");
        resetKPIs();
    } finally {
        setLoadingState(false);
    }
}

/**
 * Updates the KPI cards with color-coded risk assessment
 */
function updateKPIs(data) {
    endSocEl.textContent = `${data.predicted_end_soc}%`;
    speedEl.textContent = `${data.recommended_speed} km/h`;
    
    // Risk UI Logic
    riskEl.textContent = data.risk_level;
    
    // Style Risk based on severity
    if (data.risk_level === "CRITICAL") {
        riskEl.style.color = "#ef4444"; // Red
    } else if (data.risk_level === "WARNING") {
        riskEl.style.color = "#f59e0b"; // Amber
    } else {
        riskEl.style.color = "#10b981"; // Green
    }
}

/**
 * Visualizes the predicted battery drain (SoC) over the route distance
 */
function renderPredictionChart(curveData) {
    const canvas = document.getElementById("tripChart");
    if (!canvas) return;
    
    const ctx = canvas.getContext("2d");
    
    const labels = curveData.map(point => `${point.distance}km`);
    const values = curveData.map(point => point.soc);

    if (predictionChart) {
        predictionChart.destroy(); // Prevent overlapping charts
    }

    predictionChart = new Chart(ctx, {
        type: "line",
        data: {
            labels: labels,
            datasets: [{
                label: "Battery SoC %",
                data: values,
                borderColor: "#3b82f6",
                backgroundColor: "rgba(59, 130, 246, 0.1)",
                fill: true,
                tension: 0.4,
                borderWidth: 3,
                pointRadius: 4,
                pointBackgroundColor: "#3b82f6"
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { 
                legend: { display: false },
                tooltip: { mode: 'index', intersect: false }
            },
            scales: {
                y: { 
                    min: 0, 
                    max: 100, 
                    title: { display: true, text: 'State of Charge (%)', color: '#94a3b8' },
                    ticks: { color: "#94a3b8" }, 
                    grid: { color: "rgba(255,255,255,0.05)" } 
                },
                x: { 
                    title: { display: true, text: 'Distance (km)', color: '#94a3b8' },
                    ticks: { color: "#94a3b8" }, 
                    grid: { display: false } 
                }
            }
        }
    });
}

/**
 * UI State Management Helpers
 */
function setLoadingState(isLoading) {
    if (isLoading) {
        predictBtn.disabled = true;
        predictBtn.textContent = "Processing AI...";
        messageEl.classList.remove("hidden");
        showFeedback("Calculating battery drain curve...", "info");
    } else {
        predictBtn.disabled = false;
        predictBtn.textContent = "Predict Trip";
    }
}

function showFeedback(text, type) {
    messageEl.textContent = text;
    messageEl.className = "state-box"; // Reset classes
    if (type === "error") messageEl.classList.add("state-error");
    else if (type === "success") messageEl.classList.add("state-success");
    else messageEl.classList.add("state-loading");
    
    messageEl.classList.remove("hidden");
}

function resetKPIs() {
    endSocEl.textContent = "--%";
    riskEl.textContent = "--";
    riskEl.style.color = "inherit";
    speedEl.textContent = "-- km/h";
}

// Event Listeners
document.addEventListener("DOMContentLoaded", () => {
    predictBtn.addEventListener("click", predictTrip);
});