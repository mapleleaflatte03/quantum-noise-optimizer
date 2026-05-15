# Quantum Noise Optimizer

**Physics-informed quantum circuit optimizer + error mitigation toolkit built on [pyqpanda3](https://pypi.org/project/pyqpanda3/)**

Profiles hardware noise, optimizes circuits, mitigates errors, and visualizes noise physics — combining compilation passes with error mitigation for maximum fidelity.

## Key Results

| Technique | Scenario | Improvement |
|-----------|----------|------------:|
| Gate substitution | 5q GHZ, CNOT 10x noisier than CZ | **+191%** |
| Readout mitigation | Bell state, 10-15% readout error | **+25%** |
| Circuit passes | 5q VQE (4 layers), 30% gate reduction | **+2.2%** |
| Zero-Noise Extrapolation | Bell state, 5% depolarizing | **+3.8%** |
| Full pipeline combined | 3q GHZ, asymmetric noise + readout | **+38%** |

## Features

### 🔧 Circuit Optimization
- **Rotation merging**: RZ(a)·RZ(b) → RZ(a+b)
- **Gate cancellation**: H·H, X·X, CNOT·CNOT → identity
- **Commutation reordering**: moves gates to enable more cancellations
- **Noise-aware substitution**: CNOT → H·CZ·H when CZ is less noisy

### 🛡️ Error Mitigation
- **Readout mitigation**: Confusion matrix calibration + inversion
- **Zero-Noise Extrapolation (ZNE)**: Unitary folding + extrapolation to zero noise
- **Dynamical Decoupling (DD)**: XY4/XX sequences during idle periods

### 📊 Physics Visualization
- **Noise report**: Per-gate error rates, estimated circuit fidelity, decay curve
- **Fidelity vs depth**: Exponential decay with effective T2 estimate
- **Noise heatmap**: Layer-by-layer fidelity degradation

### 🔄 Interoperability
- **QASM import/export**: OpenQASM 2.0 round-trip support

## Installation

```bash
pip install pyqpanda3
git clone https://github.com/mapleleaflatte03/quantum-noise-optimizer.git
cd quantum-noise-optimizer
sudo apt install libgomp1  # Linux only
```

Requires Python 3.10+.

## Quick Start

```python
import sys; sys.path.insert(0, "src")
from pyqpanda3 import core
from noise_optimizer import *

# Optimize a circuit
prog = from_qasm("""OPENQASM 2.0;
include "qelib1.inc";
qreg q[2];
h q[0]; h q[0]; h q[0];
cx q[0],q[1]; cx q[0],q[1];
""")
optimized = optimize_circuit(prog)  # 5 gates → 1 gate

# Noise-aware substitution
noise = core.NoiseModel()
noise.add_all_qubit_quantum_error(core.depolarizing_error(0.10), core.GateType.CNOT)
noise.add_all_qubit_quantum_error(core.depolarizing_error(0.02), core.GateType.CZ)
profiler = NoiseProfiler(noise, shots=5000)
optimizer = NoiseAwareOptimizer(profiler.profile())
ghz = optimizer.build_ghz_state(5)  # Auto-selects CZ over CNOT

# Error mitigation
mitigator = ReadoutMitigator(n_qubits=2)
mitigator.calibrate(noise)
corrected = mitigator.mitigate(raw_counts)

# ZNE
zne = ZeroNoiseExtrapolator(scale_factors=[1, 2, 3])
result = zne.mitigate_expectation(circuit, noise, n_qubits=2)

# Physics visualization
print_noise_report(prog, noise, n_qubits=2)
decay = fidelity_vs_depth(3, max_depth=10, noise_model=noise)
print(f"Effective T2: {decay['t2_effective']:.1f} layers")
```

## Examples

```bash
python examples/demo_ghz.py            # Noise-aware GHZ optimization
python examples/demo_full_pipeline.py   # All techniques combined
python examples/demo_physics.py         # Physics visualization + DD
```

## Run Tests

```bash
python tests/test_all.py  # 10 tests
```

## Project Structure

```
src/noise_optimizer/
├── noise_profiler.py          # Per-gate error characterization
├── optimizer.py               # Noise-aware gate substitution
├── circuit_passes.py          # Rotation merging, gate cancellation
├── readout_mitigator.py       # Measurement error correction
├── zne.py                     # Zero-Noise Extrapolation
├── dynamical_decoupling.py    # DD sequence insertion (XY4, XX)
├── visualization.py           # Noise reports, fidelity decay, T2 estimation
└── qasm.py                    # OpenQASM 2.0 import/export
```

## Physics Background

This toolkit is designed around physical understanding of quantum noise:

| Noise Type | Physical Cause | Our Mitigation |
|------------|---------------|----------------|
| Depolarizing | Random Pauli errors | Gate substitution, circuit reduction |
| T1 (relaxation) | Energy decay to ground state | Shorter circuits via optimization |
| T2 (dephasing) | Phase randomization | Dynamical decoupling, ZNE |
| Readout error | Detector imperfections | Confusion matrix inversion |
| Crosstalk | Qubit-qubit coupling | (planned: topology-aware routing) |

**Key insight**: Fidelity decays exponentially with circuit depth (effective T2 ≈ 10-20 gate layers at typical NISQ noise). Every gate removed = exponential fidelity gain.

## Built With

- [pyqpanda3](https://pypi.org/project/pyqpanda3/) v0.3.5 — OriginQ quantum SDK (MIT)
- Python 3.10+ / NumPy / SciPy

## License

MIT
