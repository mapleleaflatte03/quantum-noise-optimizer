"""Calibration-Aware Qubit Selection for Origin Wukong 180.

Uses real hardware calibration data (T1, T2, gate fidelity, readout fidelity,
CZ gate fidelity) to select optimal qubits and routing paths.

This is the key differentiator: physics-informed decisions based on REAL
hardware characteristics, not generic heuristics.
"""

import json
import numpy as np
from pathlib import Path


class HardwareCalibration:
    """Loads and queries real hardware calibration data."""

    def __init__(self, calibration_path: str = None):
        if calibration_path is None:
            calibration_path = str(Path(__file__).parent.parent.parent / "results" / "wukong180_calibration.json")
        with open(calibration_path) as f:
            self.data = json.load(f)
        self.qubits = self.data["single_qubits"]
        self.cz_gates = self.data["two_qubit_gates"]
        self._build_connectivity()

    def _build_connectivity(self):
        """Build adjacency map from CZ gate data."""
        self.adjacency = {}  # qubit_id -> [(neighbor_id, cz_fidelity), ...]
        for gate in self.cz_gates:
            q0, q1 = gate["qubits"]
            fid = gate["CZ_fidelity"]
            self.adjacency.setdefault(str(q0), []).append((str(q1), fid))
            self.adjacency.setdefault(str(q1), []).append((str(q0), fid))

    def qubit_score(self, qubit_id: str, weights: dict = None) -> float:
        """Score a qubit based on calibration metrics.

        Higher = better. Weights control importance of each metric.
        """
        if weights is None:
            weights = {"T2": 0.3, "readout": 0.4, "gate": 0.2, "T1": 0.1}

        q = self.qubits.get(str(qubit_id))
        if not q:
            return 0.0

        # Normalize each metric to [0, 1]
        all_t2 = [v["T2_us"] for v in self.qubits.values()]
        all_ro = [v["readout_fidelity"] for v in self.qubits.values()]
        all_t1 = [v["T1_us"] for v in self.qubits.values()]

        t2_norm = q["T2_us"] / max(all_t2) if max(all_t2) > 0 else 0
        t1_norm = q["T1_us"] / max(all_t1) if max(all_t1) > 0 else 0
        ro_norm = q["readout_fidelity"]
        gate_norm = q["gate_fidelity"]

        return (weights["T2"] * t2_norm + weights["readout"] * ro_norm +
                weights["gate"] * gate_norm + weights["T1"] * t1_norm)

    def best_qubits(self, n: int, connected: bool = True) -> list:
        """Select the n best qubits, optionally requiring connectivity.

        If connected=True, finds the best connected subgraph of size n.
        """
        if not connected:
            scored = [(qid, self.qubit_score(qid)) for qid in self.qubits]
            scored.sort(key=lambda x: -x[1])
            return [qid for qid, _ in scored[:n]]

        # Greedy: start from best qubit, expand to best neighbors
        scored = [(qid, self.qubit_score(qid)) for qid in self.qubits]
        scored.sort(key=lambda x: -x[1])

        selected = [scored[0][0]]
        for _ in range(n - 1):
            best_next = None
            best_score = -1
            for q in selected:
                for neighbor, cz_fid in self.adjacency.get(q, []):
                    if neighbor not in selected and neighbor in self.qubits:
                        # Combined score: qubit quality + CZ gate quality
                        score = self.qubit_score(neighbor) * 0.7 + cz_fid * 0.3
                        if score > best_score:
                            best_score = score
                            best_next = neighbor
            if best_next:
                selected.append(best_next)
            else:
                break

        return selected

    def best_path(self, n_qubits: int) -> list:
        """Find the best linear chain of n qubits (for GHZ-like circuits).

        Optimizes for: high qubit quality + high CZ fidelity along the chain.
        """
        best_chain = None
        best_score = -1

        # Try starting from top-scored qubits
        scored = [(qid, self.qubit_score(qid)) for qid in self.qubits]
        scored.sort(key=lambda x: -x[1])

        for start_qid, _ in scored[:20]:  # Try top 20 starting points
            chain = [start_qid]
            visited = {start_qid}

            for _ in range(n_qubits - 1):
                best_next = None
                best_edge_score = -1
                for neighbor, cz_fid in self.adjacency.get(chain[-1], []):
                    if neighbor not in visited and neighbor in self.qubits:
                        edge_score = cz_fid * self.qubit_score(neighbor)
                        if edge_score > best_edge_score:
                            best_edge_score = edge_score
                            best_next = neighbor
                if best_next:
                    chain.append(best_next)
                    visited.add(best_next)
                else:
                    break

            if len(chain) == n_qubits:
                # Score entire chain
                chain_score = sum(self.qubit_score(q) for q in chain) / n_qubits
                for i in range(len(chain) - 1):
                    # Add CZ fidelity between consecutive qubits
                    for neighbor, fid in self.adjacency.get(chain[i], []):
                        if neighbor == chain[i + 1]:
                            chain_score += fid * 0.5
                            break

                if chain_score > best_score:
                    best_score = chain_score
                    best_chain = chain

        return best_chain or []

    def report(self, qubits: list) -> str:
        """Generate a report for selected qubits."""
        lines = ["Selected Qubits Report:", "=" * 50]
        for qid in qubits:
            q = self.qubits.get(str(qid), {})
            lines.append(
                f"  Q{qid}: T1={q.get('T1_us', 0):.1f}μs, T2={q.get('T2_us', 0):.1f}μs, "
                f"gate={q.get('gate_fidelity', 0):.4f}, readout={q.get('readout_fidelity', 0):.4f}"
            )
        # CZ fidelities between consecutive pairs
        for i in range(len(qubits) - 1):
            for neighbor, fid in self.adjacency.get(str(qubits[i]), []):
                if neighbor == str(qubits[i + 1]):
                    lines.append(f"  CZ({qubits[i]},{qubits[i+1]}): fidelity={fid:.4f}")
                    break
        return "\n".join(lines)
