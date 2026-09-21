import pytest

from src.backend.main import (
    assess_emergency_state,
    calculate_edge_cost,
    calculate_environmental_risk,
    calculate_physiological_risk,
    compute_multimodal_worker_state,
    generate_scenario_telemetry,
    get_path_instructions,
    reconstruct_path,
    run_bmssp_route,
    simulate_worker_telemetry,
)


@pytest.mark.parametrize(
    "values, expected",
    [
        ({"hr": 38, "spo2": 96, "o2": 20.9, "ch4": 0.1, "co": 10, "co2": 500, "temp_c": 36.8, "activity": 0.2}, "NORMAL"),
        ({"hr": 120, "spo2": 90, "o2": 19.3, "ch4": 0.8, "co": 40, "co2": 1500, "temp_c": 38.5, "activity": 0.8}, "WARNING"),
        ({"hr": 170, "spo2": 82, "o2": 16.5, "ch4": 2.5, "co": 90, "co2": 3500, "temp_c": 41.5, "activity": 1.0}, "CRITICAL"),
    ],
)
def test_emergency_threshold_detection(values, expected):
    state = assess_emergency_state(values)
    assert state["status"] == expected


def test_rate_of_change_detection():
    history = [
        {"hr": 90, "spo2": 97, "o2": 20.8, "ch4": 0.1, "co": 12, "co2": 500, "temp_c": 36.7, "activity": 0.3},
        {"hr": 100, "spo2": 95, "o2": 20.4, "ch4": 0.25, "co": 18, "co2": 600, "temp_c": 37.0, "activity": 0.35},
        {"hr": 116, "spo2": 92, "o2": 19.8, "ch4": 0.5, "co": 28, "co2": 900, "temp_c": 38.0, "activity": 0.55},
    ]
    state = assess_emergency_state({"hr": 118, "spo2": 91, "o2": 19.5, "ch4": 0.7, "co": 32, "co2": 1100, "temp_c": 38.5, "activity": 0.7}, history=history)
    assert state["status"] in {"WARNING", "CRITICAL"}
    assert state["rate_of_change"]["hr_delta"] > 0


def test_physiological_risk_and_baseline():
    risk = calculate_physiological_risk({
        "hr": 146,
        "spo2": 88,
        "temperature_c": 39.2,
        "activity": 0.9,
        "baseline_hr": 96,
        "baseline_spo2": 98,
        "baseline_temp": 36.8,
        "expected_hr": 104,
    })
    assert risk["state"] in {"WARNING", "CRITICAL"}
    assert risk["delta_hr"] > 0


def test_environmental_risk():
    risk = calculate_environmental_risk({
        "o2": 17.6,
        "ch4": 2.1,
        "co": 80,
        "co2": 4200,
        "temperature_c": 40.5,
        "relative_humidity": 0.68,
        "trends": {"o2": -1.2, "ch4": 1.2, "co": 20, "co2": 700, "temp": 1.9},
    })
    assert risk["state"] in {"WARNING", "CRITICAL"}
    assert risk["score"] > 0.4


def test_multimodal_fusion():
    fused = compute_multimodal_worker_state(
        physiological={"state": "CRITICAL", "score": 0.92},
        environmental={"state": "WARNING", "score": 0.75},
        activity=0.8,
        exposure_minutes=19,
        sensor_confidence=0.84,
    )
    assert fused["overall_state"] in {"WARNING", "CRITICAL"}
    assert fused["overall_score"] >= 0.6


def test_graph_edge_cost_and_blocking():
    cost = calculate_edge_cost({
        "distance": 120,
        "hazard": 0.4,
        "gas": 0.7,
        "oxygen": 0.3,
        "thermal": 0.5,
        "physiological": 0.2,
    })
    assert cost > 0
    assert cost == pytest.approx(120 * 0.35 + 0.4 * 25 + 0.7 * 30 + 0.3 * 18 + 0.5 * 20 + 0.2 * 10, rel=1e-6)


def test_bmssp_route_and_reconstruction():
    graph = {
        "A": {"B": 4, "C": 2},
        "B": {"D": 5},
        "C": {"D": 1},
        "D": {"EXIT": 2},
        "EXIT": {},
    }
    route = run_bmssp_route(graph, "A", "EXIT")
    assert route["path"] == ["A", "C", "D", "EXIT"]
    assert route["total_cost"] >= 5
    assert reconstruct_path(route["prev"], "A", "EXIT") == ["A", "C", "D", "EXIT"]


def test_dynamic_replanning_and_instructions():
    graph = {
        "A": {"B": 2, "C": 3},
        "B": {"E": 3},
        "C": {"E": 1},
        "E": {"EXIT": 2},
        "EXIT": {},
    }
    route = run_bmssp_route(graph, "E", "EXIT")
    instructions = get_path_instructions(route["path"], current_node="E")
    assert route["path"][0] == "E"
    assert "next" in instructions[0].lower()


def test_simulator_generates_realistic_scenario():
    data = generate_scenario_telemetry("combined physiological + environmental emergency")
    assert "workers" in data
    assert data["workers"]
    assert data["scenario"]


def test_simulated_worker_telemetry_changes():
    worker = simulate_worker_telemetry({"hr": 98, "spo2": 97, "o2": 20.8, "ch4": 0.15, "co": 10, "co2": 650, "temp_c": 36.8, "activity": 0.3}, scenario="normal worker")
    assert worker["hr"] >= 90
    assert worker["status"] in {"NORMAL", "WARNING", "CRITICAL"}
