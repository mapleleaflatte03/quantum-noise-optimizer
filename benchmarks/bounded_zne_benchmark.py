"""Benchmark: PhysicallyBoundedZNE vs Standard ZNE across circuit types, noise levels, scale factors."""

import sys
import json
import time
import numpy as np
from itertools import product

sys.path.insert(0, "/home/ubuntu/quantum-noise-optimizer/src")

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error
from qiskit.quantum_info import Statevector, SparsePauliOp

from noise_optimizer.bounded_zne import PhysicallyBoundedZNE, auto_select_model

SHOTS = 4096

# --- Circuit generators ---

def make_ghz(n):
    qc = QuantumCircuit(n)
    qc.h(0)
    for i in range(1, n):
        qc.cx(0, i)
    return qc

def make_random_circuit(n, seed=42):
    rng = np.random.default_rng(seed + n)
    qc = QuantumCircuit(n)
    for _ in range(n * 2):
        q = rng.integers(0, n)
        gate = rng.choice(['h', 'x', 'rx', 'rz'])
        if gate == 'h':
            qc.h(q)
        elif gate == 'x':
            qc.x(q)
        elif gate == 'rx':
            qc.rx(rng.uniform(0.1, np.pi), q)
        else:
            qc.rz(rng.uniform(0.1, np.pi), q)
    for i in range(n - 1):
        qc.cx(i, i + 1)
    return qc

def make_qft(n):
    qc = QuantumCircuit(n)
    for i in range(n):
        qc.h(i)
        for j in range(i + 1, n):
            qc.cp(np.pi / 2**(j - i), i, j)
    return qc

# --- Z-parity observable ---

def z_parity_op(n):
    """Z⊗Z⊗...⊗Z parity operator."""
    return SparsePauliOp('Z' * n)

def ideal_expectation(qc, n):
    """Compute ideal <Z^n> via statevector."""
    sv = Statevector.from_instruction(qc)
    op = z_parity_op(n)
    return float(np.real(sv.expectation_value(op)))

# --- Noise model builder ---

def build_noise_model(p1q, p2q):
    nm = NoiseModel()
    err_1q = depolarizing_error(p1q, 1)
    err_2q = depolarizing_error(p2q, 2)
    nm.add_all_qubit_quantum_error(err_1q, ['h', 'x', 'rx', 'rz', 'ry'])
    nm.add_all_qubit_quantum_error(err_2q, ['cx', 'cp'])
    return nm

# --- Noise scaling via unitary folding ---

def fold_circuit(qc, scale_factor):
    """Global unitary folding: scale_factor=1 means original, 3 means G·G†·G."""
    if scale_factor <= 1.0:
        return qc.copy()
    n_full = int((scale_factor - 1) / 2)
    remainder = (scale_factor - 1) - 2 * n_full
    ops = qc.data
    n_partial = int(remainder / 2 * len(ops))

    folded = qc.copy()
    for _ in range(n_full):
        folded.compose(qc.inverse(), inplace=True)
        folded.compose(qc, inplace=True)
    if n_partial > 0:
        partial = QuantumCircuit(qc.num_qubits)
        for inst in ops[:n_partial]:
            partial.append(inst)
        folded.compose(partial.inverse(), inplace=True)
        folded.compose(partial, inplace=True)
    return folded

# --- Expectation value from counts ---

def expectation_from_counts(counts, n):
    """Compute <Z^n> = sum_x (-1)^(parity(x)) * p(x)."""
    total = sum(counts.values())
    val = 0.0
    for bitstring, count in counts.items():
        parity = bitstring.count('1') % 2
        val += ((-1) ** parity) * count / total
    return val

# --- Run noisy circuit and get expectation ---

def run_noisy(qc, noise_model, n):
    meas_qc = qc.copy()
    meas_qc.measure_all()
    sim = AerSimulator(noise_model=noise_model)
    result = sim.run(meas_qc, shots=SHOTS).result()
    counts = result.get_counts()
    return expectation_from_counts(counts, n)

# --- Standard ZNE (unconstrained polynomial fit) ---

def standard_zne(scale_factors, exp_values, degree):
    """Unconstrained polynomial extrapolation to scale=0."""
    coeffs = np.polyfit(scale_factors, exp_values, min(degree, len(scale_factors) - 1))
    return float(np.polyval(coeffs, 0))

# --- Main benchmark ---

def run_benchmark():
    circuits = {
        'GHZ_3': (make_ghz(3), 3),
        'GHZ_4': (make_ghz(4), 4),
        'GHZ_5': (make_ghz(5), 5),
        'Random_3': (make_random_circuit(3), 3),
        'Random_4': (make_random_circuit(4), 4),
        'Random_5': (make_random_circuit(5), 5),
        'QFT_3': (make_qft(3), 3),
        'QFT_4': (make_qft(4), 4),
    }

    noise_levels = {
        'low': (0.01, 0.03),
        'medium': (0.02, 0.05),
        'high': (0.04, 0.10),
    }

    scale_factor_sets = {
        'small': [1, 2, 3],
        'medium': [1, 1.5, 2, 2.5, 3],
        'large': [1, 2, 3, 4, 5],
    }

    results = []
    total = len(circuits) * len(noise_levels) * len(scale_factor_sets)
    print(f"Running {total} benchmark configurations...")
    start = time.time()

    for (circ_name, (qc, n)), (noise_name, (p1q, p2q)), (sf_name, sfs) in product(
        circuits.items(), noise_levels.items(), scale_factor_sets.items()
    ):
        ideal = ideal_expectation(qc, n)
        noise_model = build_noise_model(p1q, p2q)

        # Get expectation values at each scale factor
        exp_values = []
        for sf in sfs:
            folded = fold_circuit(qc, sf)
            ev = run_noisy(folded, noise_model, n)
            exp_values.append(ev)

        raw_noisy = exp_values[0]

        # Standard ZNE
        linear_est = standard_zne(sfs, exp_values, 1)
        quad_est = standard_zne(sfs, exp_values, 2)

        # Bounded ZNE (auto-select)
        try:
            model_name, model = auto_select_model(sfs, exp_values, bounds=(-1.0, 1.0))
            bounded_est = float(model.zero_noise_estimate_)
        except Exception:
            model_name = "failed"
            bounded_est = linear_est

        entry = {
            'circuit': circ_name,
            'noise_level': noise_name,
            'p1q': p1q,
            'p2q': p2q,
            'scale_factors': sf_name,
            'ideal': ideal,
            'raw_noisy': raw_noisy,
            'linear_zne': linear_est,
            'quadratic_zne': quad_est,
            'bounded_zne': bounded_est,
            'bounded_model': model_name,
            'error_raw': abs(raw_noisy - ideal),
            'error_linear': abs(linear_est - ideal),
            'error_quadratic': abs(quad_est - ideal),
            'error_bounded': abs(bounded_est - ideal),
        }
        results.append(entry)

    elapsed = time.time() - start
    print(f"Completed in {elapsed:.1f}s")
    return results


def print_summary(results):
    """Print win-rate summary table."""
    print("\n" + "=" * 80)
    print("BOUNDED ZNE BENCHMARK SUMMARY")
    print("=" * 80)

    # Overall win rates
    bounded_beats_linear = sum(1 for r in results if r['error_bounded'] < r['error_linear'])
    bounded_beats_quad = sum(1 for r in results if r['error_bounded'] < r['error_quadratic'])
    bounded_beats_raw = sum(1 for r in results if r['error_bounded'] < r['error_raw'])
    best_overall = sum(1 for r in results if r['error_bounded'] <= min(r['error_linear'], r['error_quadratic']))
    n = len(results)

    print(f"\nTotal configurations: {n}")
    print(f"{'Metric':<40} {'Win Rate':>10}")
    print("-" * 52)
    print(f"{'Bounded beats Linear ZNE':<40} {bounded_beats_linear}/{n} ({100*bounded_beats_linear/n:.1f}%)")
    print(f"{'Bounded beats Quadratic ZNE':<40} {bounded_beats_quad}/{n} ({100*bounded_beats_quad/n:.1f}%)")
    print(f"{'Bounded beats Raw (no mitigation)':<40} {bounded_beats_raw}/{n} ({100*bounded_beats_raw/n:.1f}%)")
    print(f"{'Bounded is best (vs linear+quad)':<40} {best_overall}/{n} ({100*best_overall/n:.1f}%)")

    # By noise level
    print(f"\n{'Noise Level':<12} {'vs Linear':>12} {'vs Quadratic':>14} {'Best Overall':>14}")
    print("-" * 54)
    for nl in ['low', 'medium', 'high']:
        subset = [r for r in results if r['noise_level'] == nl]
        sn = len(subset)
        bl = sum(1 for r in subset if r['error_bounded'] < r['error_linear'])
        bq = sum(1 for r in subset if r['error_bounded'] < r['error_quadratic'])
        bo = sum(1 for r in subset if r['error_bounded'] <= min(r['error_linear'], r['error_quadratic']))
        print(f"{nl:<12} {bl}/{sn} ({100*bl/sn:.0f}%)   {bq}/{sn} ({100*bq/sn:.0f}%)    {bo}/{sn} ({100*bo/sn:.0f}%)")

    # By circuit type
    print(f"\n{'Circuit':<12} {'vs Linear':>12} {'vs Quadratic':>14} {'Best Overall':>14}")
    print("-" * 54)
    for prefix in ['GHZ', 'Random', 'QFT']:
        subset = [r for r in results if r['circuit'].startswith(prefix)]
        sn = len(subset)
        if sn == 0:
            continue
        bl = sum(1 for r in subset if r['error_bounded'] < r['error_linear'])
        bq = sum(1 for r in subset if r['error_bounded'] < r['error_quadratic'])
        bo = sum(1 for r in subset if r['error_bounded'] <= min(r['error_linear'], r['error_quadratic']))
        print(f"{prefix:<12} {bl}/{sn} ({100*bl/sn:.0f}%)   {bq}/{sn} ({100*bq/sn:.0f}%)    {bo}/{sn} ({100*bo/sn:.0f}%)")

    # Average errors
    print(f"\n{'Method':<20} {'Mean Error':>12} {'Median Error':>14}")
    print("-" * 48)
    for method in ['raw', 'linear', 'quadratic', 'bounded']:
        errors = [r[f'error_{method}'] for r in results]
        print(f"{method:<20} {np.mean(errors):>12.6f} {np.median(errors):>14.6f}")


if __name__ == '__main__':
    results = run_benchmark()

    # Save results
    output_path = '/home/ubuntu/quantum-noise-optimizer/results/bounded_zne_benchmark.json'
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")

    print_summary(results)
