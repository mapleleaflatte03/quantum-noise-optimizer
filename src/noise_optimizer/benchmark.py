"""Benchmark: Compares circuit fidelity with and without noise-aware optimization."""

from dataclasses import dataclass
from pyqpanda3 import core, quantum_info
from .noise_profiler import NoiseProfiler, NoiseProfile
from .optimizer import NoiseAwareOptimizer
import numpy as np


@dataclass
class BenchmarkResult:
    """Result of a single benchmark comparison."""
    circuit_name: str
    n_qubits: int
    noise_type: str
    noise_strength: float
    fidelity_baseline: float
    fidelity_optimized: float
    improvement: float  # percentage improvement

    def __str__(self):
        return (
            f"{self.circuit_name} ({self.n_qubits}q, {self.noise_type}@{self.noise_strength:.3f}): "
            f"baseline={self.fidelity_baseline:.4f}, optimized={self.fidelity_optimized:.4f}, "
            f"improvement={self.improvement:+.2f}%"
        )


class Benchmark:
    """Runs comparative benchmarks between baseline and optimized circuits."""

    def __init__(self, shots: int = 10000):
        self.shots = shots
        self.results: list[BenchmarkResult] = []

    def run_all(self, noise_configs: list[dict] | None = None) -> list[BenchmarkResult]:
        """Run benchmarks across multiple noise configurations."""
        if noise_configs is None:
            noise_configs = self._default_configs()

        self.results = []
        for config in noise_configs:
            results = self._run_config(config)
            self.results.extend(results)

        return self.results

    def _default_configs(self) -> list[dict]:
        """Default noise configurations to benchmark.

        Includes both symmetric and asymmetric noise scenarios.
        Asymmetric = CNOT noisier than CZ (realistic for many superconducting devices).
        """
        configs = []
        # Symmetric noise (uniform across all gates)
        for strength in [0.01, 0.03, 0.05]:
            configs.append({"type": "depolarizing", "strength": strength, "asymmetric": False})

        # Asymmetric noise: CNOT 3-5x noisier than CZ (realistic for transmon qubits)
        for cnot_factor in [3, 5, 10]:
            for base in [0.01, 0.02, 0.03]:
                configs.append({
                    "type": "depolarizing", "strength": base,
                    "asymmetric": True, "cnot_factor": cnot_factor,
                })
        return configs

    def _build_noise_model(self, config: dict) -> core.NoiseModel:
        """Build a NoiseModel from config dict."""
        noise = core.NoiseModel()
        t = config["type"]
        s = config["strength"]
        asymmetric = config.get("asymmetric", False)
        cnot_factor = config.get("cnot_factor", 1)

        error_fn = {
            "depolarizing": core.depolarizing_error,
            "amplitude_damping": core.amplitude_damping_error,
            "phase_damping": core.phase_damping_error,
        }[t]

        # Single-qubit gates: low noise
        noise.add_all_qubit_quantum_error(error_fn(s * 0.5), core.GateType.H)
        noise.add_all_qubit_quantum_error(error_fn(s * 0.3), core.GateType.RX)
        noise.add_all_qubit_quantum_error(error_fn(s * 0.3), core.GateType.RY)
        noise.add_all_qubit_quantum_error(error_fn(s * 0.3), core.GateType.RZ)
        noise.add_all_qubit_quantum_error(error_fn(s * 0.1), core.GateType.X)
        noise.add_all_qubit_quantum_error(error_fn(s * 0.1), core.GateType.Y)
        noise.add_all_qubit_quantum_error(error_fn(s * 0.1), core.GateType.Z)

        # Two-qubit gates: asymmetric makes CNOT much noisier than CZ
        if asymmetric:
            cnot_noise = min(s * cnot_factor, 0.75)  # cap at 0.75
            cz_noise = s
        else:
            cnot_noise = s
            cz_noise = s

        noise.add_all_qubit_quantum_error(error_fn(cnot_noise), core.GateType.CNOT)
        noise.add_all_qubit_quantum_error(error_fn(cz_noise), core.GateType.CZ)

        return noise

    def _run_config(self, config: dict) -> list[BenchmarkResult]:
        """Run all circuit benchmarks for a single noise config."""
        noise_model = self._build_noise_model(config)

        # Profile the noise
        profiler = NoiseProfiler(noise_model, shots=self.shots)
        profile = profiler.profile()
        optimizer = NoiseAwareOptimizer(profile)

        results = []

        # Benchmark Bell state
        for n_qubits in [2, 3, 5]:
            result = self._benchmark_ghz(n_qubits, noise_model, optimizer, config)
            results.append(result)

        return results

    def _benchmark_ghz(self, n_qubits: int, noise_model: core.NoiseModel,
                       optimizer: NoiseAwareOptimizer, config: dict) -> BenchmarkResult:
        """Benchmark GHZ state creation."""
        # Baseline: standard H + CNOT chain
        baseline_prog = core.QProg()
        baseline_prog << core.H(0)
        for i in range(1, n_qubits):
            baseline_prog << core.CNOT(i - 1, i)
        baseline_prog << core.measure(list(range(n_qubits)), list(range(n_qubits)))

        # Optimized
        opt_circuit = optimizer.build_ghz_state(n_qubits)
        opt_prog = core.QProg()
        opt_prog << opt_circuit
        opt_prog << core.measure(list(range(n_qubits)), list(range(n_qubits)))

        # Run baseline
        machine = core.CPUQVM()
        machine.run(baseline_prog, shots=self.shots, model=noise_model)
        baseline_counts = machine.result().get_counts()

        # Run optimized
        machine2 = core.CPUQVM()
        machine2.run(opt_prog, shots=self.shots, model=noise_model)
        opt_counts = machine2.result().get_counts()

        # Ideal distribution for GHZ
        ideal_dist = {"0" * n_qubits: 0.5, "1" * n_qubits: 0.5}

        # Calculate fidelities
        baseline_fid = self._fidelity(baseline_counts, ideal_dist)
        opt_fid = self._fidelity(opt_counts, ideal_dist)

        improvement = ((opt_fid - baseline_fid) / baseline_fid) * 100 if baseline_fid > 0 else 0

        name = "GHZ" if n_qubits > 2 else "Bell"
        return BenchmarkResult(
            circuit_name=name,
            n_qubits=n_qubits,
            noise_type=config["type"],
            noise_strength=config["strength"],
            fidelity_baseline=baseline_fid,
            fidelity_optimized=opt_fid,
            improvement=improvement,
        )

    def _fidelity(self, counts: dict, ideal_dist: dict) -> float:
        """Calculate Hellinger fidelity between measured counts and ideal distribution."""
        total = sum(counts.values())
        measured_dist = {k: v / total for k, v in counts.items()}
        return quantum_info.hellinger_fidelity(ideal_dist, measured_dist)

    def summary(self) -> str:
        """Generate a summary report of all benchmark results."""
        if not self.results:
            return "No results. Run benchmarks first."

        lines = ["=" * 80, "NOISE-AWARE OPTIMIZER BENCHMARK RESULTS", "=" * 80, ""]

        # Group by noise type
        by_type = {}
        for r in self.results:
            by_type.setdefault(r.noise_type, []).append(r)

        for noise_type, results in by_type.items():
            lines.append(f"--- {noise_type.upper()} ---")
            for r in sorted(results, key=lambda x: (x.n_qubits, x.noise_strength)):
                lines.append(str(r))
            lines.append("")

        # Overall stats
        improvements = [r.improvement for r in self.results]
        positive = [i for i in improvements if i > 0]
        lines.append(f"Total benchmarks: {len(self.results)}")
        lines.append(f"Improved: {len(positive)}/{len(self.results)}")
        if improvements:
            lines.append(f"Avg improvement: {np.mean(improvements):+.2f}%")
            lines.append(f"Max improvement: {max(improvements):+.2f}%")

        return "\n".join(lines)
