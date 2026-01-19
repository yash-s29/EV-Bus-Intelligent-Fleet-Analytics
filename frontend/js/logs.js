// ==================================================
// LOGS.JS — Fleet Logs Integrated with Route Monitor
// ==================================================

const API_BASE = "http://127.0.0.1:5000";

// -----------------------------
// DOM Elements
// -----------------------------
const busIdEl = document.getElementById("busId");
const limitEl = document.getElementById("limit");
const tableBody = document.querySelector("#logTable tbody");
const tableState = document.getElementById("logState");
const filterBtn = document.getElementById("filterBtn");
const exportBtn = document.getElementById("exportBtn");
const closeBtn = document.getElementById("closeLogs");

const routeWindow = window.opener || null;

// -----------------------------
// Active buses (localStorage)
// -----------------------------
let activeBuses = JSON.parse(localStorage.getItem("activeBuses") || "[]");

// -----------------------------
// UI Helpers
// -----------------------------
function showState(message, type = "info") {
  if (!tableState) return;
  tableState.textContent = message;
  tableState.className = `state-box ${type === "error" ? "error" : "loading"}`;
  tableState.style.display = "block";
  if (tableBody) tableBody.innerHTML = "";
}

function hideState() {
  if (!tableState) return;
  tableState.style.display = "none";
}

// -----------------------------
// Status helpers
// -----------------------------
function getStatusAndIssues(sohPercent) {
  if (sohPercent >= 90) return { status: "Good", issues: 0 };
  if (sohPercent >= 60) return { status: "Proper", issues: 0 };
  if (sohPercent >= 50) return { status: "Attention", issues: 1 };
  return { status: "Critical", issues: 1 };
}

function statusClass(sohPercent) {
  if (sohPercent >= 90) return "status-green";
  if (sohPercent >= 50) return "status-yellow";
  return "status-red";
}

function animateRow(row) {
  row.style.opacity = 0;
  tableBody.appendChild(row);
  requestAnimationFrame(() => {
    row.style.transition = "opacity 0.3s ease";
    row.style.opacity = 1;
  });
}

// -----------------------------
// Render table
// -----------------------------
function renderLogsTable() {
  tableBody.innerHTML = "";
  if (!activeBuses.length) {
    showState("No active buses. Enter a Bus ID to start monitoring.");
    return;
  }

  hideState();

  activeBuses.forEach(bus => {
    const tr = document.createElement("tr");
    tr.className = statusClass(bus.soh);

    tr.innerHTML = `
      <td class="bus-id-cell">${bus.bus_id}</td>
      <td>${bus.soh ?? "--"}%</td>
      <td>${bus.maintenance_due ?? "-"}</td>
      <td class="issues-cell">${bus.issues}</td>
      <td>${bus.status}</td>
      <td><button class="remove-bus-btn" title="Remove this bus">&times;</button></td>
    `;

    // Clickable Issues alert
    const issuesCell = tr.querySelector(".issues-cell");
    if (bus.issues > 0) {
      issuesCell.style.cursor = "pointer";
      issuesCell.addEventListener("click", () => {
        alert(`Bus ${bus.bus_id} battery health is ${bus.soh}%. Immediate attention required.`);
      });
    }

    // Bus selection
    const busCell = tr.querySelector(".bus-id-cell");
    busCell.style.cursor = "pointer";
    busCell.addEventListener("click", () => {
      localStorage.setItem("selectedBusId", bus.bus_id);
      if (routeWindow && routeWindow.fetchRouteStatus) {
        routeWindow.fetchRouteStatus(activeBuses.map(b => b.bus_id));
        routeWindow.focus();
      }
      Array.from(tableBody.rows).forEach(r => r.classList.remove("selected-bus"));
      tr.classList.add("selected-bus");
    });

    // Remove bus
    tr.querySelector(".remove-bus-btn").addEventListener("click", () => {
      activeBuses = activeBuses.filter(b => b.bus_id !== bus.bus_id);
      localStorage.setItem("activeBuses", JSON.stringify(activeBuses));
      renderLogsTable();
      if (routeWindow && routeWindow.fetchRouteStatus) routeWindow.fetchRouteStatus(activeBuses.map(b => b.bus_id));
    });

    animateRow(tr);
  });
}

// -----------------------------
// Load logs for a bus
// -----------------------------
async function loadLogs() {
  const busId = busIdEl.value.trim();
  const limit = Math.min(Math.max(parseInt(limitEl.value, 10) || 100, 1), 1000);

  if (!busId) return showState("Please enter a Bus ID", "error");

  showState("Fetching logs…");

  try {
    const query = new URLSearchParams({ bus_id: busId, limit }).toString();
    const res = await fetch(`${API_BASE}/api/logs?${query}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (!data.success || !data.data.records.length) return showState("No records found for this Bus ID");

    data.data.records.forEach(r => {
      let sohPercent = parseFloat(r.soh ?? r.predicted_soh ?? 0);
      if (sohPercent <= 1) sohPercent *= 100;
      sohPercent = parseFloat(sohPercent.toFixed(1));

      const { status, issues } = getStatusAndIssues(sohPercent);
      const maintenanceDate = r.maintenance_due ? new Date(r.maintenance_due).toLocaleString() : "-";

      const busObj = {
        bus_id: r.bus_id,
        soh: sohPercent,
        status,
        issues,
        maintenance_due: maintenanceDate,
        predicted_soh: sohPercent
      };

      const index = activeBuses.findIndex(b => b.bus_id === r.bus_id);
      if (index === -1) activeBuses.push(busObj);
      else activeBuses[index] = busObj;
    });

    localStorage.setItem("activeBuses", JSON.stringify(activeBuses));
    renderLogsTable();
    if (routeWindow && routeWindow.fetchRouteStatus) routeWindow.fetchRouteStatus(activeBuses.map(b => b.bus_id));

  } catch (err) {
    console.error("Error fetching logs:", err);
    showState("Error loading logs", "error");
  }
}

// -----------------------------
// Export CSV — Full telemetry
// -----------------------------
async function exportCSV() {
  const busId = busIdEl.value.trim();
  if (!busId) return alert("Please enter a Bus ID to export telemetry");

  const limit = Math.min(Math.max(parseInt(limitEl.value, 10) || 10000, 1), 10000);

  try {
    const query = new URLSearchParams({ bus_id: busId, limit, export: "true" }).toString();
    const res = await fetch(`${API_BASE}/api/logs?${query}`);
    if (!res.ok) {
      const errText = await res.text();
      throw new Error(`HTTP ${res.status} — ${errText}`);
    }

    const csvText = await res.text();
    if (!csvText || csvText.trim() === "") return alert("No telemetry records to export");

    const blob = new Blob([csvText], { type: "text/csv;charset=utf-8;" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `fleet_telemetry_${busId}_${new Date().toISOString().slice(0,19).replace(/:/g,"")}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);

  } catch (err) {
    console.error("Error exporting CSV:", err);
    alert("Failed to export CSV. Check console for details.");
  }
}

// -----------------------------
// Close all buses
// -----------------------------
if (closeBtn) closeBtn.addEventListener("click", () => {
  activeBuses = [];
  localStorage.removeItem("activeBuses");
  renderLogsTable();
  if (routeWindow && routeWindow.fetchRouteStatus) routeWindow.fetchRouteStatus([]);
});

// -----------------------------
// Auto-load Fleet Logs
// -----------------------------
document.addEventListener("DOMContentLoaded", () => {
  if (activeBuses.length) renderLogsTable();
});

// -----------------------------
// Event listeners
// -----------------------------
filterBtn?.addEventListener("click", loadLogs);
exportBtn?.addEventListener("click", exportCSV);
