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

## Architecture

```
┌─────────────────────────────────────────────────┐
│  MCP Server (Track A)                           │  AI agents call these tools
│  noise_profile | recommend | run_zne | compare  │
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

### Tools Available

| Tool | Description |
|------|-------------|
| `noise_profile` | Get noise characteristics for a quantum backend |
| `recommend_mitigation` | AI-powered strategy selection with reasoning |
| `run_bounded_zne` | Physically-bounded ZNE extrapolation |
| `compare_strategies` | Benchmark all methods on a test circuit |

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
- **Track C (Proof):** Dual-hardware validation on IBM Quantum + Origin Wukong 180

## Built With

- [Qiskit](https://qiskit.org/) 2.4.1 — IBM quantum SDK
- [pyqpanda3](https://pypi.org/project/pyqpanda3/) 0.3.5 — OriginQ quantum SDK
- [FastMCP](https://github.com/jlowin/fastmcp) 3.3.0 — MCP server framework
- Python 3.10+ / NumPy / SciPy

## License

MIT
