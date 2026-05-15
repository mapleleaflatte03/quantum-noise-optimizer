"""Dynamical Decoupling: Insert identity-equivalent pulse sequences during idle periods.

Physics: During idle time, qubits decohere due to coupling with the environment.
DD sequences (rapid pi-pulses) refocus this dephasing, effectively extending T2.

Sequences supported:
- XX: X·X (basic echo, protects against Z-noise/dephasing)
- XY4: X·Y·X·Y (protects against both X and Z noise)
- CPMG: repeated X pulses (optimized for T2 extension)
"""

from pyqpanda3 import core


# DD sequences (all equivalent to identity up to global phase)
DD_SEQUENCES = {
    "XX": lambda q: [core.X(q), core.X(q)],
    "XY4": lambda q: [core.X(q), core.Y(q), core.X(q), core.Y(q)],
}


def insert_dd(prog: core.QProg, sequence: str = "XY4") -> core.QProg:
    """Insert dynamical decoupling sequences during idle periods.

    Identifies qubits that are idle (not acted on) while other qubits
    have gates, and inserts DD sequences to suppress decoherence.

    Args:
        prog: Input quantum program
        sequence: DD sequence type ("XX" or "XY4")

    Returns:
        New QProg with DD sequences inserted
    """
    if sequence not in DD_SEQUENCES:
        raise ValueError(f"Unknown DD sequence: {sequence}. Use: {list(DD_SEQUENCES.keys())}")

    ops = prog.operations()
    if not ops:
        return prog

    # Find all qubits used
    all_qubits = set()
    for op in ops:
        all_qubits.update(op.qubits())

    if not all_qubits:
        return prog

    # Build time slots: group operations that can run in parallel
    # Simple heuristic: each op is one time step, find idle qubits per step
    result = core.QProg()
    dd_fn = DD_SEQUENCES[sequence]

    for op in ops:
        active_qubits = set(op.qubits())
        idle_qubits = all_qubits - active_qubits

        # Insert DD on idle qubits (only for two-qubit gates where idle time is significant)
        if len(op.qubits()) >= 2:
            for q in idle_qubits:
                for gate in dd_fn(q):
                    result << gate

        result << op

    return result


def estimate_dd_benefit(prog: core.QProg, noise_model: core.NoiseModel,
                        n_qubits: int, sequence: str = "XY4", shots: int = 10000) -> dict:
    """Estimate the fidelity benefit of DD insertion.

    Returns dict with 'without_dd' and 'with_dd' fidelity estimates.
    """
    from pyqpanda3 import quantum_info

    # Run without DD
    prog_no_dd = core.QProg()
    prog_no_dd << prog << core.measure(list(range(n_qubits)), list(range(n_qubits)))
    m1 = core.CPUQVM()
    m1.run(prog_no_dd, shots=shots, model=noise_model)
    counts_no_dd = m1.result().get_counts()

    # Run with DD
    dd_prog = insert_dd(prog, sequence)
    prog_with_dd = core.QProg()
    prog_with_dd << dd_prog << core.measure(list(range(n_qubits)), list(range(n_qubits)))
    m2 = core.CPUQVM()
    m2.run(prog_with_dd, shots=shots, model=noise_model)
    counts_with_dd = m2.result().get_counts()

    # Get ideal
    m_ideal = core.CPUQVM()
    m_ideal.run(prog_no_dd, shots=shots)
    ideal_counts = m_ideal.result().get_counts()
    total_ideal = sum(ideal_counts.values())
    ideal_dist = {k: v / total_ideal for k, v in ideal_counts.items()}

    # Fidelities
    total1 = sum(counts_no_dd.values())
    total2 = sum(counts_with_dd.values())
    dist1 = {k: v / total1 for k, v in counts_no_dd.items()}
    dist2 = {k: v / total2 for k, v in counts_with_dd.items()}

    fid_no_dd = quantum_info.hellinger_fidelity(ideal_dist, dist1)
    fid_with_dd = quantum_info.hellinger_fidelity(ideal_dist, dist2)

    return {
        "without_dd": fid_no_dd,
        "with_dd": fid_with_dd,
        "improvement_pct": ((fid_with_dd - fid_no_dd) / fid_no_dd) * 100 if fid_no_dd > 0 else 0,
    }
