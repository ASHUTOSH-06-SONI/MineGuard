const API_BASE = "";

const fallbackWorkers = [
  { id: 1, name: "Worker 1", location: "Tunnel 7", status: "CRITICAL", hr: 38, spo2: 89, temp: 38.5, pressure: 50, battery: 74, signal: 95, x: 420, y: 292, color: "#c83737", trend: "No movement detected" },
  { id: 2, name: "Worker 2", location: "Tunnel 9", status: "WARNING", hr: 142, spo2: 96, temp: 39.4, pressure: 49, battery: 80, signal: 91, x: 520, y: 360, color: "#cf6e21", trend: "Heat exposure rising" },
  { id: 3, name: "Worker 3", location: "Tunnel 9", status: "NORMAL", hr: 128, spo2: 94, temp: 37.8, pressure: 49, battery: 81, signal: 88, x: 555, y: 360, color: "#17885e", trend: "Normal operation" },
  { id: 4, name: "Worker 4", location: "Tunnel 5", status: "INFO", hr: 110, spo2: 97, temp: 37.1, pressure: 45, battery: 76, signal: 94, x: 420, y: 216, color: "#326fbd", trend: "Cooling break" },
  { id: 5, name: "Worker 5", location: "Tunnel 8", status: "NORMAL", hr: 102, spo2: 98, temp: 36.9, pressure: 43, battery: 79, signal: 97, x: 710, y: 292, color: "#17885e", trend: "Near exit route" }
];

const fallbackTunnels = [
  { id: "Surface", x: 92, y: 62, info: "Mine entrance, triage, command uplink" },
  { id: "T1", x: 190, y: 128, info: "Primary shaft, ventilation good, depth 120m" },
  { id: "T2", x: 310, y: 128, info: "Main junction, signal repeater online" },
  { id: "T4", x: 520, y: 128, info: "Gas monitoring active, ventilation fair" },
  { id: "T3", x: 190, y: 216, info: "Heat zone, avoid for evacuation" },
  { id: "T5", x: 420, y: 216, info: "Medical cache, route to Tunnel 7" },
  { id: "T6", x: 650, y: 216, info: "Stable, emergency lighting online" },
  { id: "T7", x: 420, y: 292, info: "Critical incident location, blocked east path" },
  { id: "T8", x: 710, y: 292, info: "Emergency Exit B approach" },
  { id: "T9", x: 535, y: 360, info: "Fresh air corridor and relay point" },
  { id: "Exit B", x: 795, y: 360, info: "Emergency exit, capacity 12/min" }
];

const fallbackLinks = [["Surface", "T1"], ["T1", "T2"], ["T2", "T4"], ["T1", "T3"], ["T2", "T5"], ["T4", "T6"], ["T5", "T7"], ["T6", "T8"], ["T7", "T9"], ["T8", "Exit B"], ["T9", "Exit B"]];
const fallbackAlerts = [
  { level: "critical", title: "Worker 1 at Tunnel 7", msg: "Fall protocol, HR 38 bpm, SpO2 89%, no movement.", action: "Dispatch Rescue" },
  { level: "high", title: "Worker 2 heat stress risk", msg: "HR 142 bpm with rising local temperature near Tunnel 9.", action: "Suggest Break" },
  { level: "medium", title: "Tunnel 4 gas pocket", msg: "CO trend rising. Reroute nearby workers through Tunnel 9.", action: "Reroute" },
  { level: "info", title: "Worker 5 near Exit B", msg: "Can act as relay for rescue communications.", action: "Assign Relay" }
];
const fallbackLogs = [
  "14:35:22 - W1 critical alert auto-sent",
  "14:35:45 - Supervisor ACK recorded",
  "14:36:10 - W2-W4 reroute command queued",
  "14:36:15 - Helmets confirmed route update",
  "14:37:00 - Hospital notification prepared"
];
const fallbackHistoryRows = [
  ["14:35:22", "W1", "Critical Fall", "38", "89%", "38.5 C", "Rescue recommended"],
  ["14:36:10", "W2-W4", "Reroute Alert", "128", "94%", "41.0 C", "New route sent"],
  ["13:45:00", "W3", "Heat Stress", "165", "96%", "45.0 C", "Break suggested"],
  ["12:20:18", "W5", "Relay Update", "104", "98%", "36.9 C", "Relay assigned"]
];

const tunnelCoordinates = {
  Surface: { x: 92, y: 62 },
  T1: { x: 190, y: 128 },
  T2: { x: 310, y: 128 },
  T4: { x: 520, y: 128 },
  T3: { x: 190, y: 216 },
  T5: { x: 420, y: 216 },
  T6: { x: 650, y: 216 },
  T7: { x: 420, y: 292 },
  T8: { x: 710, y: 292 },
  T9: { x: 535, y: 360 },
  "Exit B": { x: 795, y: 360 }
};

let workers = [];
let tunnels = fallbackTunnels.slice();
let links = fallbackLinks.slice();
let alerts = fallbackAlerts.slice();
let logs = fallbackLogs.slice();
let historyRows = fallbackHistoryRows.slice();
let selectedWorkerId = 1;
let showRoutes = true;
let depthView = false;
const themes = ["paper", "mono", "dark"];
let currentTheme = "paper";

const $ = (id) => document.getElementById(id);

function applyTheme(theme = currentTheme) {
  currentTheme = theme;
  document.body.dataset.theme = theme;
  const themeToggle = $("themeToggle");
  if (themeToggle) {
    themeToggle.textContent = theme === "paper" ? "Paper" : theme === "mono" ? "Mono" : "Dark";
  }
}

function fetchJson(url) {
  return fetch(`${API_BASE}${url}`)
    .then((res) => {
      if (!res.ok) {
        throw new Error(`Request failed: ${res.status}`);
      }
      return res.json();
    })
    .catch(() => null);
}

function normalizeWorker(w) {
  return {
    id: w.id,
    name: w.name || `Worker ${w.id}`,
    location: w.location || "Unknown",
    status: w.status || "NORMAL",
    hr: w.hr ?? w.heart_rate ?? 0,
    spo2: w.spo2 ?? 0,
    temp: w.temp ?? w.temperature_c ?? 36.8,
    pressure: w.pressure ?? w.pressure_atm ?? 50,
    battery: w.battery ?? w.battery_percent ?? 0,
    signal: w.signal ?? w.signal_quality ?? 0,
    x: w.x ?? 0,
    y: w.y ?? 0,
    color: w.color || "#17885e",
    trend: w.trend || "Normal operation",
  };
}

function normalizeAlert(a) {
  return {
    level: a.level || "info",
    title: a.title || "Alert",
    msg: a.msg || a.message || "No details available.",
    action: a.action || "Review",
  };
}

async function loadDashboardState() {
  const [workersData, alertsData, topologyData] = await Promise.all([
    fetchJson("/api/workers"),
    fetchJson("/api/alerts/active"),
    fetchJson("/api/mine/topology"),
  ]);

  if (workersData?.workers) {
    workers = workersData.workers.map(normalizeWorker);
  } else if (workersData) {
    workers = workersData.map(normalizeWorker);
  } else {
    workers = fallbackWorkers;
  }

  if (alertsData?.alerts) {
    alerts = alertsData.alerts.map(normalizeAlert);
  } else if (alertsData) {
    alerts = alertsData.map(normalizeAlert);
  } else {
    alerts = fallbackAlerts;
  }

  if (topologyData?.tunnels) {
    tunnels = topologyData.tunnels;
  } else {
    tunnels = fallbackTunnels;
  }

  if (topologyData?.links) {
    links = topologyData.links;
  } else {
    links = fallbackLinks;
  }
}

function renderWorkers() {
  const list = $("workers");
  if (!list) return;
  list.innerHTML = workers.map((worker) => `
    <button class="worker-item ${selectedWorkerId === worker.id ? "selected" : ""}" data-worker-id="${worker.id}">
      <div class="worker-topline">
        <span class="dot" style="background:${worker.color}"></span>
        <strong>${worker.name}</strong>
        <span class="chip ${worker.status.toLowerCase()}">${worker.status}</span>
      </div>
      <p>${worker.location}</p>
      <small>${worker.trend}</small>
    </button>
  `).join("");

  list.querySelectorAll(".worker-item").forEach((button) => {
    button.addEventListener("click", () => {
      selectedWorkerId = Number(button.dataset.workerId);
      renderWorkers();
      renderDetailCard();
    });
  });
}

function renderAlerts() {
  const list = $("alerts");
  if (!list) return;
  list.innerHTML = alerts.map((alert) => `
    <article class="alert-item ${alert.level}">
      <div>
        <span class="tag">${alert.level.toUpperCase()}</span>
        <h3>${alert.title}</h3>
        <p>${alert.msg}</p>
      </div>
      <button type="button">${alert.action}</button>
    </article>
  `).join("");
}

function renderDetailCard() {
  const card = $("detailCard");
  const badge = $("statusBadge");
  if (!card) return;
  const worker = workers.find((entry) => entry.id === selectedWorkerId) || workers[0];
  if (!worker) return;

  const color = worker.color || "#17885e";
  if (badge) {
    badge.textContent = worker.status;
    badge.style.borderColor = color;
    badge.style.color = color;
  }

  card.innerHTML = `
    <div class="detail-header">
      <div class="badge" style="background:${color}"></div>
      <div>
        <h3>${worker.name}</h3>
        <p>${worker.location}</p>
      </div>
    </div>
    <div class="vitals-grid">
      <div><span>HR</span><strong>${worker.hr}</strong></div>
      <div><span>SpO₂</span><strong>${worker.spo2}%</strong></div>
      <div><span>Temp</span><strong>${worker.temp}°C</strong></div>
      <div><span>Battery</span><strong>${worker.battery}%</strong></div>
    </div>
    <p class="trend">${worker.trend}</p>
  `;
}

function renderAll() {
  renderWorkers();
  renderAlerts();
  renderDetailCard();
}

(async function bootstrap() {
  applyTheme();
  await loadDashboardState();
  renderAll();
  const themeToggle = $("themeToggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const nextIndex = (themes.indexOf(currentTheme) + 1) % themes.length;
      applyTheme(themes[nextIndex]);
    });
  }
})();
