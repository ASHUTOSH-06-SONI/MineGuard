from __future__ import annotations

import asyncio
import random
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel


app = FastAPI(title="MineGuard Base Station API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class Worker(BaseModel):
    id: int
    name: str
    location: str
    status: str
    heart_rate: int
    spo2: int
    temperature_c: float
    pressure_atm: int
    battery_percent: int
    signal_quality: int
    trend: str


class Alert(BaseModel):
    level: str
    title: str
    message: str
    action: str


class Tunnel(BaseModel):
    id: str
    x: int
    y: int
    info: str


WORKERS: list[Worker] = [
    Worker(id=1, name="Ashutosh Soni", location="Tunnel 7", status="CRITICAL", heart_rate=38, spo2=89, temperature_c=38.5, pressure_atm=50, battery_percent=74, signal_quality=95, trend="No movement detected"),
    Worker(id=2, name="Meera Rao", location="Tunnel 9", status="WARNING", heart_rate=142, spo2=96, temperature_c=39.4, pressure_atm=49, battery_percent=80, signal_quality=91, trend="Heat exposure rising"),
    Worker(id=3, name="Ravi Kumar", location="Tunnel 9", status="NORMAL", heart_rate=128, spo2=94, temperature_c=37.8, pressure_atm=49, battery_percent=81, signal_quality=88, trend="Normal operation"),
    Worker(id=4, name="Nisha Patel", location="Tunnel 5", status="INFO", heart_rate=110, spo2=97, temperature_c=37.1, pressure_atm=45, battery_percent=76, signal_quality=94, trend="Cooling break"),
    Worker(id=5, name="Imran Khan", location="Tunnel 8", status="NORMAL", heart_rate=102, spo2=98, temperature_c=36.9, pressure_atm=43, battery_percent=79, signal_quality=97, trend="Near exit route"),
]

ALERTS: list[Alert] = [
    Alert(level="critical", title="Worker 1 at Tunnel 7", message="Fall protocol, HR 38 bpm, SpO2 89%, no movement.", action="Dispatch Rescue"),
    Alert(level="high", title="Worker 2 heat stress risk", message="HR 142 bpm with rising local temperature near Tunnel 9.", action="Suggest Break"),
    Alert(level="medium", title="Tunnel 4 gas pocket", message="CO trend rising. Reroute nearby workers through Tunnel 9.", action="Reroute"),
    Alert(level="info", title="Worker 5 near Exit B", message="Can act as relay for rescue communications.", action="Assign Relay"),
]

TUNNELS: list[Tunnel] = [
    Tunnel(id="Surface", x=92, y=62, info="Mine entrance, triage, command uplink"),
    Tunnel(id="T1", x=190, y=128, info="Primary shaft, ventilation good, depth 120m"),
    Tunnel(id="T2", x=310, y=128, info="Main junction, signal repeater online"),
    Tunnel(id="T4", x=520, y=128, info="Gas monitoring active, ventilation fair"),
    Tunnel(id="T3", x=190, y=216, info="Heat zone, avoid for evacuation"),
    Tunnel(id="T5", x=420, y=216, info="Medical cache, route to Tunnel 7"),
    Tunnel(id="T6", x=650, y=216, info="Stable, emergency lighting online"),
    Tunnel(id="T7", x=420, y=292, info="Critical incident location, blocked east path"),
    Tunnel(id="T8", x=710, y=292, info="Emergency Exit B approach"),
    Tunnel(id="T9", x=535, y=360, info="Fresh air corridor and relay point"),
    Tunnel(id="Exit B", x=795, y=360, info="Emergency exit, capacity 12/min"),
]

LINKS = [
    ["Surface", "T1"],
    ["T1", "T2"],
    ["T2", "T4"],
    ["T1", "T3"],
    ["T2", "T5"],
    ["T4", "T6"],
    ["T5", "T7"],
    ["T6", "T8"],
    ["T7", "T9"],
    ["T8", "Exit B"],
    ["T9", "Exit B"],
]

HISTORY = [
    {"time": "14:35:22", "worker": "W1", "event": "Critical Fall", "heart_rate": 38, "spo2": "89%", "temperature": "38.5 C", "action": "Rescue recommended"},
    {"time": "14:36:10", "worker": "W2-W4", "event": "Reroute Alert", "heart_rate": 128, "spo2": "94%", "temperature": "41.0 C", "action": "New route sent"},
    {"time": "13:45:00", "worker": "W3", "event": "Heat Stress", "heart_rate": 165, "spo2": "96%", "temperature": "45.0 C", "action": "Break suggested"},
    {"time": "12:20:18", "worker": "W5", "event": "Relay Update", "heart_rate": 104, "spo2": "98%", "temperature": "36.9 C", "action": "Relay assigned"},
]


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "online", "timestamp": datetime.now(timezone.utc).isoformat()}


@app.get("/api/workers")
async def get_workers() -> list[Worker]:
    return WORKERS


@app.get("/api/alerts/active")
async def get_active_alerts() -> list[Alert]:
    return ALERTS


@app.get("/api/mine/topology")
async def get_mine_topology() -> dict[str, Any]:
    return {"tunnels": TUNNELS, "links": LINKS}


@app.get("/api/history")
async def get_history() -> list[dict[str, Any]]:
    return HISTORY


@app.websocket("/ws/dashboard")
async def dashboard_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            payload = {
                "type": "telemetry",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "workers": [simulate_worker(worker).model_dump() for worker in WORKERS],
                "latency_ms": random.randint(240, 330),
            }
            await websocket.send_json(payload)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return


def simulate_worker(worker: Worker) -> Worker:
    if worker.id == 1:
        return worker

    return worker.model_copy(
        update={
            "heart_rate": clamp(worker.heart_rate + random.randint(-3, 3), 92, 165),
            "spo2": clamp(worker.spo2 + random.randint(-1, 1), 92, 99),
            "temperature_c": round(clamp_float(worker.temperature_c + random.uniform(-0.08, 0.08), 36.5, 41.5), 1),
            "signal_quality": clamp(worker.signal_quality + random.randint(-2, 2), 82, 99),
        }
    )


def clamp(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def clamp_float(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))
