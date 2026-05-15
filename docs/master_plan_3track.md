# MASTER PLAN: Quantum Noise Intelligence — 3-Track Combined

## Track A: Noise-Aware MCP Server | Track B: Novel ZNE | Track C: Hardware Validation

### Gap: No open-source noise-focused MCP exists. We build it.

### Key Paper: arXiv:2604.24475 (Physically Bounded ZNE, Apr 2026)
- Constrain Ê(0) ∈ [-1,1] during optimization (not post-hoc clipping)
- Best model: poly-exponential d=1, a=0, bounded
- 8.5x lower MAE vs unbounded exponential
- We extend: adaptive model selection + combine with DD + multi-backend

### Architecture
```
MCP Server → AutoMitigator → {BoundedZNE, AdaptiveDD, ReadoutCorrector} → Backend (Qiskit/pyqpanda3)
```

### Timeline: 6 months
- M1: Prototype BoundedZNE on Qiskit Aer
- M2: AutoMitigator + AdaptiveDD
- M3: MCP server (FastMCP)
- M4: Hardware (IBM free + Wukong 180)
- M5: arXiv paper
- M6: Community launch

### Tech: Qiskit 2.4.1 + Aer + pyqpanda3 + FastMCP + L-BFGS-B (SciPy)
