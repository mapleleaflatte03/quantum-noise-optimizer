"""Adaptive Dynamical Decoupling for Qiskit circuits.

Ports the pyqpanda3 DD module to Qiskit, leveraging Qiskit's built-in
PadDynamicalDecoupling transpiler pass for proper idle-period detection.

Sequences supported:
- XY4: X·Y·X·Y (general dephasing protection, default)
- XX: X·X (pure Z-noise protection)
- CPMG: repeated X pulses (T2 extension)
"""

from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import XGate, YGate
from qiskit.transpiler import PassManager, InstructionDurations
from qiskit.transpiler.passes import ALAPScheduleAnalysis, PadDynamicalDecoupling
from qiskit_aer import AerSimulator
import numpy as np

# Default gate durations in dt units (typical superconducting qubit timings)
DEFAULT_DURATIONS = InstructionDurations([
    ('h', None, 50), ('x', None, 50), ('y', None, 50),
    ('z', None, 0), ('s', None, 0), ('t', None, 0),
    ('rx', None, 50), ('ry', None, 50), ('rz', None, 0),
    ('cx', None, 300), ('cz', None, 300), ('sx', None, 50),
    ('measure', None, 1000), ('reset', None, 200), ('id', None, 50),
], dt=1.0)


DD_SEQUENCES = {
    'XY4': [XGate(), YGate(), XGate(), YGate()],
    'XX': [XGate(), XGate()],
    'CPMG': [XGate(), XGate()],
}


class AdaptiveDDQiskit:
    """Adaptive Dynamical Decoupling for Qiskit circuits.

    Selects DD sequence based on noise characteristics:
    - XY4 for general dephasing (default)
    - XX for pure Z-noise
    - CPMG for T2 extension
    """

    def __init__(self, sequence='auto', noise_profile=None):
        self.noise_profile = noise_profile
        self.sequence = self._select_sequence(sequence, noise_profile)

    def _select_sequence(self, sequence, noise_profile):
        if sequence != 'auto':
            if sequence not in DD_SEQUENCES:
                raise ValueError(f"Unknown sequence: {sequence}. Use: {list(DD_SEQUENCES.keys())}")
            return sequence
        if noise_profile is None:
            return 'XY4'
        noise_type = noise_profile.get('dominant_noise', 'dephasing')
        if noise_type == 'z_noise':
            return 'XX'
        elif noise_type == 't2_decay':
            return 'CPMG'
        return 'XY4'

    def insert_dd(self, circuit: QuantumCircuit) -> QuantumCircuit:
        """Insert DD sequences during idle periods using Qiskit's PadDynamicalDecoupling pass."""
        # Transpile to basis gates
        t_circ = transpile(circuit, basis_gates=['x', 'y', 'z', 'h', 'cx', 'rz', 'sx'],
                           optimization_level=1)
        # Apply scheduling + DD padding
        dd_sequence = DD_SEQUENCES[self.sequence]
        pm = PassManager([
            ALAPScheduleAnalysis(durations=DEFAULT_DURATIONS),
            PadDynamicalDecoupling(durations=DEFAULT_DURATIONS, dd_sequence=dd_sequence),
        ])
        return pm.run(t_circ)

    def estimate_benefit(self, circuit, noise_model, shots=4096) -> dict:
        """Run with and without DD, compare fidelity."""
        backend = AerSimulator(noise_model=noise_model)

        # Get ideal distribution
        ideal_backend = AerSimulator()
        circ_meas = circuit.copy()
        if not circ_meas.cregs:
            circ_meas.measure_all()
        ideal_t = transpile(circ_meas, backend=ideal_backend, optimization_level=1)
        ideal_result = ideal_backend.run(ideal_t, shots=shots).result()
        ideal_counts = ideal_result.get_counts()

        # Without DD
        noisy_t = transpile(circ_meas, backend=backend, optimization_level=1)
        noisy_result = backend.run(noisy_t, shots=shots).result()
        counts_no_dd = noisy_result.get_counts()

        # With DD
        dd_circ = self.insert_dd(circ_meas)
        dd_result = backend.run(dd_circ, shots=shots).result()
        counts_with_dd = dd_result.get_counts()

        # Compute Hellinger fidelity
        fid_no_dd = self._hellinger_fidelity(ideal_counts, counts_no_dd)
        fid_with_dd = self._hellinger_fidelity(ideal_counts, counts_with_dd)

        improvement = ((fid_with_dd - fid_no_dd) / fid_no_dd * 100) if fid_no_dd > 0 else 0.0
        return {
            'without_dd': fid_no_dd,
            'with_dd': fid_with_dd,
            'improvement_pct': improvement,
            'sequence_used': self.sequence,
        }

    @staticmethod
    def _hellinger_fidelity(counts1, counts2):
        """Compute Hellinger fidelity between two count distributions."""
        all_keys = set(counts1) | set(counts2)
        total1 = sum(counts1.values())
        total2 = sum(counts2.values())
        fid = sum(
            np.sqrt((counts1.get(k, 0) / total1) * (counts2.get(k, 0) / total2))
            for k in all_keys
        )
        return fid ** 2
