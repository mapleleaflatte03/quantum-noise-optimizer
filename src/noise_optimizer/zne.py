"""Zero-Noise Extrapolation (ZNE): Extrapolate expectation values to the zero-noise limit.

Technique: Run circuit at multiple noise levels by inserting gate folding (G·G†·G),
then extrapolate to the zero-noise limit using polynomial fitting.
"""

from pyqpanda3 import core, quantum_info
import numpy as np


class ZeroNoiseExtrapolator:
    """Implements Zero-Noise Extrapolation via unitary folding.

    Noise is scaled by inserting G·G†·G sequences (gate folding),
    which increases the effective noise by a factor proportional to
    the number of folds while preserving the ideal unitary.
    """

    def __init__(self, scale_factors: list[float] = None, fit_method: str = "linear"):
        """
        Args:
            scale_factors: Noise scale factors (e.g., [1, 2, 3]). Must include 1.
            fit_method: "linear", "quadratic", or "exponential"
        """
        self.scale_factors = scale_factors or [1.0, 2.0, 3.0]
        self.fit_method = fit_method

    def mitigate_expectation(self, prog: core.QProg, noise_model: core.NoiseModel,
                             n_qubits: int, shots: int = 10000) -> dict:
        """Run ZNE and return the extrapolated probability distribution.

        Args:
            prog: Circuit WITHOUT measurement (we add measurement internally)
            noise_model: The base noise model
            n_qubits: Number of qubits
            shots: Shots per noise level

        Returns:
            Dict with 'raw' (scale=1), 'extrapolated', and 'scale_results' data
        """
        scale_results = {}

        for scale in self.scale_factors:
            folded = self._fold_circuit(prog, scale)
            # Add measurement
            meas_prog = core.QProg()
            meas_prog << folded
            meas_prog << core.measure(list(range(n_qubits)), list(range(n_qubits)))

            machine = core.CPUQVM()
            machine.run(meas_prog, shots=shots, model=noise_model)
            counts = machine.result().get_counts()
            total = sum(counts.values())
            dist = {k: v / total for k, v in counts.items()}
            scale_results[scale] = dist

        # Extrapolate each bitstring probability to zero noise
        extrapolated = self._extrapolate(scale_results, n_qubits)

        return {
            "raw": scale_results.get(1.0, {}),
            "extrapolated": extrapolated,
            "scale_results": scale_results,
        }

    def _fold_circuit(self, prog: core.QProg, scale_factor: float) -> core.QProg:
        """Apply global unitary folding to scale noise.

        For scale_factor=1: original circuit
        For scale_factor=3: G · G† · G (full fold)
        For scale_factor=2: partial fold (fold subset of gates)
        """
        ops = prog.operations()
        if not ops:
            return prog

        if scale_factor <= 1.0:
            return prog

        result = core.QProg()

        # Number of full folds needed
        n_full_folds = int((scale_factor - 1) / 2)
        # Remaining partial fold
        remainder = (scale_factor - 1) - 2 * n_full_folds
        n_partial_gates = int(remainder / 2 * len(ops))

        # Original circuit
        for op in ops:
            result << op

        # Full folds: append G† · G for each full fold
        for _ in range(n_full_folds):
            # G† (reverse order, dagger each gate)
            for op in reversed(ops):
                result << op.dagger()
            # G again
            for op in ops:
                result << op

        # Partial fold: fold only first n_partial_gates
        if n_partial_gates > 0:
            partial_ops = ops[:n_partial_gates]
            for op in reversed(partial_ops):
                result << op.dagger()
            for op in partial_ops:
                result << op

        return result

    def _extrapolate(self, scale_results: dict, n_qubits: int) -> dict:
        """Extrapolate probability distributions to zero noise."""
        # Collect all bitstrings
        all_bitstrings = set()
        for dist in scale_results.values():
            all_bitstrings.update(dist.keys())

        scales = sorted(scale_results.keys())
        extrapolated = {}

        for bitstring in all_bitstrings:
            # Get probability at each scale
            probs = [scale_results[s].get(bitstring, 0.0) for s in scales]

            # Extrapolate to scale=0
            if self.fit_method == "linear":
                zero_val = self._linear_extrapolate(scales, probs)
            elif self.fit_method == "quadratic":
                zero_val = self._poly_extrapolate(scales, probs, degree=2)
            elif self.fit_method == "exponential":
                zero_val = self._exp_extrapolate(scales, probs)
            else:
                zero_val = self._linear_extrapolate(scales, probs)

            extrapolated[bitstring] = zero_val

        # Clip and renormalize
        extrapolated = {k: max(v, 0) for k, v in extrapolated.items()}
        total = sum(extrapolated.values())
        if total > 0:
            extrapolated = {k: v / total for k, v in extrapolated.items()}

        # Remove near-zero entries
        extrapolated = {k: v for k, v in extrapolated.items() if v > 1e-6}
        return extrapolated

    @staticmethod
    def _linear_extrapolate(scales, probs):
        """Linear extrapolation to scale=0."""
        if len(scales) < 2:
            return probs[0]
        coeffs = np.polyfit(scales, probs, 1)
        return np.polyval(coeffs, 0)

    @staticmethod
    def _poly_extrapolate(scales, probs, degree=2):
        """Polynomial extrapolation to scale=0."""
        degree = min(degree, len(scales) - 1)
        coeffs = np.polyfit(scales, probs, degree)
        return np.polyval(coeffs, 0)

    @staticmethod
    def _exp_extrapolate(scales, probs):
        """Exponential extrapolation: fit a*exp(b*x) + c."""
        # Fallback to linear if probs have zeros
        probs_arr = np.array(probs)
        if np.any(probs_arr <= 0):
            return ZeroNoiseExtrapolator._linear_extrapolate(scales, probs)
        try:
            log_probs = np.log(probs_arr)
            coeffs = np.polyfit(scales, log_probs, 1)
            return np.exp(np.polyval(coeffs, 0))
        except (ValueError, np.linalg.LinAlgError):
            return ZeroNoiseExtrapolator._linear_extrapolate(scales, probs)
