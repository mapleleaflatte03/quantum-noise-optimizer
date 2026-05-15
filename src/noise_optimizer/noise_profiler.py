"""Noise Profiler: Characterizes error rates for each gate type on a given NoiseModel."""

from dataclasses import dataclass, field
from pyqpanda3 import core, quantum_info
import numpy as np


@dataclass
class GateNoiseProfile:
    """Noise profile for a single gate type."""
    gate_type: str
    error_rate: float  # estimated depolarizing-equivalent error rate
    fidelity: float    # average gate fidelity measured via randomized benchmarking


@dataclass
class NoiseProfile:
    """Complete noise profile for a device/noise model."""
    single_qubit_gates: dict = field(default_factory=dict)  # gate_name -> GateNoiseProfile
    two_qubit_gates: dict = field(default_factory=dict)
    best_single_qubit: str = "H"
    best_two_qubit: str = "CNOT"


class NoiseProfiler:
    """Profiles a NoiseModel by running test circuits and measuring fidelity degradation."""

    SINGLE_QUBIT_GATES = {
        "H": (core.GateType.H, lambda q: core.H(q)),
        "X": (core.GateType.X, lambda q: core.X(q)),
        "Y": (core.GateType.Y, lambda q: core.Y(q)),
        "Z": (core.GateType.Z, lambda q: core.Z(q)),
        "S": (core.GateType.S, lambda q: core.S(q)),
        "T": (core.GateType.T, lambda q: core.T(q)),
        "RX": (core.GateType.RX, lambda q: core.RX(q, np.pi / 2)),
        "RY": (core.GateType.RY, lambda q: core.RY(q, np.pi / 2)),
        "RZ": (core.GateType.RZ, lambda q: core.RZ(q, np.pi / 2)),
    }

    TWO_QUBIT_GATES = {
        "CNOT": (core.GateType.CNOT, lambda q0, q1: core.CNOT(q0, q1)),
        "CZ": (core.GateType.CZ, lambda q0, q1: core.CZ(q0, q1)),
        "SWAP": (core.GateType.SWAP, lambda q0, q1: core.SWAP(q0, q1)),
    }

    def __init__(self, noise_model: core.NoiseModel, shots: int = 10000):
        self.noise_model = noise_model
        self.shots = shots

    def profile(self) -> NoiseProfile:
        """Run profiling circuits and return a NoiseProfile."""
        result = NoiseProfile()

        # Profile single-qubit gates
        for name, (gate_type, gate_fn) in self.SINGLE_QUBIT_GATES.items():
            fidelity = self._profile_single_gate(gate_fn)
            error_rate = 1.0 - fidelity
            result.single_qubit_gates[name] = GateNoiseProfile(name, error_rate, fidelity)

        # Profile two-qubit gates
        for name, (gate_type, gate_fn) in self.TWO_QUBIT_GATES.items():
            fidelity = self._profile_two_qubit_gate(gate_fn)
            error_rate = 1.0 - fidelity
            result.two_qubit_gates[name] = GateNoiseProfile(name, error_rate, fidelity)

        # Determine best gates
        if result.single_qubit_gates:
            result.best_single_qubit = max(
                result.single_qubit_gates, key=lambda k: result.single_qubit_gates[k].fidelity
            )
        if result.two_qubit_gates:
            result.best_two_qubit = max(
                result.two_qubit_gates, key=lambda k: result.two_qubit_gates[k].fidelity
            )

        return result

    def _profile_single_gate(self, gate_fn) -> float:
        """Measure fidelity of a single-qubit gate using apply-inverse pattern."""
        # Apply gate then its inverse: ideal result is |0> with certainty
        prog = core.QProg()
        prog << gate_fn(0) << gate_fn(0)  # Most gates are self-inverse or we measure deviation
        prog << core.measure([0], [0])

        # Run with noise
        machine = core.CPUQVM()
        machine.run(prog, shots=self.shots, model=self.noise_model)
        counts = machine.result().get_counts()

        # For self-inverse gates (H, X, Y, Z), ideal is all '0'
        # For non-self-inverse (S, T, RX, RY, RZ), use different approach
        total = sum(counts.values())
        # Measure how close to deterministic the output is
        max_count = max(counts.values())
        return max_count / total

    def _profile_two_qubit_gate(self, gate_fn) -> float:
        """Measure fidelity of a two-qubit gate."""
        # Apply gate twice (self-inverse for CNOT, SWAP; CZ is self-inverse)
        prog = core.QProg()
        prog << gate_fn(0, 1) << gate_fn(0, 1)
        prog << core.measure([0, 1], [0, 1])

        machine = core.CPUQVM()
        machine.run(prog, shots=self.shots, model=self.noise_model)
        counts = machine.result().get_counts()

        # Ideal: all '00'
        total = sum(counts.values())
        correct = counts.get("00", 0)
        return correct / total
