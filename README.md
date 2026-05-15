# Quantum Noise Intelligence

**AI-accessible, physics-informed quantum error mitigation engine with novel physically-bounded ZNE.**

[![CI](https://github.com/mapleleaflatte03/quantum-noise-optimizer/actions/workflows/ci.yml/badge.svg)](https://github.com/mapleleaflatte03/quantum-noise-optimizer/actions)

The first open-source **noise-focused MCP server** for quantum computing. Exposes noise profiling, mitigation strategy selection, and physically-bounded Zero-Noise Extrapolation to AI agents via the Model Context Protocol.

## Key Results

| Method | vs Standard ZNE | Benchmark |
|--------|----------------|-----------|
| **Physically-Bounded ZNE** (AICc) | **75% win rate** | 72 configs, GHZ/Random/QFT |
| Bounded ZNE mean error | 0.019 vs 0.020 (linear) vs 0.046 (quadratic) | 3 noise levels |
| Auto model selection | Prevents overfitting via AICc penalty | Poly/Exp/PolyExp families |

Based on [arXiv:2604.24475](https://arxiv.org/abs/2604.24475) (Physically Bounded ZNE, Apr 2026).

## Demo

```
  ⚛️  Quantum Noise Intelligence
  Physically-Bounded ZNE for Reliable Quantum Computing

▶ Step 1: Measure noisy circuit at multiple noise scales
  Scale factors: [1, 2, 3, 4, 5]
  Noisy ⟨Z⟩:     [0.62, 0.45, 0.31, 0.20, 0.12]
  ⚠  Raw noisy result: ⟨Z⟩ = 0.62  (ideal = 0.85)

▶ Step 2: Apply PhysicallyBoundedZNE
  ✓ Zero-noise estimate: ⟨Z⟩ = 0.8419
  ✓ Bounded to [-1, 1] — physically valid!

▶ Step 3: Comparison
  ┌──────────────────────┬──────────┬─────────┐
  │ Method               │  ⟨Z⟩     │  Error  │
  ├──────────────────────┼──────────┼─────────┤
  │ Raw noisy            │  0.6200  │  0.2300 │
  │ Standard ZNE         │  0.9200  │  0.0700 │
  │ Bounded ZNE (ours)   │  0.8419  │  0.0081 │
  └──────────────────────┴──────────┴─────────┘

  🏆 Result: 75% win rate vs. standard ZNE (72-config benchmark)
```

Run the interactive demo: `python examples/demo_gif.py`

## Architecture

```
┌─────────────────────────────────────────────────┐
│  MCP Server (Track A)                           │  AI agents call these tools
│  8 tools: profile, recommend, zne, compare...   │
├─────────────────────────────────────────────────┤
│  Mitigation Engine (Track B)                    │  Novel algorithms
│  PhysicallyBoundedZNE | AutoMitigator | DD      │
├─────────────────────────────────────────────────┤
│  Backend Layer (Track C)                        │  Multi-hardware
│  Qiskit (IBM) | pyqpanda3 (Wukong 180)         │
└─────────────────────────────────────────────────┘
```

## MCP Server Usage

```bash
# Run the MCP server
python mcp_server/server.py

# Or with uvicorn
uvicorn mcp_server.server:mcp --host 0.0.0.0 --port 8000
```

### Tools Available (8)

| Tool | Description |
|------|-------------|
| `noise_profile` | Get noise characteristics for a quantum backend |
| `recommend_mitigation` | AI-powered strategy selection with reasoning |
| `run_bounded_zne` | Physically-bounded ZNE extrapolation |
| `compare_strategies` | Benchmark all methods on a test circuit |
| `wukong_status` | Check Origin Wukong 180 quantum computer status |
| `optimize_circuit` | Optimize a QASM circuit and recommend mitigation |
| `get_calibration_data` | Real Wukong 180 calibration: top-5 qubits, gate stats, connectivity |
| `run_experiment` | Full pipeline: circuit → noise → mitigation → fidelity result |

### AI Agent CLI Examples

```bash
# Codex CLI
codex exec --dangerously-bypass-approvals-and-sandbox "Use quantum-noise MCP to run a 4-qubit GHZ experiment with bounded_zne and report fidelity"

# Copilot CLI
copilot -p "Get Wukong 180 calibration data and find the best qubits" --allow-tool='quantum-noise' --yolo
```

### Claude Desktop / Cursor Config

```json
{
  "mcpServers": {
    "quantum-noise": {
      "command": "python",
      "args": ["mcp_server/server.py"],
      "cwd": "/path/to/quantum-noise-optimizer"
    }
  }
}
```

## Python API

```python
from noise_optimizer.bounded_zne import PhysicallyBoundedZNE, auto_select_model

# Physically-bounded ZNE
zne = PhysicallyBoundedZNE(bounds=(-1, 1), model="poly_exp", degree=1)
zne.fit(scale_factors=[1, 1.5, 2, 2.5, 3], expectation_values=[0.85, 0.72, 0.61, 0.52, 0.44])
print(zne.zero_noise_estimate_)  # Guaranteed within [-1, 1]

# Auto model selection (AICc)
name, model = auto_select_model([1, 1.5, 2, 2.5, 3], [0.85, 0.72, 0.61, 0.52, 0.44])
print(f"Best model: {name}, estimate: {model.zero_noise_estimate_:.4f}")

# Strategy recommendation
from noise_optimizer.auto_mitigator import AutoMitigator
am = AutoMitigator()
rec = am.recommend(circuit, noise_profile={'avg_2q_error': 0.01})
print(f"Strategy: {rec['strategy']}, Reason: {rec['reason']}")
```

## Installation

```bash
git clone https://github.com/mapleleaflatte03/quantum-noise-optimizer.git
cd quantum-noise-optimizer
pip install -e ".[all]"
```

## Project Structure

```
mcp_server/
└── server.py                  # MCP server (FastMCP 3.3)
src/noise_optimizer/
├── bounded_zne.py             # Physically-bounded ZNE (novel)
├── auto_mitigator.py          # Strategy selection engine
├── noise_profiler.py          # Per-gate error characterization
├── optimizer.py               # Noise-aware gate substitution
├── circuit_passes.py          # Rotation merging, gate cancellation
├── readout_mitigator.py       # Measurement error correction
├── zne.py                     # Standard ZNE (unitary folding)
├── dynamical_decoupling.py    # DD sequence insertion
├── visualization.py           # Noise reports, fidelity decay
├── qasm.py                    # OpenQASM 2.0 import/export
└── hardware_calibration.py    # Wukong 180 calibration data
benchmarks/
└── bounded_zne_benchmark.py   # 72-config benchmark suite
```

## Research Contribution

This project combines three tracks:

- **Track A (Reach):** First noise-focused MCP server — makes quantum error mitigation accessible to AI agents
- **Track B (Novelty):** Physically-bounded ZNE with AICc model selection — extends arXiv:2604.24475
- **Track C (Proof):** Simulator validation with Wukong-calibrated noise models (hardware pending API fix)

## Known Issue: OriginQ Cloud API Breaking Change (May 2026)

⚠️ **Hardware submission to WK_C180 and PQPUMESH8 is currently non-functional.**

- **Error:** `"Insts is NOT a Array!"` (errCode 33) on all job submissions
- **Cause:** OriginQ Cloud server-side breaking change — instruction format rejected despite pyqpanda3 0.3.5 sending valid JSON arrays
- **Scope:** All QPU backends affected (WK_C180, PQPUMESH8). Cloud simulator (`full_amplitude`) also affected.
- **Workaround:** Use Qiskit Aer or pyqpanda3 CPUQVM (local simulators) with realistic noise models calibrated from real Wukong 180 data.
- **Status:** Waiting for OriginQ SDK update (pyqpanda3 0.3.6+)

All benchmark results use simulator with Wukong-calibrated noise (3% CZ, 0.5% 1Q, 2% readout).

## Built With

- **arXiv preprint (v1):** `paper/quantum_noise_intelligence/` — 8-page paper, 25 references, 4 figures. Compile with `make` in that directory.

### Dependencies

- [Qiskit](https://qiskit.org/) 2.4.1 — IBM quantum SDK
- [pyqpanda3](https://pypi.org/project/pyqpanda3/) 0.3.5 — OriginQ quantum SDK
- [FastMCP](https://github.com/jlowin/fastmcp) 3.3.0 — MCP server framework
- Python 3.10+ / NumPy / SciPy

## License

MIT
