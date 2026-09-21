from __future__ import annotations

import asyncio
import copy
import json
import math
import os
import random
import sqlite3
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
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

DB_PATH = os.path.join(os.path.dirname(__file__), "mineguard.db")

REGULATORY_THRESHOLDS = {
    "hr_warning": 120,
    "hr_critical": 160,
    "spo2_warning": 92,
    "spo2_critical": 85,
    "o2_warning": 19.5,
    "o2_critical": 18.0,
    "ch4_warning": 1.0,
    "ch4_critical": 2.0,
    "co_warning": 25,
    "co_critical": 60,
    "co2_warning": 1000,
    "co2_critical": 2500,
    "temp_warning": 38.0,
    "temp_critical": 40.0,
    "activity_warning": 0.75,
    "activity_critical": 0.9,
}

RESEARCH_THRESHOLDS = {
    "hr_warning": 110,
    "hr_critical": 140,
    "spo2_warning": 95,
    "spo2_critical": 90,
    "o2_warning": 20.0,
    "o2_critical": 19.0,
    "ch4_warning": 0.7,
    "ch4_critical": 1.5,
    "co_warning": 20,
    "co_critical": 40,
    "co2_warning": 800,
    "co2_critical": 1800,
    "temp_warning": 37.5,
    "temp_critical": 39.5,
    "activity_warning": 0.6,
    "activity_critical": 0.8,
}

DEFAULT_GRAPH = {
    "Surface": {"T1": {"distance": 90, "hazard": 0.08, "gas": 0.06, "oxygen": 0.04, "thermal": 0.05, "physiological": 0.02}},
    "T1": {"T2": {"distance": 80, "hazard": 0.10, "gas": 0.08, "oxygen": 0.05, "thermal": 0.07, "physiological": 0.03}, "T3": {"distance": 120, "hazard": 0.35, "gas": 0.18, "oxygen": 0.12, "thermal": 0.28, "physiological": 0.14}},
    "T2": {"T4": {"distance": 150, "hazard": 0.18, "gas": 0.22, "oxygen": 0.08, "thermal": 0.16, "physiological": 0.08}, "T5": {"distance": 110, "hazard": 0.16, "gas": 0.10, "oxygen": 0.07, "thermal": 0.12, "physiological": 0.09}},
    "T3": {"T2": {"distance": 95, "hazard": 0.33, "gas": 0.15, "oxygen": 0.18, "thermal": 0.30, "physiological": 0.15}},
    "T4": {"T6": {"distance": 220, "hazard": 0.12, "gas": 0.09, "oxygen": 0.05, "thermal": 0.10, "physiological": 0.05}},
    "T5": {"T7": {"distance": 130, "hazard": 0.42, "gas": 0.14, "oxygen": 0.09, "thermal": 0.22, "physiological": 0.12}},
    "T6": {"T8": {"distance": 170, "hazard": 0.20, "gas": 0.15, "oxygen": 0.06, "thermal": 0.18, "physiological": 0.07}},
    "T7": {"T9": {"distance": 150, "hazard": 0.28, "gas": 0.22, "oxygen": 0.10, "thermal": 0.24, "physiological": 0.18}, "Exit B": {"distance": 160, "hazard": 0.68, "gas": 0.55, "oxygen": 0.22, "thermal": 0.48, "physiological": 0.26}},
    "T8": {"Exit B": {"distance": 110, "hazard": 0.11, "gas": 0.08, "oxygen": 0.05, "thermal": 0.10, "physiological": 0.05}},
    "T9": {"Exit B": {"distance": 120, "hazard": 0.18, "gas": 0.16, "oxygen": 0.07, "thermal": 0.14, "physiological": 0.09}},
    "Exit B": {},
}

BASE_WORKERS = [
    {"id": 1, "name": "Worker 1", "location": "T7", "status": "NORMAL", "hr": 98, "spo2": 97, "o2": 20.8, "ch4": 0.12, "co": 12, "co2": 690, "temperature_c": 36.8, "activity": 0.28, "pressure_atm": 50, "battery_percent": 74, "signal_quality": 95, "baseline_hr": 96, "baseline_spo2": 98, "baseline_temp": 36.7, "expected_hr": 102},
    {"id": 2, "name": "Worker 2", "location": "T9", "status": "NORMAL", "hr": 101, "spo2": 96, "o2": 20.5, "ch4": 0.18, "co": 15, "co2": 720, "temperature_c": 37.2, "activity": 0.45, "pressure_atm": 49, "battery_percent": 80, "signal_quality": 91, "baseline_hr": 94, "baseline_spo2": 98, "baseline_temp": 36.8, "expected_hr": 108},
    {"id": 3, "name": "Worker 3", "location": "T9", "status": "NORMAL", "hr": 110, "spo2": 94, "o2": 20.1, "ch4": 0.2, "co": 17, "co2": 760, "temperature_c": 37.6, "activity": 0.58, "pressure_atm": 49, "battery_percent": 81, "signal_quality": 88, "baseline_hr": 95, "baseline_spo2": 97, "baseline_temp": 36.9, "expected_hr": 108},
    {"id": 4, "name": "Worker 4", "location": "T5", "status": "NORMAL", "hr": 104, "spo2": 97, "o2": 20.7, "ch4": 0.14, "co": 14, "co2": 680, "temperature_c": 37.1, "activity": 0.38, "pressure_atm": 45, "battery_percent": 76, "signal_quality": 94, "baseline_hr": 97, "baseline_spo2": 98, "baseline_temp": 36.8, "expected_hr": 105},
    {"id": 5, "name": "Worker 5", "location": "T8", "status": "NORMAL", "hr": 102, "spo2": 98, "o2": 20.9, "ch4": 0.11, "co": 13, "co2": 640, "temperature_c": 36.9, "activity": 0.29, "pressure_atm": 43, "battery_percent": 79, "signal_quality": 97, "baseline_hr": 98, "baseline_spo2": 99, "baseline_temp": 36.7, "expected_hr": 103},
]


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


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def clamp_int(value: int, minimum: int, maximum: int) -> int:
    return max(minimum, min(maximum, value))


def calculate_edge_cost(edge_metrics: dict[str, Any]) -> float:
    if isinstance(edge_metrics, (int, float)):
        return float(edge_metrics)
    if not isinstance(edge_metrics, dict):
        return 0.0
    distance = float(edge_metrics.get("distance", 0.0))
    hazard = float(edge_metrics.get("hazard", 0.0))
    gas = float(edge_metrics.get("gas", 0.0))
    oxygen = float(edge_metrics.get("oxygen", 0.0))
    thermal = float(edge_metrics.get("thermal", 0.0))
    physiological = float(edge_metrics.get("physiological", 0.0))
    return distance * 0.35 + hazard * 25 + gas * 30 + oxygen * 18 + thermal * 20 + physiological * 10


def _status_from_score(score: float) -> str:
    if score >= 0.75:
        return "CRITICAL"
    if score >= 0.45:
        return "WARNING"
    return "NORMAL"


def _compute_delta(current: float, previous: float | None) -> float:
    if previous is None:
        return 0.0
    return current - previous


def assess_emergency_state(sensor: dict[str, Any], history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    metrics = dict(sensor)
    previous = history[-1] if history and len(history) else None
    current_hr = float(metrics.get("hr", 0.0))
    current_spo2 = float(metrics.get("spo2", 100.0))
    current_o2 = float(metrics.get("o2", 20.9))
    current_ch4 = float(metrics.get("ch4", 0.0))
    current_co = float(metrics.get("co", 0.0))
    current_co2 = float(metrics.get("co2", 0.0))
    current_temp = float(metrics.get("temp_c", metrics.get("temperature_c", 36.8)))

    previous_hr = float(previous.get("hr", current_hr)) if previous else current_hr
    previous_spo2 = float(previous.get("spo2", current_spo2)) if previous else current_spo2
    previous_o2 = float(previous.get("o2", current_o2)) if previous else current_o2
    previous_ch4 = float(previous.get("ch4", current_ch4)) if previous else current_ch4
    previous_co = float(previous.get("co", current_co)) if previous else current_co
    previous_co2 = float(previous.get("co2", current_co2)) if previous else current_co2
    previous_temp = float(previous.get("temp_c", previous.get("temperature_c", current_temp))) if previous else current_temp

    rate_of_change = {
        "hr_delta": round(_compute_delta(current_hr, previous_hr), 2),
        "spo2_delta": round(_compute_delta(current_spo2, previous_spo2), 2),
        "o2_delta": round(_compute_delta(current_o2, previous_o2), 2),
        "ch4_delta": round(_compute_delta(current_ch4, previous_ch4), 2),
        "co_delta": round(_compute_delta(current_co, previous_co), 2),
        "co2_delta": round(_compute_delta(current_co2, previous_co2), 2),
        "temp_delta": round(_compute_delta(current_temp, previous_temp), 2),
    }

    violations: list[str] = []
    score = 0.0

    hr = float(metrics.get("hr", 0.0))
    spo2 = float(metrics.get("spo2", 100.0))
    o2 = float(metrics.get("o2", 20.9))
    ch4 = float(metrics.get("ch4", 0.0))
    co = float(metrics.get("co", 0.0))
    co2 = float(metrics.get("co2", 0.0))
    temp_c = float(metrics.get("temp_c", metrics.get("temperature_c", 36.8)))
    activity = float(metrics.get("activity", 0.0))

    # Regulatory thresholds are authoritative; research thresholds are lower-severity signals.
    if hr >= REGULATORY_THRESHOLDS["hr_critical"]:
        violations.append("hr_critical")
        score += 0.32
    elif hr >= REGULATORY_THRESHOLDS["hr_warning"] or hr >= RESEARCH_THRESHOLDS["hr_warning"]:
        violations.append("hr_warning")
        score += 0.18
    if spo2 <= REGULATORY_THRESHOLDS["spo2_critical"]:
        violations.append("spo2_critical")
        score += 0.28
    elif spo2 <= REGULATORY_THRESHOLDS["spo2_warning"] or spo2 <= RESEARCH_THRESHOLDS["spo2_warning"]:
        violations.append("spo2_warning")
        score += 0.14
    if o2 <= REGULATORY_THRESHOLDS["o2_critical"]:
        violations.append("o2_critical")
        score += 0.25
    elif o2 <= REGULATORY_THRESHOLDS["o2_warning"] or o2 <= RESEARCH_THRESHOLDS["o2_warning"]:
        violations.append("o2_warning")
        score += 0.12
    if ch4 >= REGULATORY_THRESHOLDS["ch4_critical"]:
        violations.append("ch4_critical")
        score += 0.28
    elif ch4 >= REGULATORY_THRESHOLDS["ch4_warning"] or ch4 >= RESEARCH_THRESHOLDS["ch4_warning"]:
        violations.append("ch4_warning")
        score += 0.14
    if co >= REGULATORY_THRESHOLDS["co_critical"]:
        violations.append("co_critical")
        score += 0.25
    elif co >= REGULATORY_THRESHOLDS["co_warning"] or co >= RESEARCH_THRESHOLDS["co_warning"]:
        violations.append("co_warning")
        score += 0.12
    if co2 >= REGULATORY_THRESHOLDS["co2_critical"]:
        violations.append("co2_critical")
        score += 0.18
    elif co2 >= REGULATORY_THRESHOLDS["co2_warning"] or co2 >= RESEARCH_THRESHOLDS["co2_warning"]:
        violations.append("co2_warning")
        score += 0.08
    if temp_c >= REGULATORY_THRESHOLDS["temp_critical"]:
        violations.append("temp_critical")
        score += 0.2
    elif temp_c >= REGULATORY_THRESHOLDS["temp_warning"] or temp_c >= RESEARCH_THRESHOLDS["temp_warning"]:
        violations.append("temp_warning")
        score += 0.1
    if activity >= REGULATORY_THRESHOLDS["activity_critical"]:
        violations.append("activity_critical")
        score += 0.12
    elif activity >= REGULATORY_THRESHOLDS["activity_warning"] or activity >= RESEARCH_THRESHOLDS["activity_warning"]:
        violations.append("activity_warning")
        score += 0.06

    if previous:
        if abs(rate_of_change["hr_delta"]) >= 12:
            violations.append("rate_hr")
            score += 0.12
        if abs(rate_of_change["spo2_delta"]) >= 5:
            violations.append("rate_spo2")
            score += 0.08
        if abs(rate_of_change["o2_delta"]) >= 1.0:
            violations.append("rate_o2")
            score += 0.08
        if abs(rate_of_change["ch4_delta"]) >= 0.5:
            violations.append("rate_ch4")
            score += 0.08
        if abs(rate_of_change["temp_delta"]) >= 1.5:
            violations.append("rate_temp")
            score += 0.08

    score = clamp(score, 0.0, 1.0)
    critical_count = sum(1 for violation in violations if "critical" in violation)
    warning_count = sum(1 for violation in violations if "warning" in violation)
    if critical_count > 0 and score >= 0.68:
        status = "CRITICAL"
    elif warning_count > 0 or score >= 0.45:
        status = "WARNING"
    else:
        status = "NORMAL"
    if critical_count > 0 and warning_count == 0 and score < 0.68:
        status = "WARNING"

    return {
        "status": status,
        "score": round(score, 4),
        "violations": violations,
        "rate_of_change": rate_of_change,
        "thresholds": {
            "regulatory": REGULATORY_THRESHOLDS,
            "research": RESEARCH_THRESHOLDS,
        },
    }


def calculate_physiological_risk(metrics: dict[str, Any]) -> dict[str, Any]:
    hr = float(metrics.get("hr", 0.0))
    spo2 = float(metrics.get("spo2", 100.0))
    temp_c = float(metrics.get("temperature_c", metrics.get("temp_c", 36.8)))
    activity = float(metrics.get("activity", 0.0))
    baseline_hr = float(metrics.get("baseline_hr", hr))
    baseline_spo2 = float(metrics.get("baseline_spo2", spo2))
    baseline_temp = float(metrics.get("baseline_temp", temp_c))
    expected_hr = float(metrics.get("expected_hr", baseline_hr + 12))

    delta_hr = hr - expected_hr
    delta_temp = temp_c - baseline_temp
    spo2_drop = baseline_spo2 - spo2
    activity_factor = max(0.0, activity - 0.5)

    score = (
        clamp(abs(delta_hr) / 60.0, 0.0, 1.0) * 0.42
        + clamp(max(0.0, spo2_drop) / 12.0, 0.0, 1.0) * 0.25
        + clamp(max(0.0, delta_temp) / 4.0, 0.0, 1.0) * 0.18
        + clamp(activity_factor / 0.6, 0.0, 1.0) * 0.15
    )
    score = clamp(score, 0.0, 1.0)
    state = _status_from_score(score)
    if delta_hr >= 30 or spo2 <= 88 or temp_c >= 39.5 or activity >= 0.9:
        state = "CRITICAL"
    elif delta_hr >= 12 or spo2 <= 92 or temp_c >= 38.3 or activity >= 0.7:
        state = "WARNING"

    return {
        "state": state,
        "score": round(score, 4),
        "delta_hr": round(delta_hr, 2),
        "delta_temp": round(delta_temp, 2),
        "spo2_drop": round(spo2_drop, 2),
        "activity_factor": round(activity_factor, 2),
    }


def calculate_environmental_risk(metrics: dict[str, Any]) -> dict[str, Any]:
    o2 = float(metrics.get("o2", 20.9))
    ch4 = float(metrics.get("ch4", 0.0))
    co = float(metrics.get("co", 0.0))
    co2 = float(metrics.get("co2", 0.0))
    temp_c = float(metrics.get("temperature_c", metrics.get("temp_c", 36.8)))
    relative_humidity = float(metrics.get("relative_humidity", 0.5))
    trends = metrics.get("trends", {})

    trend_o2 = float(trends.get("o2", 0.0))
    trend_ch4 = float(trends.get("ch4", 0.0))
    trend_co = float(trends.get("co", 0.0))
    trend_co2 = float(trends.get("co2", 0.0))
    trend_temp = float(trends.get("temp", 0.0))

    score = 0.0
    score += clamp((20.9 - o2) / 5.0, 0.0, 1.0) * 0.22
    score += clamp(ch4 / 3.0, 0.0, 1.0) * 0.25
    score += clamp(co / 100.0, 0.0, 1.0) * 0.2
    score += clamp(co2 / 4000.0, 0.0, 1.0) * 0.13
    score += clamp((temp_c - 36.8) / 6.0, 0.0, 1.0) * 0.1
    score += clamp(abs(trend_o2) / 2.0, 0.0, 1.0) * 0.05
    score += clamp(abs(trend_ch4) / 2.0, 0.0, 1.0) * 0.05
    score += clamp(abs(relative_humidity - 0.5) / 0.5, 0.0, 1.0) * 0.04

    if o2 <= REGULATORY_THRESHOLDS["o2_critical"] or ch4 >= REGULATORY_THRESHOLDS["ch4_critical"] or co >= REGULATORY_THRESHOLDS["co_critical"] or temp_c >= REGULATORY_THRESHOLDS["temp_critical"]:
        state = "CRITICAL"
    elif o2 <= REGULATORY_THRESHOLDS["o2_warning"] or ch4 >= REGULATORY_THRESHOLDS["ch4_warning"] or co >= REGULATORY_THRESHOLDS["co_warning"] or temp_c >= REGULATORY_THRESHOLDS["temp_warning"] or trend_o2 < -0.5 or trend_ch4 > 0.5:
        state = "WARNING"
    else:
        state = "NORMAL"

    if score > 0.75:
        state = "CRITICAL"
    elif score > 0.45:
        state = "WARNING"

    return {
        "state": state,
        "score": round(clamp(score, 0.0, 1.0), 4),
        "trends": {
            "o2": trend_o2,
            "ch4": trend_ch4,
            "co": trend_co,
            "co2": trend_co2,
            "temp": trend_temp,
        },
    }


def compute_multimodal_worker_state(
    physiological: dict[str, Any],
    environmental: dict[str, Any],
    activity: float,
    exposure_minutes: int = 0,
    sensor_confidence: float = 0.8,
) -> dict[str, Any]:
    phys_score = float(physiological.get("score", 0.0))
    env_score = float(environmental.get("score", 0.0))
    activity_score = clamp(activity, 0.0, 1.0)
    exposure_score = clamp(exposure_minutes / 30.0, 0.0, 1.0)
    confidence_score = clamp(sensor_confidence, 0.0, 1.0)

    overall_score = (
        phys_score * 0.42
        + env_score * 0.32
        + activity_score * 0.15
        + exposure_score * 0.06
        + confidence_score * 0.05
    )
    overall_score = clamp(overall_score, 0.0, 1.0)
    overall_state = _status_from_score(overall_score)
    if physical_state := physiological.get("state"):
        if physical_state == "CRITICAL" or environmental.get("state") == "CRITICAL":
            overall_state = "CRITICAL"
        elif physical_state == "WARNING" or environmental.get("state") == "WARNING" or overall_score >= 0.45:
            overall_state = "WARNING"

    return {
        "overall_state": overall_state,
        "overall_score": round(overall_score, 4),
        "physiological": physiological,
        "environmental": environmental,
        "activity": activity_score,
        "exposure_minutes": exposure_minutes,
        "sensor_confidence": confidence_score,
    }


def run_bmssp_route(graph: dict[str, Any], start: str, target: str) -> dict[str, Any]:
    distances: dict[str, float] = {start: 0.0}
    previous: dict[str, str | None] = {start: None}
    queue: list[tuple[float, str]] = [(0.0, start)]
    visited: set[str] = set()

    while queue:
        queue.sort(key=lambda item: item[0])
        current_cost, node = queue.pop(0)
        if node in visited:
            continue
        visited.add(node)
        if node == target:
            break
        neighbors = graph.get(node, {})
        for neighbor, weight in neighbors.items():
            if isinstance(weight, dict):
                edge_cost = calculate_edge_cost(weight)
            else:
                edge_cost = float(weight)
            if edge_cost < 0:
                edge_cost = 0.0
            trial_cost = current_cost + edge_cost
            if trial_cost < distances.get(neighbor, math.inf):
                distances[neighbor] = trial_cost
                previous[neighbor] = node
                queue.append((trial_cost, neighbor))

    if target not in distances:
        raise HTTPException(status_code=404, detail=f"No route found from {start} to {target}")

    path = reconstruct_path(previous, start, target)
    return {"path": path, "total_cost": round(distances[target], 2), "prev": previous}


def reconstruct_path(previous: dict[str, str | None], start: str, target: str) -> list[str]:
    if target not in previous and target != start:
        return []
    path: list[str] = []
    current: str | None = target
    while current is not None:
        path.append(current)
        if current == start:
            break
        current = previous.get(current)
    return list(reversed(path))


def get_path_instructions(path: list[str], current_node: str | None = None) -> list[str]:
    if not path:
        return ["No safe route available. Hold position and request reassessment."]
    route = path
    if current_node is not None and route and route[0] != current_node:
        route = [current_node, *route]
    instructions: list[str] = []
    for index, node in enumerate(route[:-1]):
        next_node = route[index + 1]
        if node == current_node:
            instructions.append(f"Next: move from {node} to {next_node} and continue the evacuation route.")
        else:
            instructions.append(f"Next: proceed from {node} toward {next_node}.")
    if route[-1] == "EXIT" or route[-1].lower().startswith("exit"):
        instructions.append("Final: evacuate to the exit and maintain safe spacing.")
    else:
        instructions.append(f"Continue to {route[-1]} and maintain evacuation posture.")
    return instructions


def replan_route(graph: dict[str, Any], current_node: str, destination: str, edge_updates: dict[str, Any] | None = None) -> dict[str, Any]:
    updated_graph = copy.deepcopy(graph)
    edge_updates = edge_updates or {}
    for edge_key, payload in edge_updates.items():
        source, target = edge_key.split("->")
        if source in updated_graph and target in updated_graph[source]:
            if payload.get("blocked"):
                updated_graph[source][target] = math.inf
            elif isinstance(payload, dict):
                updated_graph[source][target] = payload
    return run_bmssp_route(updated_graph, current_node, destination)


def safe_serialize_worker(worker: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": worker.get("id"),
        "name": worker.get("name"),
        "location": worker.get("location"),
        "status": worker.get("status"),
        "hr": int(worker.get("hr", 0)),
        "spo2": int(worker.get("spo2", 0)),
        "o2": float(worker.get("o2", 20.9)),
        "ch4": float(worker.get("ch4", 0.0)),
        "co": float(worker.get("co", 0.0)),
        "co2": float(worker.get("co2", 0.0)),
        "temperature_c": float(worker.get("temperature_c", worker.get("temp_c", 36.8))),
        "activity": float(worker.get("activity", 0.0)),
        "pressure_atm": int(worker.get("pressure_atm", 0)),
        "battery_percent": int(worker.get("battery_percent", 0)),
        "signal_quality": int(worker.get("signal_quality", 0)),
        "trend": worker.get("trend", "Normal operation"),
    }


def build_default_graph() -> dict[str, dict[str, Any]]:
    return copy.deepcopy(DEFAULT_GRAPH)


def _connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    conn = _connect_db()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS workers (
                id INTEGER PRIMARY KEY,
                name TEXT,
                location TEXT,
                status TEXT,
                hr INTEGER,
                spo2 INTEGER,
                o2 REAL,
                ch4 REAL,
                co REAL,
                co2 REAL,
                temperature_c REAL,
                activity REAL,
                pressure_atm INTEGER,
                battery_percent INTEGER,
                signal_quality INTEGER,
                baseline_hr REAL,
                baseline_spo2 REAL,
                baseline_temp REAL,
                expected_hr REAL,
                trend TEXT,
                updated_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS sensor_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_id INTEGER,
                timestamp TEXT,
                hr INTEGER,
                spo2 INTEGER,
                o2 REAL,
                ch4 REAL,
                co REAL,
                co2 REAL,
                temperature_c REAL,
                activity REAL,
                status TEXT,
                sensor_confidence REAL,
                FOREIGN KEY(worker_id) REFERENCES workers(id)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_id INTEGER,
                level TEXT,
                title TEXT,
                message TEXT,
                action TEXT,
                created_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mine_graph_nodes (
                id TEXT PRIMARY KEY,
                label TEXT,
                x INTEGER,
                y INTEGER,
                kind TEXT,
                metadata TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS mine_graph_edges (
                id TEXT PRIMARY KEY,
                source TEXT,
                target TEXT,
                distance REAL,
                hazard REAL,
                gas REAL,
                oxygen REAL,
                thermal REAL,
                physiological REAL,
                blocked INTEGER,
                updated_at TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS routes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                worker_id INTEGER,
                path TEXT,
                cost REAL,
                created_at TEXT
            )
            """
        )

        worker_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(workers)").fetchall()
        }
        worker_schema = {
            "hr": "INTEGER",
            "spo2": "INTEGER",
            "o2": "REAL",
            "ch4": "REAL",
            "co": "REAL",
            "co2": "REAL",
            "temperature_c": "REAL",
            "activity": "REAL",
            "pressure_atm": "INTEGER",
            "battery_percent": "INTEGER",
            "signal_quality": "INTEGER",
            "baseline_hr": "REAL",
            "baseline_spo2": "REAL",
            "baseline_temp": "REAL",
            "expected_hr": "REAL",
            "trend": "TEXT",
            "updated_at": "TEXT",
        }
        for column_name, column_type in worker_schema.items():
            if column_name not in worker_columns:
                conn.execute(f"ALTER TABLE workers ADD COLUMN {column_name} {column_type}")

        conn.commit()
    finally:
        conn.close()


def seed_demo_data() -> None:
    conn = _connect_db()
    try:
        for worker in BASE_WORKERS:
            conn.execute(
                """
                INSERT OR REPLACE INTO workers (
                    id, name, location, status, hr, spo2, o2, ch4, co, co2,
                    temperature_c, activity, pressure_atm, battery_percent,
                    signal_quality, baseline_hr, baseline_spo2, baseline_temp,
                    expected_hr, trend, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """,
                (
                    worker["id"], worker["name"], worker["location"], worker["status"], worker["hr"], worker["spo2"], worker["o2"], worker["ch4"], worker["co"], worker["co2"],
                    worker["temperature_c"], worker["activity"], worker["pressure_atm"], worker["battery_percent"], worker["signal_quality"], worker["baseline_hr"], worker["baseline_spo2"], worker["baseline_temp"],
                    worker["expected_hr"], "Normal operation",
                ),
            )
        conn.commit()
    finally:
        conn.close()

    conn = _connect_db()
    try:
        for node_name, neighbors in DEFAULT_GRAPH.items():
            if node_name == "Exit B":
                continue
            conn.execute(
                "INSERT OR REPLACE INTO mine_graph_nodes (id, label, x, y, kind, metadata) VALUES (?, ?, ?, ?, ?, ?)",
                (node_name, node_name, 0, 0, "junction", json.dumps({"neighbors": list(neighbors.keys())})),
            )
        conn.execute(
            "INSERT OR REPLACE INTO mine_graph_nodes (id, label, x, y, kind, metadata) VALUES (?, ?, ?, ?, ?, ?)",
            ("Exit B", "Exit B", 0, 0, "exit", json.dumps({"pacing": "safe"})),
        )
        for source, neighbors in DEFAULT_GRAPH.items():
            for target, metrics in neighbors.items():
                edge_key = f"{source}->{target}"
                conn.execute(
                    "INSERT OR REPLACE INTO mine_graph_edges (id, source, target, distance, hazard, gas, oxygen, thermal, physiological, blocked, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))",
                    (
                        edge_key,
                        source,
                        target,
                        float(metrics.get("distance", 0.0)),
                        float(metrics.get("hazard", 0.0)),
                        float(metrics.get("gas", 0.0)),
                        float(metrics.get("oxygen", 0.0)),
                        float(metrics.get("thermal", 0.0)),
                        float(metrics.get("physiological", 0.0)),
                        0,
                    ),
                )
        conn.commit()
    finally:
        conn.close()


def read_workers_from_db() -> list[dict[str, Any]]:
    conn = _connect_db()
    try:
        rows = conn.execute("SELECT * FROM workers ORDER BY id").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def read_alerts_from_db() -> list[dict[str, Any]]:
    conn = _connect_db()
    try:
        rows = conn.execute("SELECT * FROM alerts ORDER BY created_at DESC LIMIT 20").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def read_history_from_db() -> list[dict[str, Any]]:
    conn = _connect_db()
    try:
        rows = conn.execute("SELECT * FROM sensor_history ORDER BY timestamp DESC LIMIT 50").fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


def read_graph_from_db() -> dict[str, dict[str, Any]]:
    conn = _connect_db()
    try:
        rows = conn.execute("SELECT source, target, distance, hazard, gas, oxygen, thermal, physiological, blocked FROM mine_graph_edges").fetchall()
    finally:
        conn.close()

    graph: dict[str, dict[str, Any]] = {}
    for row in rows:
        source = row["source"]
        target = row["target"]
        graph.setdefault(source, {})
        cost = {"distance": row["distance"], "hazard": row["hazard"], "gas": row["gas"], "oxygen": row["oxygen"], "thermal": row["thermal"], "physiological": row["physiological"]}
        if row["blocked"]:
            cost["blocked"] = True
        graph[source][target] = cost
    return graph


def generate_scenario_telemetry(scenario: str) -> dict[str, Any]:
    scenario_key = scenario.lower().strip()
    templates = {
        "normal worker": {"hr": 96, "spo2": 98, "o2": 20.8, "ch4": 0.12, "co": 12, "co2": 700, "temp_c": 36.8, "activity": 0.28},
        "high physiological strain": {"hr": 140, "spo2": 91, "o2": 20.3, "ch4": 0.2, "co": 20, "co2": 980, "temp_c": 38.8, "activity": 0.85},
        "methane increase": {"hr": 112, "spo2": 94, "o2": 20.0, "ch4": 1.8, "co": 25, "co2": 1300, "temp_c": 37.4, "activity": 0.55},
        "oxygen depletion": {"hr": 116, "spo2": 89, "o2": 17.5, "ch4": 0.4, "co": 18, "co2": 1250, "temp_c": 37.2, "activity": 0.52},
        "combined physiological + environmental emergency": {"hr": 165, "spo2": 83, "o2": 16.8, "ch4": 2.4, "co": 72, "co2": 3100, "temp_c": 41.2, "activity": 0.9},
        "hazard appearing on an existing evacuation route": {"hr": 118, "spo2": 92, "o2": 19.0, "ch4": 1.5, "co": 42, "co2": 2000, "temp_c": 39.1, "activity": 0.7},
    }
    base_metrics = templates.get(scenario_key, templates["normal worker"])
    workers = []
    for worker in BASE_WORKERS:
        worker_profile = dict(worker)
        worker_profile.update(base_metrics)
        worker_profile["status"] = assess_emergency_state(worker_profile)["status"]
        workers.append(safe_serialize_worker(worker_profile))
    return {"scenario": scenario, "workers": workers}


def simulate_worker_telemetry(base_metrics: dict[str, Any], scenario: str = "normal worker") -> dict[str, Any]:
    scenario_values = {
        "normal worker": {"hr": 1, "spo2": 0, "o2": 0.1, "ch4": 0.0, "co": 0, "co2": 0, "temp_c": 0.05, "activity": 0.0},
        "high physiological strain": {"hr": 22, "spo2": -4, "o2": -0.1, "ch4": 0.05, "co": 7, "co2": 120, "temp_c": 1.2, "activity": 0.42},
        "methane increase": {"hr": 8, "spo2": -2, "o2": -0.2, "ch4": 1.2, "co": 10, "co2": 500, "temp_c": 0.3, "activity": 0.12},
        "oxygen depletion": {"hr": 12, "spo2": -7, "o2": -2.7, "ch4": 0.1, "co": 5, "co2": 250, "temp_c": 0.1, "activity": 0.1},
        "combined physiological + environmental emergency": {"hr": 55, "spo2": -11, "o2": -3.1, "ch4": 1.9, "co": 45, "co2": 1800, "temp_c": 3.5, "activity": 0.54},
        "hazard appearing on an existing evacuation route": {"hr": 18, "spo2": -3, "o2": -1.0, "ch4": 1.4, "co": 30, "co2": 800, "temp_c": 2.2, "activity": 0.2},
    }
    delta = scenario_values.get(scenario.lower(), scenario_values["normal worker"])
    worker = dict(base_metrics)
    worker["hr"] = clamp_int(int(worker.get("hr", 95) + delta["hr"]), 70, 200)
    worker["spo2"] = clamp_int(int(worker.get("spo2", 98) + delta["spo2"]), 70, 100)
    worker["o2"] = float(clamp(worker.get("o2", 20.8) + delta["o2"], 16.0, 21.0))
    worker["ch4"] = float(clamp(worker.get("ch4", 0.1) + delta["ch4"], 0.0, 5.0))
    worker["co"] = float(clamp(worker.get("co", 10) + delta["co"], 0.0, 120.0))
    worker["co2"] = float(clamp(worker.get("co2", 700) + delta["co2"], 400.0, 5000.0))
    worker["temperature_c"] = float(clamp(worker.get("temperature_c", 36.8) + delta["temp_c"], 30.0, 45.0))
    worker["activity"] = float(clamp(worker.get("activity", 0.3) + delta["activity"], 0.0, 1.0))
    worker["status"] = assess_emergency_state(worker)["status"]
    return worker


@app.on_event("startup")
async def startup_event() -> None:
    init_db()
    seed_demo_data()


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "online", "timestamp": utcnow().isoformat()}


@app.get("/api/workers")
async def get_workers() -> list[dict[str, Any]]:
    workers = read_workers_from_db()
    if not workers:
        seed_demo_data()
        workers = read_workers_from_db()
    return [safe_serialize_worker(worker) for worker in workers]


@app.get("/api/alerts/active")
async def get_active_alerts() -> list[dict[str, Any]]:
    alerts = read_alerts_from_db()
    if not alerts:
        return [{"level": "info", "title": "System online", "message": "No active alerts. Monitoring stable.", "action": "Monitor"}]
    return alerts


@app.get("/api/mine/topology")
async def get_mine_topology() -> dict[str, Any]:
    graph = read_graph_from_db()
    if not graph:
        graph = build_default_graph()
    nodes = [{"id": node, "x": 0, "y": 0, "info": node} for node in sorted(graph.keys())]
    edges = []
    for source, neighbors in graph.items():
        for target in neighbors:
            edges.append([source, target])
    return {"nodes": nodes, "edges": edges, "graph": graph}


@app.get("/api/history")
async def get_history() -> list[dict[str, Any]]:
    return read_history_from_db()


@app.get("/api/risk/{worker_id}")
async def get_worker_risk(worker_id: int) -> dict[str, Any]:
    workers = read_workers_from_db()
    worker = next((item for item in workers if int(item["id"]) == worker_id), None)
    if worker is None:
        raise HTTPException(status_code=404, detail=f"Worker {worker_id} not found")
    phys = calculate_physiological_risk({
        "hr": worker["hr"],
        "spo2": worker["spo2"],
        "temperature_c": worker["temperature_c"],
        "activity": worker["activity"],
        "baseline_hr": worker["baseline_hr"],
        "baseline_spo2": worker["baseline_spo2"],
        "baseline_temp": worker["baseline_temp"],
        "expected_hr": worker["expected_hr"],
    })
    env = calculate_environmental_risk({
        "o2": worker["o2"],
        "ch4": worker["ch4"],
        "co": worker["co"],
        "co2": worker["co2"],
        "temperature_c": worker["temperature_c"],
        "relative_humidity": 0.58,
        "trends": {"o2": -0.4, "ch4": 0.2, "co": 6, "co2": 180, "temp": 0.5},
    })
    fused = compute_multimodal_worker_state(phys, env, float(worker["activity"]), 12, 0.88)
    return {"worker_id": worker_id, "physiological": phys, "environmental": env, "fusion": fused}


@app.post("/api/scenarios/replay")
async def replay_scenario(payload: dict[str, Any]) -> dict[str, Any]:
    scenario = str(payload.get("scenario") or "normal worker")
    data = generate_scenario_telemetry(scenario)
    return data


@app.post("/api/routes/replan")
async def replan_worker_route(payload: dict[str, Any]) -> dict[str, Any]:
    current_node = str(payload.get("current_node") or "T7")
    destination = str(payload.get("destination") or "Exit B")
    graph = read_graph_from_db() or build_default_graph()
    edge_updates = payload.get("edge_updates") or {}
    route = replan_route(graph, current_node, destination, edge_updates)
    return route


@app.websocket("/ws/dashboard")
async def dashboard_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    try:
        while True:
            workers = read_workers_from_db() or BASE_WORKERS
            telemetry = []
            for worker in workers:
                worker_copy = dict(worker)
                scenario_name = "normal worker"
                worker_copy.update(simulate_worker_telemetry(worker_copy, scenario_name))
                worker_copy["status"] = assess_emergency_state(worker_copy)["status"]
                worker_copy["trend"] = worker_copy["status"]
                telemetry.append(safe_serialize_worker(worker_copy))
            payload = {
                "type": "telemetry",
                "timestamp": utcnow().isoformat(),
                "workers": telemetry,
                "latency_ms": random.randint(240, 330),
            }
            await websocket.send_json(payload)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return


__all__ = [
    "REGULATORY_THRESHOLDS",
    "RESEARCH_THRESHOLDS",
    "BASE_WORKERS",
    "DEFAULT_GRAPH",
    "app",
    "assess_emergency_state",
    "calculate_edge_cost",
    "calculate_environmental_risk",
    "calculate_physiological_risk",
    "compute_multimodal_worker_state",
    "generate_scenario_telemetry",
    "get_path_instructions",
    "reconstruct_path",
    "replan_route",
    "run_bmssp_route",
    "simulate_worker_telemetry",
]
