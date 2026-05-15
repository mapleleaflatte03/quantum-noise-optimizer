"""Circuit optimization passes: rotation merging, gate cancellation, commutation."""

from pyqpanda3 import core
import numpy as np


# Gates that are self-inverse (G·G = I)
SELF_INVERSE_GATES = {
    core.GateType.H, core.GateType.X, core.GateType.Y, core.GateType.Z,
    core.GateType.CNOT, core.GateType.CZ, core.GateType.SWAP,
}

# Rotation gates that can be merged
ROTATION_GATES = {core.GateType.RX, core.GateType.RY, core.GateType.RZ}

# Gates that commute with Z-basis (diagonal gates)
Z_COMMUTING = {core.GateType.RZ, core.GateType.Z, core.GateType.S, core.GateType.T, core.GateType.CZ}


def cancel_inverse_pairs(prog: core.QProg) -> core.QProg:
    """Remove adjacent pairs of self-inverse gates on the same qubits.

    Examples: H·H → I, X·X → I, CNOT·CNOT → I
    """
    ops = prog.operations()
    if not ops:
        return prog

    result = []
    i = 0
    while i < len(ops):
        if i + 1 < len(ops):
            curr = ops[i]
            next_op = ops[i + 1]
            # Check if same gate type, same qubits, and self-inverse
            if (curr.gate_type() == next_op.gate_type()
                    and curr.qubits() == next_op.qubits()
                    and curr.gate_type() in SELF_INVERSE_GATES):
                i += 2  # skip both
                continue
        result.append(ops[i])
        i += 1

    new_prog = core.QProg()
    for op in result:
        new_prog << op
    return new_prog


def merge_rotations(prog: core.QProg) -> core.QProg:
    """Merge adjacent rotation gates of the same type on the same qubit.

    RZ(a)·RZ(b) → RZ(a+b), same for RX, RY.
    Removes gates where merged angle ≈ 0 (mod 2π).
    """
    ops = prog.operations()
    if not ops:
        return prog

    result = []
    i = 0
    while i < len(ops):
        curr = ops[i]
        if curr.gate_type() in ROTATION_GATES:
            # Accumulate consecutive same-type rotations on same qubit
            total_angle = curr.parameters()[0]
            j = i + 1
            while j < len(ops):
                next_op = ops[j]
                if (next_op.gate_type() == curr.gate_type()
                        and next_op.qubits() == curr.qubits()):
                    total_angle += next_op.parameters()[0]
                    j += 1
                else:
                    break

            # Normalize angle to [-π, π]
            total_angle = total_angle % (2 * np.pi)
            if total_angle > np.pi:
                total_angle -= 2 * np.pi

            # Only emit gate if angle is non-trivial
            if abs(total_angle) > 1e-10:
                gt = curr.gate_type()
                q = curr.qubits()[0]
                if gt == core.GateType.RZ:
                    result.append(core.RZ(q, total_angle))
                elif gt == core.GateType.RX:
                    result.append(core.RX(q, total_angle))
                elif gt == core.GateType.RY:
                    result.append(core.RY(q, total_angle))
            i = j
        else:
            result.append(curr)
            i += 1

    new_prog = core.QProg()
    for op in result:
        new_prog << op
    return new_prog


def commute_and_cancel(prog: core.QProg) -> core.QProg:
    """Move commuting gates past each other to enable more cancellations.

    Strategy: If two gates on the same qubit are separated by gates on
    different qubits, swap them to be adjacent, then cancel.
    """
    ops = list(prog.operations())
    if len(ops) < 3:
        return prog

    changed = True
    while changed:
        changed = False
        for i in range(len(ops) - 2):
            curr = ops[i]
            mid = ops[i + 1]
            next_op = ops[i + 2]

            # Check if curr and next_op could cancel
            if (curr.gate_type() == next_op.gate_type()
                    and curr.qubits() == next_op.qubits()
                    and curr.gate_type() in SELF_INVERSE_GATES):
                # Check if mid operates on different qubits (no overlap)
                if not set(curr.qubits()) & set(mid.qubits()):
                    # Commute: swap mid and curr, then curr and next cancel
                    ops[i] = mid
                    ops[i + 1] = curr
                    # Now ops[i+1] and ops[i+2] are adjacent and can cancel
                    changed = True

    # Now run cancellation
    new_prog = core.QProg()
    for op in ops:
        new_prog << op
    return cancel_inverse_pairs(new_prog)


def optimize_circuit(prog: core.QProg, passes: int = 3) -> core.QProg:
    """Run all optimization passes iteratively until convergence.

    Args:
        prog: Input quantum program
        passes: Maximum number of iterations

    Returns:
        Optimized quantum program
    """
    current = prog
    for _ in range(passes):
        prev_count = len(current.operations())

        current = merge_rotations(current)
        current = cancel_inverse_pairs(current)
        current = commute_and_cancel(current)

        new_count = len(current.operations())
        if new_count == prev_count:
            break  # converged

    return current


def count_gates(prog: core.QProg) -> dict:
    """Count gates by type in a program."""
    counts = {}
    for op in prog.operations():
        name = op.name()
        counts[name] = counts.get(name, 0) + 1
    return counts


def circuit_stats(prog: core.QProg) -> dict:
    """Get circuit statistics."""
    ops = prog.operations()
    return {
        "total_gates": len(ops),
        "depth": prog.depth(),
        "qubits": prog.qubits_num(),
        "gate_counts": count_gates(prog),
    }
