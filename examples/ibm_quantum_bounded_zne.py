"""IBM Quantum Bounded ZNE Demo.

Demonstrates PhysicallyBoundedZNE on IBM Quantum hardware (or Aer simulation).

Modes:
  - SIMULATION (default): Qiskit Aer with realistic noise model
  - HARDWARE: qiskit-ibm-runtime when IBM_QUANTUM_TOKEN env var is set

Usage:
  python examples/ibm_quantum_bounded_zne.py
"""
import sys, os, json
import numpy as np

sys.path.insert(0, "src")

from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import (
    NoiseModel, depolarizing_error, ReadoutError, thermal_relaxation_error
)
from noise_optimizer.bounded_zne import PhysicallyBoundedZNE, auto_select_model

# --- Configuration ---
SCALE_FACTORS = [1.0, 1.3, 1.6, 2.0, 2.5]
QUBIT_COUNTS = [3, 4, 5]
SHOTS = 4096
RESULTS_FILE = "results/ibm_quantum_results.json"


def build_ghz_circuit(n_qubits):
    """Create an n-qubit GHZ state circuit (no measurements)."""
    qc = QuantumCircuit(n_qubits)
    qc.h(0)
    for i in range(1, n_qubits):
        qc.cx(i - 1, i)
    return qc


def unitary_fold(circuit, scale_factor):
    """Apply unitary folding to amplify noise by scale_factor.

    Uses global circuit folding: C -> C (C† C)^n with partial tail folding.
    The effective noise scale is proportional to the total number of gates executed.
    For non-integer folds, we fold individual gates from the tail of the circuit.
    """
    if scale_factor < 1.0:
        raise ValueError("Scale factor must be >= 1.0")
    if np.isclose(scale_factor, 1.0):
        return circuit.copy()

    n_gates = circuit.size()
    # Total gate executions needed for desired scale
    target_gates = int(round(scale_factor * n_gates))
    # Must be odd (original + pairs of gate†,gate)
    if target_gates % 2 == 0:
        target_gates += 1

    # Number of additional gates beyond original
    additional = target_gates - n_gates
    # Full circuit folds (each adds 2*n_gates)
    num_full_folds = additional // (2 * n_gates)
    remaining_gates = additional - num_full_folds * (2 * n_gates)
    # Remaining gates come in pairs (gate† gate), so number of tail gates to fold
    n_tail = remaining_gates // 2

    folded = circuit.copy()
    inv = circuit.inverse()

    # Full folds: append C† C
    for _ in range(num_full_folds):
        folded = folded.compose(inv).compose(circuit)

    # Partial fold: fold the last n_tail gates from the tail
    if n_tail > 0:
        tail_gates = circuit.data[-n_tail:]
        tail_circ = QuantumCircuit(circuit.num_qubits)
        for instr in tail_gates:
            tail_circ.append(instr)
        tail_inv = tail_circ.inverse()
        folded = folded.compose(tail_inv).compose(tail_circ)

    return folded


def build_noise_model():
    """Realistic noise model: 1q depol 0.1%, 2q depol 1%, readout 2%, T1/T2 relaxation."""
    nm = NoiseModel()

    # Combined 1q error: depolarizing (0.1%) composed with thermal relaxation
    # T1=100us, T2=80us, gate_time=50ns for 1q gates
    t1, t2 = 100e-6, 80e-6
    dep_1q = depolarizing_error(0.001, 1)
    thermal_1q = thermal_relaxation_error(t1, t2, 50e-9)
    combined_1q = dep_1q.compose(thermal_1q)
    nm.add_all_qubit_quantum_error(combined_1q, ['h', 'x', 'rz', 'sx'])

    # Combined 2q error: depolarizing (1%) composed with thermal relaxation
    # gate_time=300ns for 2q gates
    dep_2q = depolarizing_error(0.01, 2)
    thermal_2q = thermal_relaxation_error(t1, t2, 300e-9).expand(
        thermal_relaxation_error(t1, t2, 300e-9)
    )
    combined_2q = dep_2q.compose(thermal_2q)
    nm.add_all_qubit_quantum_error(combined_2q, ['cx'])

    # Readout error: 2%
    ro = ReadoutError([[0.98, 0.02], [0.02, 0.98]])
    nm.add_all_qubit_readout_error(ro)

    return nm


def get_backend():
    """Return backend: IBM hardware if token set, else Aer simulator."""
    token = os.environ.get("IBM_QUANTUM_TOKEN")
    if token:
        from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2
        service = QiskitRuntimeService(channel="ibm_quantum", token=token)
        backend = service.least_busy(simulator=False, operational=True, min_num_qubits=5)
        print(f"[HARDWARE MODE] Using backend: {backend.name}")
        return backend, "hardware"
    else:
        nm = build_noise_model()
        backend = AerSimulator(noise_model=nm)
        print("[SIMULATION MODE] Using Aer with realistic noise model")
        return backend, "simulation"


def measure_expectation(circuit, backend, mode):
    """Measure GHZ fidelity: P(|00...0>) + P(|11...1>)."""
    n = circuit.num_qubits
    meas_circ = circuit.copy()
    meas_circ.measure_all()

    if mode == "hardware":
        from qiskit_ibm_runtime import SamplerV2
        from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
        pm = generate_preset_pass_manager(backend=backend, optimization_level=1)
        transpiled = pm.run(meas_circ)
        sampler = SamplerV2(backend)
        job = sampler.run([transpiled], shots=SHOTS)
        result = job.result()
        counts = result[0].data.meas.get_counts()
    else:
        from qiskit import transpile
        transpiled = transpile(meas_circ, backend, optimization_level=0)
        result = backend.run(transpiled, shots=SHOTS).result()
        counts = result.get_counts()

    total = sum(counts.values())
    all_zeros = '0' * n
    all_ones = '1' * n
    fidelity = (counts.get(all_zeros, 0) + counts.get(all_ones, 0)) / total
    return fidelity


def standard_zne(scale_factors, values, order=1):
    """Standard polynomial ZNE extrapolation (unbounded)."""
    coeffs = np.polyfit(scale_factors, values, order)
    return np.polyval(coeffs, 0.0)


def run_experiment():
    """Run the full bounded ZNE experiment."""
    backend, mode = get_backend()
    all_results = {}

    print(f"\nScale factors: {SCALE_FACTORS}")
    print(f"Qubit counts: {QUBIT_COUNTS}")
    print(f"Shots: {SHOTS}\n")
    print("=" * 72)

    for n_qubits in QUBIT_COUNTS:
        print(f"\n{'─' * 72}")
        print(f"  GHZ-{n_qubits} ({n_qubits} qubits)")
        print(f"{'─' * 72}")

        base_circuit = build_ghz_circuit(n_qubits)
        expectations = []

        for sf in SCALE_FACTORS:
            folded = unitary_fold(base_circuit, sf)
            exp_val = measure_expectation(folded, backend, mode)
            expectations.append(exp_val)
            print(f"  λ={sf:.1f}: fidelity={exp_val:.4f} (depth={folded.depth()})")

        # Bounded ZNE (auto-select best model)
        model_name, bounded_model = auto_select_model(SCALE_FACTORS, expectations, bounds=(0.0, 1.0))
        bounded_estimate = bounded_model.zero_noise_estimate_

        # Standard linear ZNE
        linear_estimate = standard_zne(SCALE_FACTORS, expectations, order=1)

        # Standard quadratic ZNE
        quadratic_estimate = standard_zne(SCALE_FACTORS, expectations, order=2)

        # Ideal value for GHZ fidelity
        ideal = 1.0

        print(f"\n  Results:")
        print(f"    Noisy (λ=1):        {expectations[0]:.4f}")
        print(f"    Linear ZNE:         {linear_estimate:.4f}")
        print(f"    Quadratic ZNE:      {quadratic_estimate:.4f}")
        print(f"    Bounded ZNE ({model_name}): {bounded_estimate:.4f}")
        print(f"    Ideal:              {ideal:.4f}")
        print(f"    Bounded ZNE error:  {abs(bounded_estimate - ideal):.4f}")

        all_results[f"ghz_{n_qubits}"] = {
            "n_qubits": n_qubits,
            "scale_factors": SCALE_FACTORS,
            "expectations": expectations,
            "noisy": expectations[0],
            "linear_zne": float(linear_estimate),
            "quadratic_zne": float(quadratic_estimate),
            "bounded_zne": float(bounded_estimate),
            "bounded_model": model_name,
            "ideal": ideal,
            "bounded_error": float(abs(bounded_estimate - ideal)),
            "linear_error": float(abs(linear_estimate - ideal)),
            "quadratic_error": float(abs(quadratic_estimate - ideal)),
        }

    # Summary table
    print(f"\n{'=' * 72}")
    print(f"  SUMMARY: Zero-Noise Extrapolation Comparison")
    print(f"{'=' * 72}")
    print(f"  {'Circuit':<10} {'Noisy':<8} {'Linear':<8} {'Quadratic':<10} {'Bounded':<8} {'Model':<16}")
    print(f"  {'─' * 68}")
    for key, r in all_results.items():
        print(f"  {key:<10} {r['noisy']:.4f}   {r['linear_zne']:.4f}   "
              f"{r['quadratic_zne']:.4f}     {r['bounded_zne']:.4f}   {r['bounded_model']}")

    print(f"\n  Error vs ideal (lower is better):")
    print(f"  {'Circuit':<10} {'Linear err':<12} {'Quadratic err':<14} {'Bounded err':<12}")
    print(f"  {'─' * 50}")
    for key, r in all_results.items():
        print(f"  {key:<10} {r['linear_error']:.4f}       {r['quadratic_error']:.4f}         {r['bounded_error']:.4f}")

    # Save results
    os.makedirs("results", exist_ok=True)
    output = {"mode": mode, "shots": SHOTS, "scale_factors": SCALE_FACTORS, "results": all_results}
    with open(RESULTS_FILE, "w") as f:
        json.dump(output, f, indent=2)
    print(f"\n  Results saved to {RESULTS_FILE}")


if __name__ == "__main__":
    run_experiment()
