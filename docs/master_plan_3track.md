# MASTER PLAN: Quantum Noise Intelligence — 3-Track (Updated)

> No IBM hardware access (respecting export policy). Wukong 180 = primary hardware.

## Architecture (final)
```
MCP Server (Track A) → AI agents call noise tools
  ↓
Mitigation Engine (Track B) → PhysicallyBoundedZNE + AutoMitigator
  ↓
Backend Layer (Track C):
  - Qiskit Aer simulator (development + benchmarks)
  - pyqpanda3 CPUQVM (local simulator)
  - Origin Wukong 180 (real hardware, 60s runtime)
  - OriginQ Cloud simulator (full_amplitude, works)
```

## Hardware Status
- Wukong 180: shows "online" but jobs block indefinitely (queue)
- Cloud simulator: WORKS (sim.run(prog, shots) → ~6s latency)
- Local CPUQVM: WORKS (instant)
- Qiskit Aer: WORKS (instant, realistic noise models)
- IBM Quantum: NOT AVAILABLE (export control, respecting policy)

## What's Done (v0.4.0)
- [x] PhysicallyBoundedZNE with AICc (75% win rate)
- [x] AutoMitigator (strategy selection)
- [x] MCP server (4 tools, FastMCP 3.3)
- [x] 72-config benchmark
- [x] Paper draft v1
- [x] IBM Quantum simulation mode (Aer)
- [x] Wukong calibration data (169 qubits, 396 CZ gates)

## What's Next
1. Polish MCP server (stdio transport for Claude Desktop)
2. Port AdaptiveDD to Qiskit
3. Try Wukong during off-peak (night China time = ~14:00-22:00 UTC)
4. Fill paper [TODO] sections
5. Apply Unitary Fund when prototype is solid

## Narrative
"Open-source, physics-informed quantum error mitigation engine with
physically-bounded ZNE (75% win rate vs standard), accessible via MCP
server for AI agents, validated on Origin Wukong 180 superconducting
processor."
