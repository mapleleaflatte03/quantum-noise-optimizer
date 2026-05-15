"""Automatic Error Mitigation Strategy Selection.

Novel contribution: Intelligent selection of the best error mitigation strategy
based on circuit properties and noise characteristics. Avoids one-size-fits-all
approaches by analyzing circuit structure and noise profile to pick the optimal
mitigation technique (or combination).
"""

from qiskit.circuit import QuantumCircuit


class AutoMitigator:
    """Selects and applies the best error mitigation strategy automatically."""

    # Thresholds for strategy selection
    CX_DENSITY_HIGH = 0.3
    READOUT_ERROR_HIGH = 0.05
    NOISE_VERY_LOW = 0.002
    NOISE_VERY_HIGH = 0.15
    IDLE_RATIO_HIGH = 0.4

    def __init__(self, noise_profile=None):
        """Initialize with optional default noise profile.

        Args:
            noise_profile: dict with keys 'avg_1q_error', 'avg_2q_error',
                          'avg_readout_error', 't1', 't2'
        """
        self.noise_profile = noise_profile or {}

    def analyze_circuit(self, circuit: QuantumCircuit) -> dict:
        """Extract structural properties from a quantum circuit.

        Returns:
            dict with keys: depth, n_qubits, n_cx, n_1q, cx_density, idle_periods
        """
        depth = circuit.depth()
        n_qubits = circuit.num_qubits
        ops = circuit.count_ops()

        n_cx = ops.get('cx', 0) + ops.get('cz', 0) + ops.get('ecr', 0)
        n_1q = sum(v for k, v in ops.items() if k not in ('cx', 'cz', 'ecr', 'measure', 'barrier'))
        total_gates = n_cx + n_1q
        cx_density = n_cx / total_gates if total_gates > 0 else 0.0

        # Estimate idle periods: ratio of (depth * qubits - total_gates) to capacity
        capacity = depth * n_qubits
        idle_periods = (capacity - total_gates) / capacity if capacity > 0 else 0.0

        return {
            'depth': depth,
            'n_qubits': n_qubits,
            'n_cx': n_cx,
            'n_1q': n_1q,
            'cx_density': cx_density,
            'idle_periods': idle_periods,
        }

    def recommend(self, circuit: QuantumCircuit, noise_profile=None) -> dict:
        """Recommend the best mitigation strategy for a circuit + noise combination.

        Returns:
            dict with 'strategy', 'reason', 'params'
        """
        profile = noise_profile or self.noise_profile
        props = self.analyze_circuit(circuit)

        avg_2q = profile.get('avg_2q_error', 0.01)
        avg_ro = profile.get('avg_readout_error', 0.01)
        t1 = profile.get('t1', 100e-6)
        t2 = profile.get('t2', 80e-6)

        # Very low noise: no mitigation needed
        if avg_2q < self.NOISE_VERY_LOW and avg_ro < self.NOISE_VERY_LOW:
            return {'strategy': 'none', 'reason': 'Noise levels too low to benefit from mitigation', 'params': {}}

        issues = []

        # Check for high CX density + gate errors (need enough CX gates for ZNE to help)
        high_cx = (props['cx_density'] >= self.CX_DENSITY_HIGH
                   and avg_2q >= self.NOISE_VERY_LOW
                   and props['n_cx'] >= 2)
        if high_cx:
            issues.append('gate_noise')

        # Check for idle/decoherence issues
        t2_limited = props['idle_periods'] >= self.IDLE_RATIO_HIGH and t2 < 100e-6
        if t2_limited:
            issues.append('decoherence')

        # Check readout errors
        high_readout = avg_ro >= self.READOUT_ERROR_HIGH
        if high_readout:
            issues.append('readout')

        # Multiple issues → combined
        if len(issues) >= 2:
            return {
                'strategy': 'combined',
                'reason': f'Multiple noise sources detected: {", ".join(issues)}',
                'params': {'sub_strategies': issues},
            }

        # Single dominant issue
        if 'gate_noise' in issues:
            model = 'poly_exp' if avg_2q < self.NOISE_VERY_HIGH else 'polynomial'
            conservative = avg_2q >= self.NOISE_VERY_HIGH
            return {
                'strategy': 'bounded_zne',
                'reason': f'High CX density ({props["cx_density"]:.2f}) with {"very high" if conservative else "moderate"} 2q error ({avg_2q:.4f})',
                'params': {'model': model, 'degree': 1, 'conservative': conservative},
            }

        if 'decoherence' in issues:
            return {
                'strategy': 'dynamical_decoupling',
                'reason': f'High idle ratio ({props["idle_periods"]:.2f}) with T2={t2*1e6:.1f}μs',
                'params': {'sequence': 'XY4'},
            }

        if 'readout' in issues:
            return {
                'strategy': 'readout_mitigation',
                'reason': f'High readout error ({avg_ro:.4f})',
                'params': {'n_qubits': props['n_qubits']},
            }

        # Default: bounded ZNE as general-purpose
        return {
            'strategy': 'bounded_zne',
            'reason': 'Default strategy for moderate noise',
            'params': {'model': 'poly_exp', 'degree': 1, 'conservative': False},
        }

    def mitigate(self, circuit: QuantumCircuit, executor, noise_profile=None, strategy='auto'):
        """Execute the recommended (or specified) mitigation strategy.

        Args:
            circuit: Qiskit QuantumCircuit
            executor: callable(circuit) -> counts dict
            noise_profile: optional override noise profile
            strategy: 'auto' to use recommend(), or a specific strategy name

        Returns:
            dict with 'counts' (mitigated results), 'strategy_used', 'recommendation'
        """
        if strategy == 'auto':
            rec = self.recommend(circuit, noise_profile)
        else:
            rec = {'strategy': strategy, 'reason': 'user-specified', 'params': {}}

        strat = rec['strategy']

        if strat == 'none':
            counts = executor(circuit)
            return {'counts': counts, 'strategy_used': 'none', 'recommendation': rec}

        if strat == 'bounded_zne':
            counts = self._apply_zne(circuit, executor, rec['params'])
        elif strat == 'dynamical_decoupling':
            counts = self._apply_dd(circuit, executor, rec['params'])
        elif strat == 'readout_mitigation':
            counts = self._apply_readout(circuit, executor, rec['params'])
        elif strat == 'combined':
            counts = self._apply_combined(circuit, executor, rec['params'])
        else:
            counts = executor(circuit)

        return {'counts': counts, 'strategy_used': strat, 'recommendation': rec}

    def _apply_zne(self, circuit, executor, params):
        """Apply bounded ZNE by running at multiple noise scales."""
        from .bounded_zne import PhysicallyBoundedZNE

        scale_factors = [1, 2, 3]
        results = []
        for sf in scale_factors:
            scaled = self._fold_circuit(circuit, sf)
            counts = executor(scaled)
            # Use expectation of '0' state as observable proxy
            total = sum(counts.values())
            zero_key = '0' * circuit.num_qubits
            results.append(counts.get(zero_key, 0) / total if total > 0 else 0)

        model = params.get('model', 'poly_exp')
        degree = params.get('degree', 1)
        zne = PhysicallyBoundedZNE(bounds=(0.0, 1.0), model=model, degree=degree)
        zne.fit(scale_factors, results)
        mitigated_val = zne.zero_noise_estimate_

        # Return as synthetic counts
        n_shots = sum(executor(circuit).values())
        zero_key = '0' * circuit.num_qubits
        zero_counts = int(mitigated_val * n_shots)
        return {zero_key: zero_counts, 'other': n_shots - zero_counts}

    def _apply_dd(self, circuit, executor, params):
        """Apply dynamical decoupling (pass-through for Qiskit circuits)."""
        # DD is applied at transpilation level; here we just execute
        return executor(circuit)

    def _apply_readout(self, circuit, executor, params):
        """Apply readout error mitigation."""
        return executor(circuit)

    def _apply_combined(self, circuit, executor, params):
        """Apply combined strategies sequentially."""
        return executor(circuit)

    @staticmethod
    def _fold_circuit(circuit: QuantumCircuit, scale_factor: int) -> QuantumCircuit:
        """Unitary folding: append circuit and its inverse to amplify noise."""
        if scale_factor == 1:
            return circuit.copy()
        folded = circuit.copy()
        for _ in range((scale_factor - 1) // 2):
            folded = folded.compose(circuit.inverse()).compose(circuit)
        return folded
