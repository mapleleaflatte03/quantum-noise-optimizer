"""Tests for noise_optimizer package."""
import sys
sys.path.insert(0, "src")

from noise_optimizer import (
    NoiseProfiler, NoiseAwareOptimizer, Benchmark,
    optimize_circuit, merge_rotations, cancel_inverse_pairs, commute_and_cancel, circuit_stats,
)
from pyqpanda3 import core, quantum_info
import numpy as np


def test_rotation_merging():
    """Adjacent same-type rotations should merge into one."""
    prog = core.QProg()
    prog << core.RZ(0, 0.3) << core.RZ(0, 0.5) << core.RZ(0, 0.2)
    opt = merge_rotations(prog)
    stats = circuit_stats(opt)
    assert stats["total_gates"] == 1, f"Expected 1 gate, got {stats['total_gates']}"
    # Check merged angle ≈ 1.0
    ops = opt.operations()
    assert abs(ops[0].parameters()[0] - 1.0) < 1e-9
    print("PASS: test_rotation_merging")


def test_rotation_merging_cancels_to_zero():
    """Rotations that sum to 0 (mod 2π) should be removed entirely."""
    prog = core.QProg()
    prog << core.RZ(0, np.pi) << core.RZ(0, np.pi)  # sum = 2π ≡ 0
    opt = merge_rotations(prog)
    assert circuit_stats(opt)["total_gates"] == 0
    print("PASS: test_rotation_merging_cancels_to_zero")


def test_gate_cancellation():
    """Adjacent self-inverse gates should cancel."""
    prog = core.QProg()
    prog << core.H(0) << core.H(0)
    opt = cancel_inverse_pairs(prog)
    assert circuit_stats(opt)["total_gates"] == 0
    print("PASS: test_gate_cancellation")


def test_cnot_cancellation():
    """Adjacent CNOT on same qubits should cancel."""
    prog = core.QProg()
    prog << core.CNOT(0, 1) << core.CNOT(0, 1)
    opt = cancel_inverse_pairs(prog)
    assert circuit_stats(opt)["total_gates"] == 0
    print("PASS: test_cnot_cancellation")


def test_commute_and_cancel():
    """Gates separated by non-overlapping gates should commute and cancel."""
    prog = core.QProg()
    # H(0) · X(1) · H(0) → X(1) after commutation + cancellation
    prog << core.H(0) << core.X(1) << core.H(0)
    opt = commute_and_cancel(prog)
    stats = circuit_stats(opt)
    assert stats["total_gates"] == 1, f"Expected 1 gate, got {stats['total_gates']}"
    print("PASS: test_commute_and_cancel")


def test_optimize_circuit_convergence():
    """Full optimization should reduce a redundant circuit."""
    prog = core.QProg()
    prog << core.H(0) << core.H(0) << core.RZ(0, 0.5) << core.RZ(0, -0.5)
    prog << core.CNOT(0, 1) << core.CNOT(0, 1)
    opt = optimize_circuit(prog)
    assert circuit_stats(opt)["total_gates"] == 0
    print("PASS: test_optimize_circuit_convergence")


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

    baseline = core.QProg()
    baseline << core.H(0) << core.CNOT(0, 1) << core.measure([0, 1], [0, 1])
    m1 = core.CPUQVM()
    m1.run(baseline, shots=10000, model=noise)
    baseline_counts = m1.result().get_counts()

    opt_circuit = optimizer.build_bell_state()
    opt_prog = core.QProg()
    opt_prog << opt_circuit << core.measure([0, 1], [0, 1])
    m2 = core.CPUQVM()
    m2.run(opt_prog, shots=10000, model=noise)
    opt_counts = m2.result().get_counts()

    ideal = {"00": 0.5, "11": 0.5}
    baseline_fid = quantum_info.hellinger_fidelity(ideal, {k: v/10000 for k, v in baseline_counts.items()})
    opt_fid = quantum_info.hellinger_fidelity(ideal, {k: v/10000 for k, v in opt_counts.items()})

    assert opt_fid > baseline_fid
    print(f"PASS: test_optimized_bell_state_higher_fidelity (baseline={baseline_fid:.4f}, opt={opt_fid:.4f})")


def test_benchmark_runs():
    """Benchmark should complete without errors."""
    bench = Benchmark(shots=1000)
    configs = [{"type": "depolarizing", "strength": 0.02, "asymmetric": True, "cnot_factor": 5}]
    results = bench.run_all(configs)
    assert len(results) == 3
    assert all(r.fidelity_baseline > 0 for r in results)
    print("PASS: test_benchmark_runs")


if __name__ == "__main__":
    test_rotation_merging()
    test_rotation_merging_cancels_to_zero()
    test_gate_cancellation()
    test_cnot_cancellation()
    test_commute_and_cancel()
    test_optimize_circuit_convergence()
    test_profiler_detects_noisy_gate()
    test_optimizer_uses_cz_when_better()
    test_optimized_bell_state_higher_fidelity()
    test_benchmark_runs()
    print("\nAll tests passed!")

