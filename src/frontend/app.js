const API_BASE = "http://localhost:8080";

const fallbackWorkers = [
  { id: 1, name: "Ashutosh Soni", location: "Tunnel 7", status: "CRITICAL", hr: 38, spo2: 89, temp: 38.5, pressure: 50, battery: 74, signal: 95, x: 420, y: 292, color: "#c83737", trend: "No movement detected" },
  { id: 2, name: "Meera Rao", location: "Tunnel 9", status: "WARNING", hr: 142, spo2: 96, temp: 39.4, pressure: 49, battery: 80, signal: 91, x: 520, y: 360, color: "#cf6e21", trend: "Heat exposure rising" },
  { id: 3, name: "Ravi Kumar", location: "Tunnel 9", status: "NORMAL", hr: 128, spo2: 94, temp: 37.8, pressure: 49, battery: 81, signal: 88, x: 555, y: 360, color: "#17885e", trend: "Normal operation" },
  { id: 4, name: "Nisha Patel", location: "Tunnel 5", status: "INFO", hr: 110, spo2: 97, temp: 37.1, pressure: 45, battery: 76, signal: 94, x: 420, y: 216, color: "#326fbd", trend: "Cooling break" },
  { id: 5, name: "Imran Khan", location: "Tunnel 8", status: "NORMAL", hr: 102, spo2: 98, temp: 36.9, pressure: 43, battery: 79, signal: 97, x: 710, y: 292, color: "#17885e", trend: "Near exit route" }
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

let workers = [...fallbackWorkers];
let tunnels = [...fallbackTunnels];
let links = [...fallbackLinks];
let alerts = [...fallbackAlerts];
let logs = [...fallbackLogs];
let historyRows = [...fallbackHistoryRows];
let selectedWorkerId = 1;
let showRoutes = true;
let depthView = false;
let websocket = null;
let usingLiveBackend = false;

const $ = (id) => document.getElementById(id);

function normalizeWorker(raw) {
  const base = fallbackWorkers.find((worker) => worker.id === Number(raw.id)) || fallbackWorkers[0];
  return {
    ...base,
    id: Number(raw.id),
    name: raw.name || base.name,
    location: raw.location || base.location,
    status: (raw.status || base.status).toUpperCase(),
    hr: Number(raw.heart_rate ?? raw.hr ?? base.hr),
    spo2: Number(raw.spo2 ?? base.spo2),
    temp: Number(raw.temperature_c ?? raw.temp ?? base.temp),
    pressure: Number(raw.pressure_atm ?? raw.pressure ?? base.pressure),
    battery: Number(raw.battery_percent ?? raw.battery ?? base.battery),
    signal: Number(raw.signal_quality ?? raw.signal ?? base.signal),
    trend: raw.trend || base.trend,
    x: base.x,
    y: base.y,
    color: base.color,
  };
}

function normalizeAlert(raw) {
  return {
    level: String(raw.level || "info").toLowerCase(),
    title: raw.title || "System update",
    msg: raw.message || raw.msg || "No additional details.",
    action: raw.action || "Review",
  };
}

function mapServerData(serverWorkers = [], serverAlerts = [], topology = { tunnels: [], links: [] }, history = []) {
  const baseById = new Map(fallbackWorkers.map((worker) => [worker.id, worker]));
  workers = serverWorkers.length ? serverWorkers.map((worker) => normalizeWorker(worker)) : [...fallbackWorkers];

  if (serverWorkers.length === 0) {
    workers = [...fallbackWorkers];
  }

  workers = workers.map((worker) => {
    const base = baseById.get(worker.id) || fallbackWorkers[0];
    return { ...base, ...worker, x: base.x, y: base.y, color: base.color };
  });

  alerts = serverAlerts.length ? serverAlerts.map(normalizeAlert) : [...fallbackAlerts];
  tunnels = topology.tunnels?.length ? topology.tunnels.map((tunnel) => ({
    id: tunnel.id,
    x: typeof tunnel.x === "number" ? tunnel.x : fallbackTunnels.find((item) => item.id === String(tunnel.id))?.x || 0,
    y: typeof tunnel.y === "number" ? tunnel.y : fallbackTunnels.find((item) => item.id === String(tunnel.id))?.y || 0,
    info: tunnel.info || tunnel.name || "Mine tunnel",
  })) : [...fallbackTunnels];
  links = topology.links?.length ? topology.links : [...fallbackLinks];

  historyRows = history.length ? history.map((row) => [
    row.time || "--:--",
    row.worker || "--",
    row.event || row.title || "Update",
    String(row.heart_rate ?? "--"),
    String(row.spo2 ?? "--"),
    String(row.temperature ?? "--"),
    row.action || "Reviewed",
  ]) : [...fallbackHistoryRows];

  logs = fallbackLogs;
  selectedWorkerId = Math.min(Math.max(selectedWorkerId, 1), workers.length);
}

async function fetchJson(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    throw new Error(`Request failed: ${response.status}`);
  }
  return response.json();
}

async function hydrateDashboard() {
  try {
    const [serverWorkers, serverAlerts, topology, history] = await Promise.all([
      fetchJson(`${API_BASE}/api/workers`),
      fetchJson(`${API_BASE}/api/alerts/active`),
      fetchJson(`${API_BASE}/api/mine/topology`),
      fetchJson(`${API_BASE}/api/history`),
    ]);

    mapServerData(serverWorkers, serverAlerts, topology, history);
    usingLiveBackend = true;
    $("sync").textContent = "live";
    $("footerSync").textContent = "live";
  } catch (error) {
    mapServerData();
    usingLiveBackend = false;
    console.warn("Backend unavailable, using local demo data:", error);
  }

  renderAll();
  connectWebSocket();
}

function connectWebSocket() {
  if (websocket) {
    websocket.close();
  }

  try {
    const wsUrl = `${API_BASE.replace(/^http/, "ws")}/ws/dashboard`;
    websocket = new WebSocket(wsUrl);
    websocket.onmessage = (event) => {
      const payload = JSON.parse(event.data);
      if (payload.type === "telemetry" && Array.isArray(payload.workers)) {
        workers = workers.map((worker) => {
          const live = payload.workers.find((item) => Number(item.id) === worker.id);
          if (!live) return worker;
          return normalizeWorker({
            ...worker,
            ...live,
            id: worker.id,
          });
        });
        renderAll();
      }
    };
    websocket.onclose = () => {
      if (!usingLiveBackend) return;
      setTimeout(connectWebSocket, 2000);
    };
  } catch (error) {
    console.warn("WebSocket unavailable:", error);
  }
}

function renderAlerts() {
  $("alerts").innerHTML = alerts.map((alert) => `
    <article class="alert ${alert.level}">
      <header><strong>${alert.title}</strong><span>${alert.level.toUpperCase()}</span></header>
      <p>${alert.msg}</p>
      <button type="button">${alert.action}</button>
    </article>
  `).join("");
}

function renderWorkers() {
  $("workers").innerHTML = workers.map((worker) => `
    <article class="worker-card ${worker.id === selectedWorkerId ? "selected" : ""}" data-worker="${worker.id}">
      <header><strong>W${worker.id} - ${worker.name}</strong><span>${worker.status}</span></header>
      <p>${worker.location} | ${worker.trend}</p>
      <div class="vital-row">
        <span>HR <strong>${worker.hr}</strong></span>
        <span>SpO2 <strong>${worker.spo2}%</strong></span>
        <span>Temp <strong>${worker.temp.toFixed(1)} C</strong></span>
        <span>Signal <strong>${worker.signal}%</strong></span>
      </div>
    </article>
  `).join("");

  document.querySelectorAll(".worker-card").forEach((card) => {
    card.addEventListener("click", () => {
      selectedWorkerId = Number(card.dataset.worker);
      renderAll();
      const chosen = workers.find((worker) => worker.id === selectedWorkerId);
      setMapDetail(`W${selectedWorkerId} selected. ${chosen?.trend || "No update available."}`);
    });
  });
}

function renderMap() {
  const nodeById = Object.fromEntries(tunnels.map((tunnel) => [tunnel.id, tunnel]));
  $("depthGrid").innerHTML = Array.from({ length: 6 }, (_, index) => {
    const y = 70 + index * 58;
    return `<path class="depth-line" d="M 50 ${y} H 850" /><text x="52" y="${y - 6}" fill="#71817e" font-size="11">${index * 100}m</text>`;
  }).join("");
  $("hazardsLayer").innerHTML = `
    <circle cx="190" cy="232" r="78" fill="url(#heat)" />
    <text x="124" y="308" class="hazard-label">Heat &gt;45 C</text>
    <circle cx="535" cy="268" r="84" fill="url(#gas)" />
    <text x="548" y="262" class="hazard-label">Gas watch</text>
    <rect x="470" y="112" width="98" height="32" rx="5" fill="rgba(200,55,55,0.22)" stroke="#c83737" />
    <text x="481" y="133" class="hazard-label">Rockfall</text>
  `;
  $("tunnelsLayer").innerHTML = links.map(([from, to]) => {
    const a = nodeById[from];
    const b = nodeById[to];
    if (!a || !b) return "";
    return `<path class="tunnel" data-link="${from}-${to}" d="M ${a.x} ${a.y} L ${b.x} ${b.y}" />`;
  }).join("");
  $("routesLayer").innerHTML = showRoutes ? `
    <path class="route" d="M 92 62 L 190 128 L 310 128 L 420 216 L 420 292" />
    <path class="route" d="M 420 292 L 535 360 L 795 360" />
  ` : "";
  $("nodesLayer").innerHTML = tunnels.map((tunnel) => `
    <g class="map-node" data-tunnel="${tunnel.id}">
      <circle class="node" cx="${tunnel.x}" cy="${depthView ? tunnel.y + tunnel.y * 0.05 : tunnel.y}" r="${tunnel.id.includes("Exit") || tunnel.id === "Surface" ? 18 : 13}" />
      <text class="node-label" x="${tunnel.x + 18}" y="${(depthView ? tunnel.y + tunnel.y * 0.05 : tunnel.y) + 5}">${tunnel.id}</text>
    </g>
  `).join("");
  $("workersLayer").innerHTML = workers.map((worker) => `
    <g class="worker" data-worker="${worker.id}" transform="translate(${worker.x}, ${depthView ? worker.y + worker.y * 0.05 : worker.y})">
      <circle r="${worker.id === selectedWorkerId ? 17 : 14}" fill="${worker.color}" />
      <text>W${worker.id}</text>
    </g>
  `).join("");

  document.querySelectorAll(".map-node").forEach((node) => {
    node.addEventListener("click", () => {
      const tunnel = tunnels.find((item) => item.id === node.dataset.tunnel);
      setMapDetail(`${tunnel?.id || "Tunnel"}: ${tunnel?.info || "No details available."}`);
    });
  });
  document.querySelectorAll(".worker").forEach((node) => {
    node.addEventListener("click", () => {
      selectedWorkerId = Number(node.dataset.worker);
      renderAll();
    });
  });
}

function sparkPath(values) {
  const width = 140;
  const height = 58;
  const min = Math.min(...values);
  const max = Math.max(...values);
  return values.map((value, index) => {
    const x = (index / (values.length - 1)) * width;
    const y = height - ((value - min) / Math.max(max - min, 1)) * (height - 10) - 5;
    return `${index === 0 ? "M" : "L"} ${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ");
}

function renderVitals() {
  const worker = workers.find((item) => item.id === selectedWorkerId) || workers[0];
  $("workerSelect").innerHTML = workers.map((item) => `<option value="${item.id}" ${item.id === selectedWorkerId ? "selected" : ""}>W${item.id} ${item.name}</option>`).join("");
  const metrics = [
    ["Heart Rate", `${worker.hr} bpm`, worker.hr > 150 || worker.hr < 45 ? "ALARM" : "STABLE", [112, 120, 126, 138, 145, worker.hr]],
    ["SpO2", `${worker.spo2}%`, worker.spo2 < 90 ? "DROPPING" : "NORMAL", [98, 97, 96, 94, 92, worker.spo2]],
    ["Temperature", `${worker.temp.toFixed(1)} C`, worker.temp > 39 ? "RISING" : "FLAT", [36.8, 37.1, 37.4, 37.9, 38.2, worker.temp]],
    ["Pressure", `${worker.pressure} atm`, "STABLE", [44, 45, 47, 49, 50, worker.pressure]],
    ["Movement", worker.id === 1 ? "None" : "Active", worker.id === 1 ? "2 min still" : "Last 2s", worker.id === 1 ? [22, 18, 8, 2, 0, 0] : [20, 24, 18, 28, 23, 26]]
  ];

  $("vitals").innerHTML = metrics.map(([name, value, trend, series]) => `
    <article class="vital-card">
      <h3>${name}</h3>
      <strong>${value}</strong>
      <span class="trend">${trend}</span>
      <svg class="spark" viewBox="0 0 140 58" preserveAspectRatio="none">
        <path d="${sparkPath(series)}" />
      </svg>
    </article>
  `).join("");
}

function renderStaticLists() {
  $("log").innerHTML = logs.map((line) => `<div class="log-line">${line}</div>`).join("");
  $("history").innerHTML = historyRows.map((row) => `<tr>${row.map((cell) => `<td>${cell}</td>`).join("")}</tr>`).join("");
}

function renderAll() {
  renderAlerts();
  renderWorkers();
  renderMap();
  renderVitals();
  renderStaticLists();
}

function setMapDetail(text) {
  $("mapDetails").textContent = text;
}

function tick() {
  const now = new Date();
  $("clock").textContent = now.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "Asia/Kolkata" }) + " IST";
  const latency = 240 + Math.round(Math.random() * 90);
  $("latency-pill").textContent = `${latency} ms`;
  $("sync").textContent = usingLiveBackend ? "live" : `${1 + Math.round(Math.random() * 3)}s ago`;
  $("footerSync").textContent = $("sync").textContent;
}

function simulateTelemetry() {
  if (usingLiveBackend) return;

  workers.forEach((worker) => {
    if (worker.id !== 1) {
      worker.hr = Math.max(92, Math.min(165, worker.hr + Math.round(Math.random() * 6 - 3)));
      worker.spo2 = Math.max(92, Math.min(99, worker.spo2 + Math.round(Math.random() * 2 - 1)));
      worker.temp = Math.max(36.5, Math.min(41.5, worker.temp + (Math.random() - 0.48) * 0.16));
      worker.signal = Math.max(82, Math.min(99, worker.signal + Math.round(Math.random() * 4 - 2)));
    }
  });
  const avgBattery = Math.round(workers.reduce((sum, worker) => sum + worker.battery, 0) / workers.length);
  $("battery").textContent = `${avgBattery}%`;
  renderWorkers();
  renderVitals();
}

$("routesToggle").addEventListener("click", () => {
  showRoutes = !showRoutes;
  $("routesToggle").classList.toggle("active", showRoutes);
  renderMap();
});

$("viewToggle").addEventListener("click", () => {
  depthView = !depthView;
  $("viewToggle").classList.toggle("active", depthView);
  renderMap();
});

$("exportBtn").addEventListener("click", () => setMapDetail("Rescue briefing export queued: active alerts, selected route, and Tunnel 7 vitals."));
$("csvBtn").addEventListener("click", () => {
  const csv = ["Time,Worker,Event,HR,SpO2,Temp,Action", ...historyRows.map((row) => row.join(","))].join("\n");
  const blob = new Blob([csv], { type: "text/csv" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "mineguard-shift-log.csv";
  link.click();
  URL.revokeObjectURL(link.href);
});
$("workerSelect").addEventListener("change", (event) => {
  selectedWorkerId = Number(event.target.value);
  renderAll();
});

hydrateDashboard();
tick();
setInterval(tick, 1000);
setInterval(simulateTelemetry, 2800);
