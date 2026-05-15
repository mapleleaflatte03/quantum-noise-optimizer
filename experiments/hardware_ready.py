"""Hardware-ready ZNE experiment. Runs on simulator now, Wukong later.

Modes:
  simulator (default): pyqpanda3 CPUQVM with Wukong-calibrated noise
  wukong: Real hardware (currently broken - errCode 33 API mismatch)

Usage:
  python experiments/hardware_ready.py              # simulator
  python experiments/hardware_ready.py --wukong     # real hardware (when fixed)
"""
import sys, json, time, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pyqpanda3 import core, quantum_info
from noise_optimizer.bounded_zne import auto_select_model

# Wukong 180 calibration-derived noise rates
WUKONG_NOISE = {"cz_error": 0.03, "single_qubit_error": 0.005, "readout_error": 0.02}
OPTIMAL_QUBITS = [78, 88, 97]
SCALE_FACTORS = [1.0, 1.5, 2.0, 2.5, 3.0]


def run_simulator(prog, n_qubits, noise_scale=1.0, shots=4096):
    """Run on CPUQVM with Wukong-calibrated noise."""
    noise = core.NoiseModel()
    noise.add_all_qubit_quantum_error(
        core.depolarizing_error(min(WUKONG_NOISE["cz_error"] * noise_scale, 0.75)),
        core.GateType.CNOT)
    noise.add_all_qubit_quantum_error(
        core.depolarizing_error(min(WUKONG_NOISE["single_qubit_error"] * noise_scale, 0.75)),
        core.GateType.H)

    prog_m = core.QProg()
    prog_m << prog << core.measure(list(range(n_qubits)), list(range(n_qubits)))
    machine = core.CPUQVM()
    machine.run(prog_m, shots=shots, model=noise)
    counts = machine.result().get_counts()
    total = sum(counts.values())
    return sum((1 - 2*(k.count('1') % 2)) * v / total for k, v in counts.items())


def run_ideal(prog, n_qubits, shots=4096):
    """Run without noise."""
    prog_m = core.QProg()
    prog_m << prog << core.measure(list(range(n_qubits)), list(range(n_qubits)))
    machine = core.CPUQVM()
    machine.run(prog_m, shots=shots)
    counts = machine.result().get_counts()
    total = sum(counts.values())
    return sum((1 - 2*(k.count('1') % 2)) * v / total for k, v in counts.items())


def make_ghz(n):
    prog = core.QProg()
    prog << core.H(0)
    for i in range(1, n):
        prog << core.CNOT(i-1, i)
    return prog


def make_bell():
    prog = core.QProg()
    prog << core.H(0) << core.CNOT(0, 1)
    return prog


def zne_experiment(prog, n_qubits, name):
    """Run full ZNE experiment: measure at multiple noise scales, extrapolate."""
    ideal = run_ideal(prog, n_qubits)
    exps = [run_simulator(prog, n_qubits, s) for s in SCALE_FACTORS]

    # Standard linear
    coeffs = np.polyfit(SCALE_FACTORS, exps, 1)
    linear = float(np.polyval(coeffs, 0))

    # Bounded ZNE (our method)
    model_name, model = auto_select_model(SCALE_FACTORS, exps, bounds=(-1, 1))
    bounded = model.zero_noise_estimate_

    result = {
        "circuit": name, "n_qubits": n_qubits,
        "ideal": round(ideal, 4), "raw": round(exps[0], 4),
        "linear_zne": round(linear, 4), "bounded_zne": round(bounded, 4),
        "model": model_name,
        "error_raw": round(abs(exps[0] - ideal), 4),
        "error_linear": round(abs(linear - ideal), 4),
        "error_bounded": round(abs(bounded - ideal), 4),
        "measurements": [round(e, 4) for e in exps],
    }
    return result


def main():
    mode = "wukong" if "--wukong" in sys.argv else "simulator"
    print(f"=== ZNE Experiment (mode: {mode}) ===")
    print(f"Noise model: CZ={WUKONG_NOISE['cz_error']*100}%, 1Q={WUKONG_NOISE['single_qubit_error']*100}%")
    print(f"Scale factors: {SCALE_FACTORS}")

    if mode == "wukong":
        print("\n⚠️  Wukong mode currently broken (errCode 33: API format mismatch)")
        print("    pyqpanda3 0.3.5 sends instruction format that server rejects.")
        print("    Falling back to simulator.\n")
        # NOTE: When OriginQ fixes the API, replace run_simulator with real hardware calls
        # using job.query() polling (not blocking job.result())

    results = []
    circuits = [
        (make_bell(), 2, "Bell"),
        (make_ghz(3), 3, "GHZ-3"),
        (make_ghz(4), 4, "GHZ-4"),
        (make_ghz(5), 5, "GHZ-5"),
    ]

    for prog, n, name in circuits:
        r = zne_experiment(prog, n, name)
        winner = "bounded" if r["error_bounded"] <= r["error_linear"] else "linear"
        print(f"  {name:6s}: ideal={r['ideal']:+.4f} raw_err={r['error_raw']:.4f} "
              f"linear_err={r['error_linear']:.4f} bounded_err={r['error_bounded']:.4f} → {winner}")
        results.append(r)

    # Save
    output = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "mode": mode, "noise_model": WUKONG_NOISE,
        "scale_factors": SCALE_FACTORS, "results": results,
    }
    out_path = os.path.join(os.path.dirname(__file__), '..', 'results', 'experiment_data.json')
    with open(out_path, 'w') as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
