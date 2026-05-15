"""QASM import/export: Convert between OpenQASM 2.0 and pyqpanda3 QProg."""

from pyqpanda3 import core, intermediate_compiler


def from_qasm(qasm_string: str) -> core.QProg:
    """Import a circuit from an OpenQASM 2.0 string."""
    return intermediate_compiler.convert_qasm_string_to_qprog(qasm_string)


def to_qasm(prog: core.QProg) -> str:
    """Export a circuit to OpenQASM 2.0 string."""
    return intermediate_compiler.convert_qprog_to_qasm(prog)


def from_qasm_file(filepath: str) -> core.QProg:
    """Import a circuit from an OpenQASM 2.0 file."""
    return intermediate_compiler.convert_qasm_file_to_qprog(filepath)
