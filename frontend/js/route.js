  /**
   * ==================================================
   * ROUTE.JS — Fleet Navigation Intelligence (PRO+)
   * Upgrades:
   * - Animated buses along roads
   * - Traffic-aware optimized routes
   * - Charging stations dynamically
   * - Focus + auto-pan on selected/critical buses
   * - Popups for buses & charging stations
   * ==================================================
   */

  const routeTableBody = document.querySelector("#routeTable tbody");
  const routeStateEl = document.getElementById("routeState");
  const syncTimerEl = document.getElementById("sync-timer");
  const syncProgressEl = document.getElementById("sync-progress-bar");
  const mapSearchEl = document.getElementById("mapSearch");

  let selectedBusId = localStorage.getItem("selectedBusId") || "";
  let isFetching = false;
  let countdown = 10;
  const REFRESH_INTERVAL = 10;

  // =======================
  // MAP + LAYERS
  // =======================
  let map;
  const movementLayer = L.layerGroup();
  const emergencyRouteLayer = L.layerGroup();
  const arrowLayer = L.layerGroup();
  const stationLayer = L.layerGroup();
  const markerLayer = L.layerGroup();

  const busMarkers = {};
  const animationState = {};
  const stationMarkers = {};

  // =======================
  // INIT MAP
  // =======================
  function initMap() {
    if (map) return;

    map = L.map("map", { zoomControl: false, preferCanvas: true })
            .setView([18.5204, 73.8567], 13);

    // Light, real-world tiles
    L.tileLayer(
      "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
      { attribution: '&copy; <a href="https://www.openstreetmap.org/">OSM</a>', maxZoom: 20 }
    ).addTo(map);

    movementLayer.addTo(map);
    emergencyRouteLayer.addTo(map);
    arrowLayer.addTo(map);
    stationLayer.addTo(map);
    markerLayer.addTo(map);

    L.control.zoom({ position: "bottomright" }).addTo(map);
  }

  // =======================
  // STATUS & TRAFFIC COLORS
  // =======================
  function statusColor(status) {
    switch ((status || "").toUpperCase()) {
      case "GOOD": return "#16a34a";
      case "MEDIOCRE": return "#facc15";
      case "CRITICAL": return "#dc2626";
      default: return "#64748b";
    }
  }

  function trafficColor() {
    const r = Math.random();
    if (r < 0.6) return "#16a34a";
    if (r < 0.85) return "#facc15";
    return "#dc2626";
  }

  // =======================
  // UPDATE MAP
  // =======================
  function updateMap(buses) {
    movementLayer.clearLayers();
    emergencyRouteLayer.clearLayers();
    arrowLayer.clearLayers();
    stationLayer.clearLayers();

    const activeIds = new Set();

    buses.forEach(bus => {
      if (bus.lat == null || bus.lng == null) return;
      activeIds.add(bus.bus_id);

      drawBus(bus);
      drawMovementTrail(bus);

      if (bus.status === "CRITICAL" && bus.charging_station) {
        drawOptimizedEmergencyRoute(bus);
      } else if (bus.charging_station) {
        drawStation(bus.charging_station);
      }
    });

    // Remove inactive buses
    Object.keys(busMarkers).forEach(id => {
      if (!activeIds.has(id)) {
        markerLayer.removeLayer(busMarkers[id]);
        delete busMarkers[id];
        delete animationState[id];
      }
    });
  }

  // =======================
  // BUS MARKER + FOCUS
  // =======================
  function drawBus(bus) {
    const color = statusColor(bus.status);
    const isFocused = bus.bus_id === selectedBusId || bus.status === "CRITICAL";

    const icon = L.divIcon({
      className: "bus-icon",
      html: `<div class="bus-dot" style="background:${color};opacity:${isFocused ? 1 : 0.35};"></div>
            <div class="bus-label" style="opacity:${isFocused ? 1 : 0.4};">${bus.bus_id}</div>`,
      iconSize: [28, 28],
      iconAnchor: [14, 14]
    });

    if (!busMarkers[bus.bus_id]) {
      busMarkers[bus.bus_id] = L.marker([bus.lat, bus.lng], { icon })
        .addTo(markerLayer)
        .bindPopup(busPopup(bus));
      animationState[bus.bus_id] = { lat: bus.lat, lng: bus.lng };
    } else {
      animateBus(bus.bus_id, [bus.lat, bus.lng]);
      busMarkers[bus.bus_id].setIcon(icon).setPopupContent(busPopup(bus));
    }

    if (isFocused) map.panTo([bus.lat, bus.lng], { animate: true });
  }

  // =======================
  // MOVEMENT TRAIL
  // =======================
  function drawMovementTrail(bus) {
    if (!bus.prev_lat || !bus.prev_lng) return;

    L.polyline([[bus.prev_lat, bus.prev_lng], [bus.lat, bus.lng]], {
      color: "#94a3b8",
      weight: 2,
      opacity: 0.25
    }).addTo(movementLayer);
  }

  // =======================
  // EMERGENCY ROUTE
  // =======================
  function drawOptimizedEmergencyRoute(bus) {
    const s = bus.charging_station;
    if (!s) return;

    const route = [[bus.lat, bus.lng], [s.lat, s.lng]];
    const traffic = trafficColor();
    const chargerColor = s.available ? "#22c55e" : "#facc15";

    // Charger marker with popup
    const marker = L.circleMarker([s.lat, s.lng], { radius: 8, color: chargerColor, fillOpacity: 1 })
      .bindPopup(`⚡ <b>${s.name}</b><br>Status: ${s.available ? "Available" : "Busy"}`)
      .addTo(stationLayer);
    stationMarkers[s.name] = marker;

    // Base route
    L.polyline(route, { color: "#e5e7eb", weight: 10, opacity: 0.9 }).addTo(emergencyRouteLayer);

    // Traffic overlay
    L.polyline(route, { color: traffic, weight: 5, opacity: 1 }).addTo(emergencyRouteLayer);

    // Direction arrow
    drawArrow(route);
  }

  // =======================
  // DIRECTION ARROW
  // =======================
  function drawArrow(points) {
    const mid = points[Math.floor(points.length / 2)];
    L.marker(mid, { icon: L.divIcon({ className: "route-arrow", html: "➤", iconSize: [20, 20] }) })
    .addTo(arrowLayer);
  }

  // =======================
  // CHARGING STATION (non-critical)
  function drawStation(station) {
    const color = station.available ? "#22c55e" : "#facc15";
    if (stationMarkers[station.name]) return; // avoid duplicates

    const marker = L.circleMarker([station.lat, station.lng], { radius: 6, color, fillOpacity: 1 })
      .bindPopup(`⚡ <b>${station.name}</b><br>Status: ${station.available ? "Available" : "Busy"}`)
      .addTo(stationLayer);

    stationMarkers[station.name] = marker;
  }

  // =======================
  // BUS ANIMATION
  // =======================
  function animateBus(id, target) {
    const marker = busMarkers[id];
    const state = animationState[id];
    if (!marker || !state) return;

    const steps = 40;
    let i = 0;
    const dLat = (target[0] - state.lat) / steps;
    const dLng = (target[1] - state.lng) / steps;

    function step() {
      if (i >= steps) return;
      state.lat += dLat;
      state.lng += dLng;
      marker.setLatLng([state.lat, state.lng]);
      i++;
      requestAnimationFrame(step);
    }
    step();
  }

  // =======================
  // BUS POPUP
  // =======================
  function busPopup(bus) {
    return `<div style="font-size:0.85rem;line-height:1.5">
        <b>${bus.bus_id}</b><br/>
        Route: ${bus.route_id}<br/>
        SoC: ${bus.soc.toFixed(1)}%<br/>
        Status: <span style="color:${statusColor(bus.status)};font-weight:800">${bus.status}</span>
      </div>`;
  }

  // =======================
  // FETCH ROUTE STATUS
  // =======================
  async function fetchRouteStatus() {
    if (isFetching) return;
    isFetching = true;

    try {
      const res = await fetch("http://127.0.0.1:5000/api/route");
      const data = await res.json();
      if (!data.success) throw Error();

      const q = mapSearchEl?.value.toLowerCase() || "";
      const filtered = data.buses.filter(b =>
        b.bus_id.toLowerCase().includes(q) ||
        (b.charging_station?.name || "").toLowerCase().includes(q)
      );

      renderTable(filtered);
      updateMap(filtered);
      routeStateEl.style.display = "none";

    } catch {
      routeStateEl.textContent = "Live telemetry unavailable";
      routeStateEl.style.display = "block";
    } finally {
      isFetching = false;
      countdown = REFRESH_INTERVAL;
    }
  }

  // =======================
  // TABLE
  // =======================
  function renderTable(buses) {
    routeTableBody.innerHTML = "";
    buses.forEach(bus => {
      const tr = document.createElement("tr");
      tr.innerHTML = `<td>${bus.bus_id}</td>
                      <td>${bus.route_id}</td>
                      <td>${bus.soc.toFixed(1)}%</td>
                      <td style="color:${statusColor(bus.status)}">${bus.status}</td>`;
      tr.onclick = () => {
        selectedBusId = bus.bus_id;
        localStorage.setItem("selectedBusId", selectedBusId);
        map.flyTo([bus.lat, bus.lng], 15);
        busMarkers[bus.bus_id]?.openPopup();
      };
      routeTableBody.appendChild(tr);
    });
  }

  // =======================
  // LIFECYCLE
  // =======================
  mapSearchEl?.addEventListener("input", fetchRouteStatus);

  document.addEventListener("DOMContentLoaded", () => {
    initMap();
    fetchRouteStatus();

    setInterval(() => {
      countdown--;
      syncTimerEl.textContent = `${countdown}s`;
      syncProgressEl.style.width = `${(countdown / REFRESH_INTERVAL) * 100}%`;
      if (countdown <= 0) fetchRouteStatus();
    }, 1000);
  });
