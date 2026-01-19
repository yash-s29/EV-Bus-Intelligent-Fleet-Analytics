// =========================================================
// MAINTENANCE.JS — FINAL & RESILIENT
// =========================================================

const API_URL = "/api/maintenance";

// -------------------------
// DOM ELEMENTS (initialized later)
// -------------------------
let upcomingServicesEl;
let activeAlertsEl;
let avgBatteryHealthEl;
let table;
let tableBody;
let tableState;
let maintenanceCountEl;

// =========================================================
// UI STATE HELPERS
// =========================================================
function showState(message, isError = false) {
  if (!tableState) return;
  tableState.style.display = "block";
  tableState.textContent = message;
  tableState.className = `state-box ${isError ? "error" : "loading"}`;
}

function hideState() {
  if (!tableState) return;
  tableState.style.display = "none";
  tableState.className = "state-box";
}

// =========================================================
// STATUS CLASS (RENDER ONLY)
// =========================================================
function statusClass(status = "") {
  switch (String(status).toLowerCase()) {
    case "critical":
      return "status-red";
    case "warning":
      return "status-yellow";
    default:
      return "status-green";
  }
}

// =========================================================
// TABLE ROW CREATION
// =========================================================
function createTableRow(record) {
  const tr = document.createElement("tr");

  tr.innerHTML = `
    <td>${record.bus_id ?? "—"}</td>
    <td>${record.last_service ?? "—"}</td>
    <td>${record.next_service ?? "—"}</td>
    <td class="${statusClass(record.status)}">${record.status ?? "Normal"}</td>
  `;

  tr.addEventListener("click", () => {
    console.info("Maintenance Record:", record);
  });

  return tr;
}

// =========================================================
// MAIN FETCH LOGIC
// =========================================================
async function loadMaintenance() {
  showState("Fetching maintenance analytics…");

  try {
    const res = await fetch(API_URL, { cache: "no-store" });
    const json = await res.json();

    if (!res.ok || !json.success) {
      throw new Error(json?.error || "Maintenance API error");
    }

    const data = json.data || {};

    // -------------------------
    // KPIs
    // -------------------------
    upcomingServicesEl.textContent =
      Number.isFinite(data.upcoming_services) ? data.upcoming_services : "—";

    activeAlertsEl.textContent =
      Number.isFinite(data.active_alerts) ? data.active_alerts : "—";

    avgBatteryHealthEl.textContent =
      Number.isFinite(data.avg_battery_health)
        ? `${data.avg_battery_health}%`
        : "—%";

    // -------------------------
    // Table
    // -------------------------
    tableBody.innerHTML = "";
    const records = Array.isArray(data.records) ? data.records : [];

    if (!records.length) {
      maintenanceCountEl.textContent = "0 records";
      showState("No maintenance records available");
      return;
    }

    records.forEach(record => {
      tableBody.appendChild(createTableRow(record));
    });

    maintenanceCountEl.textContent = `${records.length} records`;
    hideState();
  } catch (err) {
    console.error("❌ Maintenance fetch failed:", err);
    maintenanceCountEl.textContent = "—";
    showState("Failed to load maintenance data", true);
  }
}

// =========================================================
// INIT
// =========================================================
document.addEventListener("DOMContentLoaded", () => {
  // DOM ELEMENTS
  upcomingServicesEl = document.getElementById("upcomingServices");
  activeAlertsEl = document.getElementById("activeAlerts");
  avgBatteryHealthEl = document.getElementById("avgBatteryHealth");

  table = document.getElementById("maintenanceTable");
  tableBody = table?.querySelector("tbody");

  tableState = document.getElementById("maintenanceState");
  maintenanceCountEl = document.getElementById("maintenanceCount");

  // Verify essential elements exist
  if (!table || !tableBody || !tableState || !upcomingServicesEl || !activeAlertsEl || !avgBatteryHealthEl) {
    console.error("❌ Maintenance DOM elements missing. Script cannot run.");
    return;
  }

  // Initial load + periodic refresh
  loadMaintenance();
  setInterval(loadMaintenance, 60_000); // every 60s
});
