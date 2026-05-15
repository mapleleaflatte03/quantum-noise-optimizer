"""Full pipeline: circuit passes + noise-aware substitution + readout mitigation + ZNE."""
import sys
sys.path.insert(0, "src")

from pyqpanda3 import core, quantum_info
from noise_optimizer import (
    NoiseProfiler, NoiseAwareOptimizer,
    optimize_circuit, circuit_stats,
    ReadoutMitigator, ZeroNoiseExtrapolator,
)
import numpy as np

print("=" * 70)
print("FULL OPTIMIZATION + MITIGATION PIPELINE")
print("=" * 70)

# === Setup: Realistic noise model (asymmetric: CNOT much noisier than CZ) ===
noise = core.NoiseModel()
noise.add_all_qubit_quantum_error(core.depolarizing_error(0.12), core.GateType.CNOT)
noise.add_all_qubit_quantum_error(core.depolarizing_error(0.02), core.GateType.CZ)
noise.add_all_qubit_quantum_error(core.depolarizing_error(0.008), core.GateType.H)
noise.add_all_qubit_quantum_error(core.depolarizing_error(0.003), core.GateType.RZ)
noise.add_all_qubit_quantum_error(core.depolarizing_error(0.003), core.GateType.RY)
# Readout errors (5-8% per qubit)
noise.add_read_out_error([[0.95, 0.05], [0.03, 0.97]], 0)
noise.add_read_out_error([[0.93, 0.07], [0.04, 0.96]], 1)
noise.add_read_out_error([[0.92, 0.08], [0.05, 0.95]], 2)

n_qubits = 3
ideal_dist = {"000": 0.5, "111": 0.5}

# === Step 1: Build a "messy" GHZ circuit (with redundancies) ===
raw_circuit = core.QProg()
raw_circuit << core.H(0) << core.H(0) << core.H(0)  # H·H·H = H (two cancel)
raw_circuit << core.RZ(0, 0.3) << core.RZ(0, -0.3)  # cancel to zero
raw_circuit << core.CNOT(0, 1) << core.CNOT(1, 2)

print("\n--- Step 1: Raw circuit ---")
print(f"Stats: {circuit_stats(raw_circuit)}")

# === Step 2: Circuit optimization passes ===
optimized = optimize_circuit(raw_circuit)
print("\n--- Step 2: After circuit passes ---")
print(f"Stats: {circuit_stats(optimized)}")
print(f"Gates removed: {circuit_stats(raw_circuit)['total_gates'] - circuit_stats(optimized)['total_gates']}")

# === Step 3: Noise-aware gate substitution ===
profiler = NoiseProfiler(noise, shots=5000)
profile = profiler.profile()
optimizer = NoiseAwareOptimizer(profile)
noise_aware_circuit = optimizer.build_ghz_state(n_qubits)
print("\n--- Step 3: Noise-aware substitution ---")
print(f"Uses CZ decomposition: {optimizer._should_use_cz_decomp()}")
print(f"Stats: {circuit_stats(noise_aware_circuit)}")

# === Step 4: Run all variants with noise ===
def run_with_noise(circuit, noise_model, n_q, shots=20000):
    prog = core.QProg()
    prog << circuit << core.measure(list(range(n_q)), list(range(n_q)))
    m = core.CPUQVM()
    m.run(prog, shots=shots, model=noise_model)
    return m.result().get_counts()

raw_counts = run_with_noise(raw_circuit, noise, n_qubits)
opt_counts = run_with_noise(optimized, noise, n_qubits)
noise_aware_counts = run_with_noise(noise_aware_circuit, noise, n_qubits)

# === Step 5: Readout mitigation ===
mitigator = ReadoutMitigator(n_qubits=n_qubits)
mitigator.calibrate(noise)
corrected_dist = mitigator.mitigate(noise_aware_counts)

# === Step 6: ZNE on the noise-aware circuit ===
zne = ZeroNoiseExtrapolator(scale_factors=[1.0, 1.5, 2.0], fit_method="linear")
zne_result = zne.mitigate_expectation(noise_aware_circuit, noise, n_qubits, shots=20000)

# === Results ===
def fidelity(counts_or_dist):
    if isinstance(list(counts_or_dist.values())[0], int):
        total = sum(counts_or_dist.values())
        dist = {k: v/total for k, v in counts_or_dist.items()}
    else:
        dist = counts_or_dist
    return quantum_info.hellinger_fidelity(ideal_dist, dist)

print("\n" + "=" * 70)
print("RESULTS")
print("=" * 70)
results = [
    ("1. Raw circuit + noise", fidelity(raw_counts)),
    ("2. After circuit passes + noise", fidelity(opt_counts)),
    ("3. Noise-aware substitution + noise", fidelity(noise_aware_counts)),
    ("4. + Readout mitigation", fidelity(corrected_dist)),
    ("5. + ZNE", fidelity(zne_result["extrapolated"])),
]

baseline = results[0][1]
for name, fid in results:
    improvement = ((fid - baseline) / baseline) * 100
    print(f"  {name}: fidelity={fid:.4f} ({improvement:+.1f}%)")

best_fid = max(r[1] for r in results)
print(f"\n  Best improvement (raw → best): {((best_fid - baseline) / baseline) * 100:+.1f}%")
