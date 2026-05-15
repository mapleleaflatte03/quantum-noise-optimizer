# Quantum Noise Optimizer

**Noise-Aware Quantum Circuit Optimizer built on [pyqpanda3](https://pypi.org/project/pyqpanda3/)**

Automatically profiles hardware noise characteristics and rewrites quantum circuits to use gate decompositions that minimize error — achieving up to **+191% fidelity improvement** in realistic asymmetric noise scenarios.

## Key Results

| Scenario | Baseline Fidelity | Optimized Fidelity | Improvement |
|----------|------------------:|-------------------:|------------:|
| 5-qubit GHZ, CNOT 10x noisier than CZ | 0.287 | 0.835 | **+191%** |
| 5-qubit GHZ, CNOT 5x noisier | 0.537 | 0.835 | **+55%** |
| 3-qubit GHZ, CNOT 10x noisier | 0.540 | 0.916 | **+69%** |
| 2-qubit Bell, CNOT 10x noisier | 0.742 | 0.953 | **+28%** |

> Tested across 36 configurations. 34/36 showed improvement. Average: **+21%**.

## How It Works

1. **Noise Profiling** — Runs characterization circuits to measure per-gate error rates
2. **Gate Substitution** — Replaces high-noise gates with equivalent lower-noise decompositions (e.g., CNOT → H·CZ·H when CZ is less noisy)
3. **Fidelity Benchmarking** — Compares optimized vs baseline circuits using Hellinger fidelity

This is particularly effective on hardware where two-qubit gate error rates are asymmetric (common in superconducting transmon devices where CZ can be 3-10x less noisy than CNOT).

## Installation

```bash
pip install pyqpanda3
git clone https://github.com/mapleleaflatte03/quantum-noise-optimizer.git
cd quantum-noise-optimizer
```

Requires Python 3.10+ and `libgomp1` on Linux:
```bash
sudo apt install libgomp1
```

## Quick Start

```python
from pyqpanda3 import core
import sys; sys.path.insert(0, "src")
from noise_optimizer import NoiseProfiler, NoiseAwareOptimizer, Benchmark

# Define a noise model (CNOT 5x noisier than CZ)
noise = core.NoiseModel()
noise.add_all_qubit_quantum_error(core.depolarizing_error(0.10), core.GateType.CNOT)
noise.add_all_qubit_quantum_error(core.depolarizing_error(0.02), core.GateType.CZ)
noise.add_all_qubit_quantum_error(core.depolarizing_error(0.005), core.GateType.H)

# Profile the noise
profiler = NoiseProfiler(noise, shots=5000)
profile = profiler.profile()

# Build optimized circuits
optimizer = NoiseAwareOptimizer(profile)
ghz_circuit = optimizer.build_ghz_state(5)

# Run with noise
prog = core.QProg()
prog << ghz_circuit << core.measure(list(range(5)), list(range(5)))
machine = core.CPUQVM()
machine.run(prog, shots=10000, model=noise)
print(machine.result().get_counts())
```

## Run Benchmarks

```python
from noise_optimizer import Benchmark

bench = Benchmark(shots=10000)
bench.run_all()
print(bench.summary())
```

## Run Tests

```bash
python tests/test_all.py
```

## Project Structure

```
src/noise_optimizer/
├── noise_profiler.py   # Characterizes per-gate error rates
├── optimizer.py        # Rewrites circuits using lower-noise gates
└── benchmark.py        # Comparative fidelity benchmarks
```

## Why This Matters

Real quantum hardware has **asymmetric noise** — not all gates are equally noisy. Most quantum SDKs compile circuits without considering the specific noise profile of the target device. This optimizer bridges that gap by:

- Profiling the actual noise characteristics
- Making informed gate substitution decisions
- Demonstrating measurable fidelity improvements

## Built With

- [pyqpanda3](https://pypi.org/project/pyqpanda3/) v0.3.5 — OriginQ's quantum computing SDK (MIT License)
- Python 3.14

## License

MIT
