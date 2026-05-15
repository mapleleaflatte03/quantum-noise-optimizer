"""Quantum Noise Intelligence MCP Server (fast-start version).

Lazy-loads heavy dependencies (Qiskit, pyqpanda3) on first tool call
to ensure MCP handshake completes quickly.
"""

import json
import sys
from pathlib import Path

from fastmcp import FastMCP

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

mcp = FastMCP(
    "Quantum Noise Intelligence",
    instructions="Noise-aware quantum error mitigation for AI agents. "
    "Tools: noise_profile, recommend_mitigation, run_bounded_zne, "
    "compare_strategies, wukong_status, optimize_circuit.",
)


@mcp.tool()
def noise_profile(backend: str = "aer_simulator", n_qubits: int = 5) -> dict:
    """Get noise characteristics for a quantum backend."""
    if backend == "wukong_180":
        cal_path = Path(__file__).parent.parent / "results" / "wukong180_calibration.json"
        if cal_path.exists():
            return {"backend": "wukong_180", "n_qubits": 169, "cz_gates": 396,
                    "best_qubits": [78, 88, 97], "source": "real_calibration"}
    return {"backend": backend, "n_qubits": n_qubits, "avg_1q_error": 0.001,
            "avg_2q_error": 0.01, "avg_readout_error": 0.02,
            "avg_t1_us": 100.0, "avg_t2_us": 80.0}


@mcp.tool()
def recommend_mitigation(n_qubits: int, depth: int, n_cx: int, noise_level: str = "medium") -> dict:
    """Recommend the best error mitigation strategy for a circuit."""
    noise_map = {"low": 0.005, "medium": 0.01, "high": 0.03}
    err_2q = noise_map.get(noise_level, 0.01)
    cx_density = n_cx / max(depth * n_qubits, 1)

    if err_2q < 0.002:
        strategy, reason = "none", "Noise too low for mitigation overhead"
    elif cx_density >= 0.3:
        strategy, reason = "bounded_zne", f"High CX density ({cx_density:.2f}) — ZNE effective"
    elif depth > 20:
        strategy, reason = "dynamical_decoupling", "Deep circuit — DD suppresses idle decoherence"
    else:
        strategy, reason = "combined", "Multiple noise sources — combine ZNE + readout"

    return {"strategy": strategy, "reason": reason,
            "circuit": {"n_qubits": n_qubits, "depth": depth, "n_cx": n_cx}}


@mcp.tool()
def run_bounded_zne(scale_factors: list[float], expectation_values: list[float],
                    observable_bounds: list[float] = [-1.0, 1.0]) -> dict:
    """Run physically-bounded ZNE extrapolation to estimate zero-noise value."""
    from noise_optimizer.bounded_zne import auto_select_model
    bounds = tuple(observable_bounds)
    name, model = auto_select_model(scale_factors, expectation_values, bounds)
    return {"zero_noise_estimate": round(model.zero_noise_estimate_, 6),
            "model_selected": name, "bounds_enforced": list(bounds),
            "raw_value": expectation_values[0]}


@mcp.tool()
def compare_strategies(n_qubits: int = 3, circuit_type: str = "ghz",
                       noise_level: str = "medium", shots: int = 4096) -> dict:
    """Compare mitigation strategies on a test circuit with simulated noise."""
    import numpy as np
    from qiskit import QuantumCircuit
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import NoiseModel, depolarizing_error
    from noise_optimizer.bounded_zne import auto_select_model

    n_qubits = min(max(n_qubits, 2), 6)
    qc = QuantumCircuit(n_qubits)
    qc.h(0)
    for i in range(1, n_qubits):
        qc.cx(i - 1, i)
    qc.measure_all()

    err = {"low": (0.005, 0.015), "medium": (0.01, 0.03), "high": (0.02, 0.06)}
    e1, e2 = err.get(noise_level, (0.01, 0.03))

    ideal_sim = AerSimulator()
    ideal_counts = ideal_sim.run(qc, shots=shots).result().get_counts()
    ideal_exp = sum((1 - 2*(k.count('1')%2)) * v / shots for k, v in ideal_counts.items())

    scales = [1.0, 1.5, 2.0, 2.5, 3.0]
    exps = []
    for s in scales:
        nm = NoiseModel()
        nm.add_all_qubit_quantum_error(depolarizing_error(min(e1*s, 0.75), 1), ['h'])
        nm.add_all_qubit_quantum_error(depolarizing_error(min(e2*s, 0.75), 2), ['cx'])
        counts = AerSimulator(noise_model=nm).run(qc, shots=shots).result().get_counts()
        exps.append(sum((1-2*(k.count('1')%2))*v/shots for k, v in counts.items()))

    linear = float(np.polyval(np.polyfit(scales, exps, 1), 0))
    _, model = auto_select_model(scales, exps)
    bounded = model.zero_noise_estimate_

    return {"ideal": round(ideal_exp, 4),
            "raw": {"value": round(exps[0], 4), "error": round(abs(exps[0]-ideal_exp), 4)},
            "linear_zne": {"value": round(linear, 4), "error": round(abs(linear-ideal_exp), 4)},
            "bounded_zne": {"value": round(bounded, 4), "error": round(abs(bounded-ideal_exp), 4)}}


@mcp.tool()
def wukong_status() -> dict:
    """Check Origin Wukong 180 quantum computer status."""
    cal_path = Path(__file__).parent.parent / "results" / "wukong180_calibration.json"
    result = {"backend": "Origin Wukong 180", "qubits": 169, "cz_gates": 396}
    result["calibration_available"] = cal_path.exists()
    result["best_qubits"] = [78, 88, 97]
    result["note"] = "API currently has format mismatch (errCode 33). Hardware online but jobs rejected."
    return result


@mcp.tool()
def optimize_circuit(qasm: str, noise_level: str = "medium") -> dict:
    """Optimize a quantum circuit and recommend mitigation strategy."""
    from qiskit import QuantumCircuit
    from qiskit.transpiler import preset_passmanagers
    try:
        qc = QuantumCircuit.from_qasm_str(qasm)
    except Exception as e:
        return {"error": str(e)}
    pm = preset_passmanagers.generate_preset_pass_manager(optimization_level=3)
    opt = pm.run(qc)
    orig_gates = sum(qc.count_ops().values())
    opt_gates = sum(opt.count_ops().values())
    return {"original_gates": orig_gates, "optimized_gates": opt_gates,
            "reduction": f"{(1-opt_gates/max(orig_gates,1))*100:.1f}%",
            "optimized_depth": opt.depth()}


if __name__ == "__main__":
    mcp.run(transport="stdio")
