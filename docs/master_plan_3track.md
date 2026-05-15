# MASTER PLAN: Quantum Noise Intelligence — 3-Track (Updated May 15, 2026)

## Track Status

| Track | Status | Notes |
|-------|--------|-------|
| A: MCP Server | ✅ Complete | 8 tools, verified with Codex CLI + Copilot CLI |
| B: Bounded ZNE | ✅ Complete | 75% win rate, AICc, 125-config benchmark |
| C: Hardware | ⛔ BLOCKED | OriginQ API breaking change (errCode 33) |

## Known Issue: OriginQ Cloud API Breaking Change

- **Date discovered:** May 15, 2026
- **Error:** `"Insts is NOT a Array!"` (errCode 33)
- **Affected:** ALL QPU backends (WK_C180, PQPUMESH8)
- **Root cause:** Server-side format change, pyqpanda3 0.3.5 sends valid JSON array but server rejects
- **Tested:** offset 0/1/2, is_scheduling True/False, batch format, wrapped gates — all fail
- **Resolution:** Wait for pyqpanda3 0.3.6+ or OriginQ server fix

## Simulator-First Strategy

All development and benchmarks use:
- **Qiskit Aer** (primary): realistic noise models, 4096 shots
- **pyqpanda3 CPUQVM** (secondary): Wukong-calibrated noise

Noise parameters from real Wukong 180 calibration data:
- CZ gate error: 3%
- Single-qubit error: 0.5%
- Readout error: 2%
- T1: ~100μs, T2: ~80μs

## Architecture
```
MCP Server (8 tools) → AI agents (Codex, Copilot, Claude)
  ↓
Mitigation Engine → PhysicallyBoundedZNE + AutoMitigator + AdaptiveDD
  ↓
Backend: Qiskit Aer + pyqpanda3 CPUQVM (simulator)
         Origin Wukong 180 (when API fixed)
```

## What's Done
- [x] PhysicallyBoundedZNE with AICc (75% win rate, 0% unphysical)
- [x] AutoMitigator (strategy selection)
- [x] AdaptiveDD ported to Qiskit
- [x] MCP server (8 tools, FastMCP 3.3, stdio)
- [x] Verified with Codex CLI (GPT-5.5) + Copilot CLI
- [x] 125-config paper benchmark
- [x] Hardware-ready experiment script
- [x] Paper draft v1 (9 sections)
- [x] 20 tests passing
- [x] Demo script for GIF

## What's Next
1. Submit paper to arXiv (simulator data sufficient)
2. Apply Unitary Fund microgrant
3. Community launch (Reddit, X, LinkedIn)
4. Re-test Wukong when pyqpanda3 updates
