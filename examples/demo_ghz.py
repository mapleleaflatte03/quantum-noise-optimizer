"""Example: Demonstrate noise-aware optimization on a 5-qubit GHZ state."""
import sys
sys.path.insert(0, "src")

from pyqpanda3 import core, quantum_info
from noise_optimizer import NoiseProfiler, NoiseAwareOptimizer

# Simulate realistic hardware: CNOT is 5x noisier than CZ
noise = core.NoiseModel()
noise.add_all_qubit_quantum_error(core.depolarizing_error(0.10), core.GateType.CNOT)
noise.add_all_qubit_quantum_error(core.depolarizing_error(0.02), core.GateType.CZ)
noise.add_all_qubit_quantum_error(core.depolarizing_error(0.005), core.GateType.H)
noise.add_all_qubit_quantum_error(core.depolarizing_error(0.003), core.GateType.RY)
noise.add_all_qubit_quantum_error(core.depolarizing_error(0.003), core.GateType.RZ)

# Step 1: Profile
profiler = NoiseProfiler(noise, shots=5000)
profile = profiler.profile()
print("=== Noise Profile ===")
print(f"CNOT fidelity: {profile.two_qubit_gates['CNOT'].fidelity:.4f}")
print(f"CZ fidelity:   {profile.two_qubit_gates['CZ'].fidelity:.4f}")
print(f"H fidelity:    {profile.single_qubit_gates['H'].fidelity:.4f}")

# Step 2: Optimize
optimizer = NoiseAwareOptimizer(profile)
print(f"\nOptimizer decision: use CZ decomp = {optimizer._should_use_cz_decomp()}")

# Step 3: Compare
n_qubits = 5
ideal_dist = {"00000": 0.5, "11111": 0.5}

# Baseline
baseline = core.QProg()
baseline << core.H(0)
for i in range(1, n_qubits):
    baseline << core.CNOT(i-1, i)
baseline << core.measure(list(range(n_qubits)), list(range(n_qubits)))

m1 = core.CPUQVM()
m1.run(baseline, shots=10000, model=noise)
baseline_counts = m1.result().get_counts()
baseline_fid = quantum_info.hellinger_fidelity(ideal_dist, {k: v/10000 for k, v in baseline_counts.items()})

# Optimized
opt_circuit = optimizer.build_ghz_state(n_qubits)
opt_prog = core.QProg()
opt_prog << opt_circuit << core.measure(list(range(n_qubits)), list(range(n_qubits)))

m2 = core.CPUQVM()
m2.run(opt_prog, shots=10000, model=noise)
opt_counts = m2.result().get_counts()
opt_fid = quantum_info.hellinger_fidelity(ideal_dist, {k: v/10000 for k, v in opt_counts.items()})

print(f"\n=== Results (5-qubit GHZ) ===")
print(f"Baseline fidelity:  {baseline_fid:.4f}")
print(f"Optimized fidelity: {opt_fid:.4f}")
print(f"Improvement:        {((opt_fid - baseline_fid) / baseline_fid) * 100:+.1f}%")
