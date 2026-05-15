"""Physics Visualization: Noise propagation, fidelity decay, and circuit analysis plots.

Generates text-based and matplotlib visualizations showing how noise
affects quantum circuits from a physics perspective.
"""

from pyqpanda3 import core, quantum_info
import numpy as np


def noise_heatmap(prog: core.QProg, noise_model: core.NoiseModel,
                  n_qubits: int, shots: int = 10000) -> dict:
    """Compute per-layer fidelity to show noise accumulation through the circuit.

    Returns a dict with layer-by-layer fidelity data showing how
    noise degrades the quantum state as circuit depth increases.
    """
    ops = prog.operations()
    if not ops:
        return {"layers": [], "fidelities": []}

    layers = []
    fidelities = []
    qubits = list(range(n_qubits))

    # Build circuit incrementally, measure fidelity at each step
    partial = core.QProg()
    for i, op in enumerate(ops):
        partial << op

        # Every few gates, measure fidelity
        if (i + 1) % max(1, len(ops) // 10) == 0 or i == len(ops) - 1:
            # Noisy run
            test_prog = core.QProg()
            test_prog << partial << core.measure(qubits, qubits)
            m_noisy = core.CPUQVM()
            m_noisy.run(test_prog, shots=shots, model=noise_model)
            noisy_counts = m_noisy.result().get_counts()

            # Ideal run
            m_ideal = core.CPUQVM()
            m_ideal.run(test_prog, shots=shots)
            ideal_counts = m_ideal.result().get_counts()

            total_n = sum(noisy_counts.values())
            total_i = sum(ideal_counts.values())
            noisy_dist = {k: v / total_n for k, v in noisy_counts.items()}
            ideal_dist = {k: v / total_i for k, v in ideal_counts.items()}

            fid = quantum_info.hellinger_fidelity(ideal_dist, noisy_dist)
            layers.append(i + 1)
            fidelities.append(fid)

    return {"layers": layers, "fidelities": fidelities}


def fidelity_vs_depth(n_qubits: int, max_depth: int, noise_model: core.NoiseModel,
                      gate_type: str = "CNOT", shots: int = 5000) -> dict:
    """Show how fidelity decays with circuit depth — demonstrates T2-like behavior.

    Physics insight: Fidelity decays approximately exponentially with depth,
    analogous to T2 decay in NMR/quantum systems.
    """
    depths = list(range(1, max_depth + 1))
    fidelities = []

    for d in depths:
        # Build a chain of gates
        prog = core.QProg()
        prog << core.H(0)
        for layer in range(d):
            for q in range(n_qubits - 1):
                prog << core.CNOT(q, q + 1)

        prog << core.measure(list(range(n_qubits)), list(range(n_qubits)))

        # Noisy
        m1 = core.CPUQVM()
        m1.run(prog, shots=shots, model=noise_model)
        noisy = m1.result().get_counts()

        # Ideal
        m2 = core.CPUQVM()
        m2.run(prog, shots=shots)
        ideal = m2.result().get_counts()

        total_n = sum(noisy.values())
        total_i = sum(ideal.values())
        fid = quantum_info.hellinger_fidelity(
            {k: v / total_i for k, v in ideal.items()},
            {k: v / total_n for k, v in noisy.items()},
        )
        fidelities.append(fid)

    # Fit exponential decay: F ≈ exp(-d/T2_eff)
    log_fid = [np.log(f) if f > 0 else -10 for f in fidelities]
    try:
        coeffs = np.polyfit(depths, log_fid, 1)
        t2_eff = -1.0 / coeffs[0] if coeffs[0] != 0 else float('inf')
    except (np.linalg.LinAlgError, ValueError):
        t2_eff = float('inf')

    return {
        "depths": depths,
        "fidelities": fidelities,
        "t2_effective": t2_eff,
        "decay_rate": -1.0 / t2_eff if t2_eff != float('inf') else 0,
    }


def print_noise_report(prog: core.QProg, noise_model: core.NoiseModel, n_qubits: int):
    """Print a text-based noise analysis report."""
    from .circuit_passes import circuit_stats
    from .noise_profiler import NoiseProfiler

    stats = circuit_stats(prog)
    profiler = NoiseProfiler(noise_model, shots=3000)
    profile = profiler.profile()

    print("=" * 60)
    print("NOISE ANALYSIS REPORT")
    print("=" * 60)
    print(f"\nCircuit: {stats['total_gates']} gates, depth={stats['depth']}, {n_qubits} qubits")
    print(f"Gate breakdown: {stats['gate_counts']}")

    print("\n--- Per-Gate Error Rates ---")
    for name, p in sorted(profile.single_qubit_gates.items(), key=lambda x: -x[1].error_rate):
        if p.error_rate > 0.001:
            print(f"  {name:6s}: error={p.error_rate:.4f} (fidelity={p.fidelity:.4f})")
    for name, p in sorted(profile.two_qubit_gates.items(), key=lambda x: -x[1].error_rate):
        if p.error_rate > 0.001:
            print(f"  {name:6s}: error={p.error_rate:.4f} (fidelity={p.fidelity:.4f})")

    # Estimate total circuit error (multiplicative model)
    total_fidelity = 1.0
    for name, count in stats['gate_counts'].items():
        gate_fid = 1.0
        if name in profile.single_qubit_gates:
            gate_fid = profile.single_qubit_gates[name].fidelity
        elif name in profile.two_qubit_gates:
            gate_fid = profile.two_qubit_gates[name].fidelity
        total_fidelity *= gate_fid ** count

    print(f"\n--- Estimated Circuit Fidelity ---")
    print(f"  Multiplicative estimate: {total_fidelity:.4f}")
    print(f"  (Assumes independent errors — actual may differ)")

    # Fidelity decay
    heatmap = noise_heatmap(prog, noise_model, n_qubits, shots=3000)
    if heatmap["fidelities"]:
        print(f"\n--- Fidelity Decay Through Circuit ---")
        for layer, fid in zip(heatmap["layers"], heatmap["fidelities"]):
            bar = "█" * int(fid * 40)
            print(f"  Gate {layer:3d}: {fid:.4f} |{bar}")

    print("\n" + "=" * 60)
