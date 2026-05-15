"""Noise-Aware Quantum Circuit Optimizer built on pyqpanda3."""

from .noise_profiler import NoiseProfiler
from .optimizer import NoiseAwareOptimizer
from .benchmark import Benchmark
from .circuit_passes import (
    optimize_circuit,
    merge_rotations,
    cancel_inverse_pairs,
    commute_and_cancel,
    circuit_stats,
)
from .readout_mitigator import ReadoutMitigator
from .zne import ZeroNoiseExtrapolator
from .qasm import from_qasm, to_qasm, from_qasm_file
from .dynamical_decoupling import insert_dd, estimate_dd_benefit
from .visualization import noise_heatmap, fidelity_vs_depth, print_noise_report

__version__ = "0.3.0"
__all__ = [
    "NoiseProfiler", "NoiseAwareOptimizer", "Benchmark",
    "optimize_circuit", "merge_rotations", "cancel_inverse_pairs",
    "commute_and_cancel", "circuit_stats", "ReadoutMitigator",
    "ZeroNoiseExtrapolator", "from_qasm", "to_qasm", "from_qasm_file",
    "insert_dd", "estimate_dd_benefit",
    "noise_heatmap", "fidelity_vs_depth", "print_noise_report",
]
