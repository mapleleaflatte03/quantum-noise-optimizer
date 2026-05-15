"""Tests for noise_optimizer package."""
import sys
sys.path.insert(0, "src")

from noise_optimizer import NoiseProfiler, NoiseAwareOptimizer, Benchmark
from pyqpanda3 import core, quantum_info
import numpy as np


def test_profiler_detects_noisy_gate():
    """Profiler should detect that CNOT is noisier than CZ."""
    noise = core.NoiseModel()
    noise.add_all_qubit_quantum_error(core.depolarizing_error(0.10), core.GateType.CNOT)
    noise.add_all_qubit_quantum_error(core.depolarizing_error(0.01), core.GateType.CZ)

    profiler = NoiseProfiler(noise, shots=5000)
    profile = profiler.profile()

    assert profile.two_qubit_gates["CZ"].fidelity > profile.two_qubit_gates["CNOT"].fidelity
    print("PASS: test_profiler_detects_noisy_gate")


def test_optimizer_uses_cz_when_better():
    """Optimizer should prefer CZ decomposition when CZ is less noisy."""
    noise = core.NoiseModel()
    noise.add_all_qubit_quantum_error(core.depolarizing_error(0.10), core.GateType.CNOT)
    noise.add_all_qubit_quantum_error(core.depolarizing_error(0.005), core.GateType.CZ)
    noise.add_all_qubit_quantum_error(core.depolarizing_error(0.005), core.GateType.H)

    profiler = NoiseProfiler(noise, shots=5000)
    profile = profiler.profile()
    optimizer = NoiseAwareOptimizer(profile)

    assert optimizer._should_use_cz_decomp() is True
    print("PASS: test_optimizer_uses_cz_when_better")


def test_optimized_bell_state_higher_fidelity():
    """Optimized Bell state should have higher fidelity under asymmetric noise."""
    noise = core.NoiseModel()
    noise.add_all_qubit_quantum_error(core.depolarizing_error(0.15), core.GateType.CNOT)
    noise.add_all_qubit_quantum_error(core.depolarizing_error(0.01), core.GateType.CZ)
    noise.add_all_qubit_quantum_error(core.depolarizing_error(0.005), core.GateType.H)

    profiler = NoiseProfiler(noise, shots=5000)
    profile = profiler.profile()
    optimizer = NoiseAwareOptimizer(profile)

    # Baseline Bell
    baseline = core.QProg()
    baseline << core.H(0) << core.CNOT(0, 1) << core.measure([0, 1], [0, 1])
    m1 = core.CPUQVM()
    m1.run(baseline, shots=10000, model=noise)
    baseline_counts = m1.result().get_counts()

    # Optimized Bell
    opt_circuit = optimizer.build_bell_state()
    opt_prog = core.QProg()
    opt_prog << opt_circuit << core.measure([0, 1], [0, 1])
    m2 = core.CPUQVM()
    m2.run(opt_prog, shots=10000, model=noise)
    opt_counts = m2.result().get_counts()

    ideal = {"00": 0.5, "11": 0.5}
    baseline_fid = quantum_info.hellinger_fidelity(ideal, {k: v/10000 for k, v in baseline_counts.items()})
    opt_fid = quantum_info.hellinger_fidelity(ideal, {k: v/10000 for k, v in opt_counts.items()})

    assert opt_fid > baseline_fid, f"opt={opt_fid:.4f} should be > baseline={baseline_fid:.4f}"
    print(f"PASS: test_optimized_bell_state_higher_fidelity (baseline={baseline_fid:.4f}, opt={opt_fid:.4f})")


def test_benchmark_runs():
    """Benchmark should complete without errors."""
    bench = Benchmark(shots=1000)
    configs = [{"type": "depolarizing", "strength": 0.02, "asymmetric": True, "cnot_factor": 5}]
    results = bench.run_all(configs)
    assert len(results) == 3  # Bell + GHZ-3 + GHZ-5
    assert all(r.fidelity_baseline > 0 for r in results)
    print("PASS: test_benchmark_runs")


if __name__ == "__main__":
    test_profiler_detects_noisy_gate()
    test_optimizer_uses_cz_when_better()
    test_optimized_bell_state_higher_fidelity()
    test_benchmark_runs()
    print("\nAll tests passed!")
