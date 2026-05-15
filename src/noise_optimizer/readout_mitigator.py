"""Measurement (readout) error mitigation via confusion matrix inversion."""

from pyqpanda3 import core
import numpy as np
from itertools import product


class ReadoutMitigator:
    """Mitigates measurement errors by characterizing and inverting the confusion matrix.

    Workflow:
    1. Profile readout errors by preparing known states and measuring
    2. Build confusion matrix A where A[i][j] = P(measure i | prepared j)
    3. Apply A^{-1} to raw measurement distributions to get corrected results
    """

    def __init__(self, n_qubits: int, noise_model: core.NoiseModel = None, shots: int = 10000):
        self.n_qubits = n_qubits
        self.noise_model = noise_model
        self.shots = shots
        self.confusion_matrix = None
        self.correction_matrix = None

    def calibrate(self, noise_model: core.NoiseModel = None):
        """Characterize readout errors by preparing computational basis states.

        For n qubits, prepares |0...0> and |1...1> (simplified) or all 2^n states.
        For small n (≤5), profiles all basis states. For larger n, uses tensor product assumption.
        """
        model = noise_model or self.noise_model
        if model is None:
            raise ValueError("No noise model provided")

        if self.n_qubits <= 4:
            self._calibrate_full(model)
        else:
            self._calibrate_tensor(model)

    def _calibrate_full(self, noise_model: core.NoiseModel):
        """Full calibration: prepare each basis state and measure."""
        n = self.n_qubits
        dim = 2 ** n
        self.confusion_matrix = np.zeros((dim, dim))

        for state_idx in range(dim):
            # Prepare basis state
            prog = core.QProg()
            bits = format(state_idx, f'0{n}b')
            for q, b in enumerate(bits):
                if b == '1':
                    prog << core.X(q)
            prog << core.measure(list(range(n)), list(range(n)))

            # Measure with noise
            machine = core.CPUQVM()
            machine.run(prog, shots=self.shots, model=noise_model)
            counts = machine.result().get_counts()

            # Fill column of confusion matrix
            total = sum(counts.values())
            for bitstring, count in counts.items():
                measured_idx = int(bitstring, 2)
                self.confusion_matrix[measured_idx][state_idx] = count / total

        # Compute correction (pseudo-inverse for numerical stability)
        self.correction_matrix = np.linalg.pinv(self.confusion_matrix)

    def _calibrate_tensor(self, noise_model: core.NoiseModel):
        """Tensor product calibration: profile each qubit independently."""
        n = self.n_qubits
        qubit_matrices = []

        for q in range(n):
            mat = np.zeros((2, 2))
            for prep in [0, 1]:
                prog = core.QProg()
                if prep == 1:
                    prog << core.X(q)
                prog << core.measure([q], [0])

                machine = core.CPUQVM()
                machine.run(prog, shots=self.shots, model=noise_model)
                counts = machine.result().get_counts()
                total = sum(counts.values())
                mat[0][prep] = counts.get('0', 0) / total
                mat[1][prep] = counts.get('1', 0) / total
            qubit_matrices.append(mat)

        # Build full confusion matrix as tensor product
        self.confusion_matrix = qubit_matrices[0]
        for mat in qubit_matrices[1:]:
            self.confusion_matrix = np.kron(self.confusion_matrix, mat)

        self.correction_matrix = np.linalg.pinv(self.confusion_matrix)

    def mitigate(self, counts: dict) -> dict:
        """Apply readout error correction to measurement counts.

        Args:
            counts: Raw measurement counts dict (e.g., {'00': 4500, '11': 5500})

        Returns:
            Corrected probability distribution (may have small negative values, clipped to 0)
        """
        if self.correction_matrix is None:
            raise RuntimeError("Must call calibrate() before mitigate()")

        n = self.n_qubits
        dim = 2 ** n

        # Convert counts to probability vector
        total = sum(counts.values())
        prob_vec = np.zeros(dim)
        for bitstring, count in counts.items():
            idx = int(bitstring, 2)
            prob_vec[idx] = count / total

        # Apply correction
        corrected = self.correction_matrix @ prob_vec

        # Clip negatives and renormalize
        corrected = np.maximum(corrected, 0)
        corrected_sum = corrected.sum()
        if corrected_sum > 0:
            corrected /= corrected_sum

        # Convert back to dict
        result = {}
        for idx in range(dim):
            if corrected[idx] > 1e-10:
                bitstring = format(idx, f'0{n}b')
                result[bitstring] = corrected[idx]

        return result
