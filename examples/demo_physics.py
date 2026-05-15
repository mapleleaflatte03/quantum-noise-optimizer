"""Demo: Physics visualization + Dynamical Decoupling analysis."""
import sys
sys.path.insert(0, "src")

from pyqpanda3 import core
from noise_optimizer import (
    insert_dd, estimate_dd_benefit,
    fidelity_vs_depth, print_noise_report,
    optimize_circuit, circuit_stats,
)

# Realistic noise: CNOT dominant error source
noise = core.NoiseModel()
noise.add_all_qubit_quantum_error(core.depolarizing_error(0.04), core.GateType.CNOT)
noise.add_all_qubit_quantum_error(core.depolarizing_error(0.01), core.GateType.H)
noise.add_all_qubit_quantum_error(core.depolarizing_error(0.005), core.GateType.X)
noise.add_all_qubit_quantum_error(core.depolarizing_error(0.005), core.GateType.Y)
noise.add_all_qubit_quantum_error(core.depolarizing_error(0.003), core.GateType.RZ)

# === 1. Noise Report on a 4-qubit GHZ ===
prog = core.QProg()
prog << core.H(0) << core.CNOT(0, 1) << core.CNOT(1, 2) << core.CNOT(2, 3)
print_noise_report(prog, noise, n_qubits=4)

# === 2. Fidelity vs Depth (T2 decay curve) ===
print("\n=== FIDELITY vs DEPTH (T2 decay) ===")
decay = fidelity_vs_depth(4, max_depth=12, noise_model=noise, shots=5000)
print(f"Effective T2: {decay['t2_effective']:.1f} gate layers")
print(f"Decay rate:   {decay['decay_rate']:.4f} per layer\n")
for d, f in zip(decay["depths"], decay["fidelities"]):
    bar = "█" * int(f * 50)
    print(f"  depth={d:2d}: {f:.4f} |{bar}")

# === 3. Dynamical Decoupling comparison ===
print("\n=== DYNAMICAL DECOUPLING ===")
print("Circuit: H(0) → CNOT(0,1) → CNOT(1,2) → CNOT(2,3)")
print(f"Original gates: {circuit_stats(prog)['total_gates']}")

dd_prog = insert_dd(prog, "XY4")
print(f"With XY4 DD:    {circuit_stats(dd_prog)['total_gates']} gates")

dd_result = estimate_dd_benefit(prog, noise, n_qubits=4, sequence="XY4", shots=10000)
print(f"\nFidelity without DD: {dd_result['without_dd']:.4f}")
print(f"Fidelity with DD:    {dd_result['with_dd']:.4f}")
print(f"DD effect:           {dd_result['improvement_pct']:+.2f}%")
print("\n(Note: DD helps most against dephasing/T2 noise on real hardware.")
print(" On depolarizing simulator, DD adds gates = more noise channels.)")
