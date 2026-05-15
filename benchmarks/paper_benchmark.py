"""Publication-quality benchmark: Bounded ZNE vs standard methods for arXiv paper."""

import sys
import json
import time
import numpy as np
from itertools import product

sys.path.insert(0, 'src')

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, depolarizing_error
from qiskit.quantum_info import Statevector, SparsePauliOp
from noise_optimizer.bounded_zne import PhysicallyBoundedZNE, auto_select_model

SHOTS = 4096
SCALE_FACTORS = [1.0, 1.5, 2.0, 2.5, 3.0]
CX_NOISE_LEVELS = [0.01, 0.03, 0.05, 0.08, 0.12]


# --- Circuit generators ---

def make_ghz(n):
    qc = QuantumCircuit(n)
    qc.h(0)
    for i in range(1, n):
        qc.cx(0, i)
    return qc

def make_random(n, depth, seed=42):
    rng = np.random.default_rng(seed + n * 100 + depth)
    qc = QuantumCircuit(n)
    gates_1q = ['h', 'x', 'rx', 'rz']
    for _ in range(depth):
        for q in range(n):
            g = rng.choice(gates_1q)
            if g == 'h': qc.h(q)
            elif g == 'x': qc.x(q)
            elif g == 'rx': qc.rx(rng.uniform(0.1, np.pi), q)
            else: qc.rz(rng.uniform(0.1, np.pi), q)
        for q in range(0, n - 1, 2):
            qc.cx(q, q + 1)
        for q in range(1, n - 1, 2):
            qc.cx(q, q + 1)
    return qc

def make_qft(n):
    qc = QuantumCircuit(n)
    for i in range(n):
        qc.h(i)
        for j in range(i + 1, n):
            qc.cp(np.pi / 2**(j - i), i, j)
    return qc


# --- Observable and ideal value ---

def parity_expectation_ideal(qc, n):
    sv = Statevector.from_instruction(qc)
    op = SparsePauliOp('Z' * n)
    return float(np.real(sv.expectation_value(op)))

def expectation_from_counts(counts, n):
    total = sum(counts.values())
    val = 0.0
    for bitstring, count in counts.items():
        parity = bitstring.count('1') % 2
        val += ((-1) ** parity) * count / total
    return val


# --- Noise and folding ---

def build_noise_model(p_cx):
    nm = NoiseModel()
    nm.add_all_qubit_quantum_error(depolarizing_error(p_cx / 10, 1), ['h', 'x', 'rx', 'rz', 'ry'])
    nm.add_all_qubit_quantum_error(depolarizing_error(p_cx, 2), ['cx', 'cp'])
    return nm

def fold_circuit(qc, scale_factor):
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


# --- ZNE methods ---

def standard_zne(sfs, evs, degree):
    coeffs = np.polyfit(sfs, evs, min(degree, len(sfs) - 1))
    return float(np.polyval(coeffs, 0))

def bounded_zne(sfs, evs):
    try:
        _, model = auto_select_model(sfs, evs, bounds=(-1.0, 1.0))
        return float(model.zero_noise_estimate_)
    except Exception:
        return standard_zne(sfs, evs, 1)


# --- Main benchmark ---

def run_benchmark():
    # Build circuit configs
    configs = []
    for n in range(3, 9):
        configs.append(('GHZ', n, make_ghz(n)))
    for n in range(3, 7):
        for d in [5, 10, 15, 20]:
            configs.append((f'Random_d{d}', n, make_random(n, d)))
    for n in range(3, 6):
        configs.append(('QFT', n, make_qft(n)))

    results = []
    total = len(configs) * len(CX_NOISE_LEVELS)
    print(f"Running {total} configurations ({len(configs)} circuits × {len(CX_NOISE_LEVELS)} noise levels)...")
    start = time.time()

    sim_cache = {}
    for p_cx in CX_NOISE_LEVELS:
        nm = build_noise_model(p_cx)
        sim_cache[p_cx] = AerSimulator(noise_model=nm)

    for idx, (ctype, n, qc) in enumerate(configs):
        ideal = parity_expectation_ideal(qc, n)
        for p_cx in CX_NOISE_LEVELS:
            sim = sim_cache[p_cx]
            # Get expectations at each scale factor
            evs = []
            for sf in SCALE_FACTORS:
                folded = fold_circuit(qc, sf)
                meas_qc = folded.copy()
                meas_qc.measure_all()
                result = sim.run(meas_qc, shots=SHOTS).result()
                evs.append(expectation_from_counts(result.get_counts(), n))

            raw = evs[0]
            lin = standard_zne(SCALE_FACTORS, evs, 1)
            quad = standard_zne(SCALE_FACTORS, evs, 2)
            bnd = bounded_zne(SCALE_FACTORS, evs)

            results.append({
                'circuit_type': ctype,
                'n_qubits': n,
                'p_cx': p_cx,
                'ideal': ideal,
                'raw': raw,
                'linear_zne': lin,
                'quadratic_zne': quad,
                'bounded_zne': bnd,
            })

        if (idx + 1) % 5 == 0:
            print(f"  {idx+1}/{len(configs)} circuits done ({time.time()-start:.1f}s)")

    elapsed = time.time() - start
    print(f"Completed in {elapsed:.1f}s")
    return results


def compute_metrics(results):
    """Compute MAE, win rate, unphysical rate per method."""
    methods = ['raw', 'linear_zne', 'quadratic_zne', 'bounded_zne']
    metrics = {}
    for m in methods:
        errors = [abs(r[m] - r['ideal']) for r in results]
        unphysical = [1 for r in results if abs(r[m]) > 1.0]
        metrics[m] = {
            'mae': float(np.mean(errors)),
            'median_ae': float(np.median(errors)),
            'unphysical_rate': len(unphysical) / len(results),
        }

    # Win rates for bounded
    n = len(results)
    metrics['bounded_zne']['win_vs_raw'] = sum(
        1 for r in results if abs(r['bounded_zne'] - r['ideal']) < abs(r['raw'] - r['ideal'])
    ) / n
    metrics['bounded_zne']['win_vs_linear'] = sum(
        1 for r in results if abs(r['bounded_zne'] - r['ideal']) < abs(r['linear_zne'] - r['ideal'])
    ) / n
    metrics['bounded_zne']['win_vs_quadratic'] = sum(
        1 for r in results if abs(r['bounded_zne'] - r['ideal']) < abs(r['quadratic_zne'] - r['ideal'])
    ) / n
    metrics['bounded_zne']['best_overall'] = sum(
        1 for r in results if abs(r['bounded_zne'] - r['ideal']) <= min(
            abs(r['raw'] - r['ideal']),
            abs(r['linear_zne'] - r['ideal']),
            abs(r['quadratic_zne'] - r['ideal'])
        )
    ) / n

    # Per noise level
    per_noise = {}
    for p_cx in CX_NOISE_LEVELS:
        subset = [r for r in results if r['p_cx'] == p_cx]
        sn = len(subset)
        per_noise[str(p_cx)] = {
            'mae_raw': float(np.mean([abs(r['raw'] - r['ideal']) for r in subset])),
            'mae_linear': float(np.mean([abs(r['linear_zne'] - r['ideal']) for r in subset])),
            'mae_quadratic': float(np.mean([abs(r['quadratic_zne'] - r['ideal']) for r in subset])),
            'mae_bounded': float(np.mean([abs(r['bounded_zne'] - r['ideal']) for r in subset])),
            'win_vs_linear': sum(1 for r in subset if abs(r['bounded_zne'] - r['ideal']) < abs(r['linear_zne'] - r['ideal'])) / sn,
            'unphysical_linear': sum(1 for r in subset if abs(r['linear_zne']) > 1.0) / sn,
            'unphysical_quad': sum(1 for r in subset if abs(r['quadratic_zne']) > 1.0) / sn,
            'unphysical_bounded': sum(1 for r in subset if abs(r['bounded_zne']) > 1.0) / sn,
        }

    # Per circuit type
    per_circuit = {}
    for ctype in ['GHZ', 'Random', 'QFT']:
        subset = [r for r in results if r['circuit_type'].startswith(ctype)]
        sn = len(subset)
        if sn == 0:
            continue
        per_circuit[ctype] = {
            'mae_raw': float(np.mean([abs(r['raw'] - r['ideal']) for r in subset])),
            'mae_linear': float(np.mean([abs(r['linear_zne'] - r['ideal']) for r in subset])),
            'mae_quadratic': float(np.mean([abs(r['quadratic_zne'] - r['ideal']) for r in subset])),
            'mae_bounded': float(np.mean([abs(r['bounded_zne'] - r['ideal']) for r in subset])),
            'win_vs_linear': sum(1 for r in subset if abs(r['bounded_zne'] - r['ideal']) < abs(r['linear_zne'] - r['ideal'])) / sn,
        }

    metrics['per_noise'] = per_noise
    metrics['per_circuit'] = per_circuit
    return metrics


def print_latex_table(metrics, results):
    """Print LaTeX-ready results table."""
    print("\n% === LaTeX Table: Overall Results ===")
    print(r"\begin{table}[h]")
    print(r"\centering")
    print(r"\caption{Comparison of ZNE methods across all benchmark configurations.}")
    print(r"\label{tab:overall}")
    print(r"\begin{tabular}{lcccc}")
    print(r"\toprule")
    print(r"Method & MAE $\downarrow$ & Median AE & Unphysical (\%) & Win Rate (\%) \\")
    print(r"\midrule")

    for m, label in [('raw', 'Raw (no mitigation)'), ('linear_zne', 'Linear ZNE'),
                     ('quadratic_zne', 'Quadratic ZNE'), ('bounded_zne', r'\textbf{Bounded ZNE (ours)}')]:
        mae = metrics[m]['mae']
        med = metrics[m]['median_ae']
        unp = metrics[m]['unphysical_rate'] * 100
        if m == 'bounded_zne':
            wr = metrics[m]['best_overall'] * 100
            print(f"{label} & \\textbf{{{mae:.4f}}} & \\textbf{{{med:.4f}}} & \\textbf{{{unp:.1f}}} & \\textbf{{{wr:.1f}}} \\\\")
        else:
            print(f"{label} & {mae:.4f} & {med:.4f} & {unp:.1f} & --- \\\\")

    print(r"\bottomrule")
    print(r"\end{tabular}")
    print(r"\end{table}")

    # Per noise level table
    print("\n% === LaTeX Table: Per Noise Level ===")
    print(r"\begin{table}[h]")
    print(r"\centering")
    print(r"\caption{Bounded ZNE win rate and MAE by CX depolarizing noise level.}")
    print(r"\label{tab:pernoise}")
    print(r"\begin{tabular}{ccccccc}")
    print(r"\toprule")
    print(r"$p_{\text{CX}}$ & MAE\textsubscript{raw} & MAE\textsubscript{lin} & MAE\textsubscript{quad} & MAE\textsubscript{bounded} & Win\% & Unphys\textsubscript{quad}\% \\")
    print(r"\midrule")
    for p_cx in CX_NOISE_LEVELS:
        d = metrics['per_noise'][str(p_cx)]
        print(f"{p_cx:.2f} & {d['mae_raw']:.4f} & {d['mae_linear']:.4f} & {d['mae_quadratic']:.4f} & {d['mae_bounded']:.4f} & {d['win_vs_linear']*100:.0f} & {d['unphysical_quad']*100:.0f} \\\\")
    print(r"\bottomrule")
    print(r"\end{tabular}")
    print(r"\end{table}")

    # Per circuit type
    print("\n% === LaTeX Table: Per Circuit Type ===")
    print(r"\begin{table}[h]")
    print(r"\centering")
    print(r"\caption{Performance by circuit type.}")
    print(r"\label{tab:percircuit}")
    print(r"\begin{tabular}{lccccc}")
    print(r"\toprule")
    print(r"Circuit & MAE\textsubscript{raw} & MAE\textsubscript{lin} & MAE\textsubscript{quad} & MAE\textsubscript{bounded} & Win\% \\")
    print(r"\midrule")
    for ctype in ['GHZ', 'Random', 'QFT']:
        if ctype in metrics['per_circuit']:
            d = metrics['per_circuit'][ctype]
            print(f"{ctype} & {d['mae_raw']:.4f} & {d['mae_linear']:.4f} & {d['mae_quadratic']:.4f} & {d['mae_bounded']:.4f} & {d['win_vs_linear']*100:.0f} \\\\")
    print(r"\bottomrule")
    print(r"\end{tabular}")
    print(r"\end{table}")


if __name__ == '__main__':
    results = run_benchmark()
    metrics = compute_metrics(results)

    # Save
    output = {'results': results, 'metrics': metrics}
    with open('results/paper_benchmark.json', 'w') as f:
        json.dump(output, f, indent=2)
    print("\nSaved to results/paper_benchmark.json")

    # Print summary
    print(f"\n{'='*70}")
    print("PAPER BENCHMARK RESULTS")
    print(f"{'='*70}")
    print(f"Total configurations: {len(results)}")
    print(f"\nOverall MAE:")
    for m in ['raw', 'linear_zne', 'quadratic_zne', 'bounded_zne']:
        print(f"  {m:20s}: {metrics[m]['mae']:.4f}")
    print(f"\nBounded ZNE win rates:")
    print(f"  vs Raw:       {metrics['bounded_zne']['win_vs_raw']*100:.1f}%")
    print(f"  vs Linear:    {metrics['bounded_zne']['win_vs_linear']*100:.1f}%")
    print(f"  vs Quadratic: {metrics['bounded_zne']['win_vs_quadratic']*100:.1f}%")
    print(f"  Best overall: {metrics['bounded_zne']['best_overall']*100:.1f}%")
    print(f"\nUnphysical prediction rates:")
    for m in ['raw', 'linear_zne', 'quadratic_zne', 'bounded_zne']:
        print(f"  {m:20s}: {metrics[m]['unphysical_rate']*100:.1f}%")

    print_latex_table(metrics, results)
