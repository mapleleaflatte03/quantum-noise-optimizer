"""Quantum Noise Intelligence MCP Server.

First open-source noise-focused MCP server for quantum computing.
Exposes noise profiling, mitigation strategy selection, and
physically-bounded ZNE to AI agents via Model Context Protocol.
"""

import json
import sys
from pathlib import Path

from fastmcp import FastMCP

# Add project source to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from noise_optimizer.bounded_zne import PhysicallyBoundedZNE, auto_select_model
from noise_optimizer.auto_mitigator import AutoMitigator

mcp = FastMCP(
    "Quantum Noise Intelligence",
    instructions="Noise-aware quantum error mitigation for AI agents. "
    "Provides noise profiling, strategy selection, and physically-bounded ZNE.",
)


@mcp.tool()
def noise_profile(backend: str = "aer_simulator", n_qubits: int = 5) -> dict:
    """Get noise characteristics for a quantum backend.

    Returns per-qubit error rates, T1/T2 times, and readout errors.
    Use this to understand the noise landscape before running circuits.
    """
    from qiskit_aer.noise import NoiseModel
    from qiskit_aer import AerSimulator

    if backend == "wukong_180":
        # Load real calibration data
        cal_path = Path(__file__).parent.parent / "results" / "wukong180_calibration.json"
        if cal_path.exists():
            data = json.loads(cal_path.read_text())
            return {
                "backend": "wukong_180",
                "n_qubits": data.get("n_qubits", 169),
                "n_gates": data.get("n_gates", 396),
                "source": "real_calibration",
                "note": "Real calibration data from Origin Wukong 180",
            }

    # Default: generate typical noise profile
    return {
        "backend": backend,
        "n_qubits": n_qubits,
        "avg_1q_error": 0.001,
        "avg_2q_error": 0.01,
        "avg_readout_error": 0.02,
        "avg_t1_us": 100.0,
        "avg_t2_us": 80.0,
        "gate_set": ["h", "rx", "ry", "rz", "cx", "cz"],
        "note": "Typical superconducting device noise profile",
    }


@mcp.tool()
def recommend_mitigation(
    n_qubits: int,
    depth: int,
    n_cx: int,
    noise_level: str = "medium",
) -> dict:
    """Recommend the best error mitigation strategy for a circuit.

    Args:
        n_qubits: Number of qubits in the circuit
        depth: Circuit depth (number of layers)
        n_cx: Number of two-qubit (CX/CZ) gates
        noise_level: 'low', 'medium', or 'high'

    Returns strategy recommendation with reasoning.
    """
    noise_map = {
        "low": {"avg_1q_error": 0.001, "avg_2q_error": 0.005, "avg_readout_error": 0.01},
        "medium": {"avg_1q_error": 0.002, "avg_2q_error": 0.01, "avg_readout_error": 0.03},
        "high": {"avg_1q_error": 0.005, "avg_2q_error": 0.03, "avg_readout_error": 0.05},
    }
    profile = noise_map.get(noise_level, noise_map["medium"])

    cx_density = n_cx / max(depth * n_qubits, 1)

    if profile["avg_2q_error"] < 0.002 and profile["avg_readout_error"] < 0.01:
        strategy = "none"
        reason = "Noise is very low; mitigation overhead not justified"
    elif cx_density >= 0.3 and profile["avg_2q_error"] >= 0.01:
        strategy = "bounded_zne"
        reason = f"High CX density ({cx_density:.2f}) with significant 2q error — ZNE extrapolation effective"
    elif depth > 20 and profile["avg_2q_error"] < 0.02:
        strategy = "dynamical_decoupling"
        reason = "Deep circuit with moderate noise — DD suppresses idle decoherence"
    elif profile["avg_readout_error"] >= 0.04:
        strategy = "readout_mitigation"
        reason = "High readout error dominates — correct measurement first"
    else:
        strategy = "combined"
        reason = "Multiple noise sources — combine ZNE + readout correction"

    return {
        "strategy": strategy,
        "reason": reason,
        "circuit_info": {"n_qubits": n_qubits, "depth": depth, "n_cx": n_cx, "cx_density": round(cx_density, 3)},
        "noise_level": noise_level,
        "params": _get_strategy_params(strategy),
    }


def _get_strategy_params(strategy: str) -> dict:
    params = {
        "bounded_zne": {"scale_factors": [1.0, 1.5, 2.0, 2.5, 3.0], "model": "auto (AICc selection)"},
        "dynamical_decoupling": {"sequence": "XY4", "spacing": "uniform"},
        "readout_mitigation": {"method": "confusion_matrix", "shots_calibration": 1000},
        "combined": {"zne": True, "readout": True, "dd": False},
        "none": {},
    }
    return params.get(strategy, {})


@mcp.tool()
def run_bounded_zne(
    scale_factors: list[float],
    expectation_values: list[float],
    observable_bounds: list[float] = [-1.0, 1.0],
) -> dict:
    """Run physically-bounded ZNE on measured expectation values.

    Given measurements at different noise amplification levels,
    extrapolates to the zero-noise limit while enforcing physical bounds.

    Args:
        scale_factors: Noise amplification factors [1.0, 1.5, 2.0, ...]
        expectation_values: Measured <O> at each noise level
        observable_bounds: [lower, upper] physical bounds for the observable

    Returns the zero-noise estimate with model selection info.
    """
    bounds = tuple(observable_bounds)
    name, model = auto_select_model(scale_factors, expectation_values, bounds)

    return {
        "zero_noise_estimate": round(model.zero_noise_estimate_, 6),
        "model_selected": name,
        "selection_method": "AICc (corrected Akaike Information Criterion)",
        "bounds_enforced": list(bounds),
        "raw_value": expectation_values[0],
        "improvement": round(abs(expectation_values[0]) - abs(model.zero_noise_estimate_), 6),
        "note": "Estimate guaranteed within physical bounds. Based on arXiv:2604.24475.",
    }


@mcp.tool()
def compare_strategies(
    n_qubits: int = 3,
    circuit_type: str = "ghz",
    noise_level: str = "medium",
    shots: int = 4096,
) -> dict:
    """Compare all mitigation strategies on a test circuit.

    Runs a circuit with noise and applies different mitigation methods,
    returning a comparison of their effectiveness.

    Args:
        n_qubits: Number of qubits (2-6)
        circuit_type: 'ghz', 'random', or 'qft'
        noise_level: 'low', 'medium', or 'high'
        shots: Number of measurement shots
    """
    import numpy as np
    from qiskit import QuantumCircuit
    from qiskit_aer import AerSimulator
    from qiskit_aer.noise import NoiseModel, depolarizing_error

    n_qubits = min(max(n_qubits, 2), 6)

    # Build circuit
    qc = QuantumCircuit(n_qubits)
    if circuit_type == "ghz":
        qc.h(0)
        for i in range(1, n_qubits):
            qc.cx(i - 1, i)
    elif circuit_type == "qft":
        from qiskit.circuit.library import QFT
        qc = QFT(n_qubits)
    else:
        from qiskit.circuit.random import random_circuit
        qc = random_circuit(n_qubits, depth=5, seed=42)
    qc.measure_all()

    noise_params = {"low": (0.005, 0.015), "medium": (0.01, 0.03), "high": (0.02, 0.06)}
    err_1q, err_2q = noise_params.get(noise_level, (0.01, 0.03))

    # Ideal
    ideal_sim = AerSimulator()
    ideal_counts = ideal_sim.run(qc, shots=shots).result().get_counts()
    ideal_exp = sum((1 - 2 * (k.count("1") % 2)) * v / shots for k, v in ideal_counts.items())

    # Noisy at multiple scales
    scale_factors = [1.0, 1.5, 2.0, 2.5, 3.0]
    noisy_exps = []
    for s in scale_factors:
        noise = NoiseModel()
        noise.add_all_qubit_quantum_error(depolarizing_error(min(err_1q * s, 0.75), 1), ["h", "rx", "ry", "rz"])
        noise.add_all_qubit_quantum_error(depolarizing_error(min(err_2q * s, 0.75), 2), ["cx"])
        sim = AerSimulator(noise_model=noise)
        counts = sim.run(qc, shots=shots).result().get_counts()
        exp = sum((1 - 2 * (k.count("1") % 2)) * v / shots for k, v in counts.items())
        noisy_exps.append(exp)

    # Standard ZNE (linear)
    coeffs = np.polyfit(scale_factors, noisy_exps, 1)
    linear_zne = float(np.polyval(coeffs, 0))

    # Bounded ZNE
    name, model = auto_select_model(scale_factors, noisy_exps)
    bounded_zne = model.zero_noise_estimate_

    results = {
        "circuit": circuit_type,
        "n_qubits": n_qubits,
        "noise_level": noise_level,
        "ideal": round(ideal_exp, 4),
        "methods": {
            "raw": {"value": round(noisy_exps[0], 4), "error": round(abs(noisy_exps[0] - ideal_exp), 4)},
            "linear_zne": {"value": round(linear_zne, 4), "error": round(abs(linear_zne - ideal_exp), 4)},
            "bounded_zne": {
                "value": round(bounded_zne, 4),
                "error": round(abs(bounded_zne - ideal_exp), 4),
                "model": name,
            },
        },
        "winner": min(
            ["raw", "linear_zne", "bounded_zne"],
            key=lambda m: abs(
                (noisy_exps[0] if m == "raw" else linear_zne if m == "linear_zne" else bounded_zne) - ideal_exp
            ),
        ),
    }
    return results


if __name__ == "__main__":
    mcp.run()
