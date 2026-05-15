# Quantum Noise Optimizer - Project State (2026-05-15, session 2)

## GitHub
- Repo: https://github.com/mapleleaflatte03/quantum-noise-optimizer
- Status: v0.2.0 pushed (5 commits on main)
- User: mapleleaflatte03

## Environment
- Server: GCP Ubuntu instance at /home/ubuntu
- Python: 3.14.4
- Venv: ~/qpanda3-env (pyqpanda3 v0.3.5 installed)
- Extra dep needed: libgomp1

## Current Modules (v0.2.0)

### src/noise_optimizer/
- **noise_profiler.py** — Profiles per-gate error rates via test circuits
- **optimizer.py** — Gate substitution (CNOT↔CZ) based on noise profile
- **benchmark.py** — Comparative fidelity benchmarks (asymmetric noise)
- **circuit_passes.py** — NEW: rotation merging, gate cancellation, commutation
- **readout_mitigator.py** — NEW: confusion matrix calibration + inversion
- **zne.py** — NEW: Zero-Noise Extrapolation via unitary folding

### Key Results
- Gate substitution: +21% avg, +191% max (asymmetric noise)
- Circuit passes: 30% gate reduction on VQE circuits, +2.2% fidelity
- Readout mitigation: +25% fidelity improvement
- ZNE: +3.8% fidelity improvement (compounds with other techniques)

## pyqpanda3 API Notes
- QProg introspection: prog.operations() returns list of QGate objects
- QGate: .name(), .gate_type(), .qubits(), .parameters(), .dagger()
- Can rebuild QProg by appending QGate objects directly: new_prog << op
- Readout error: noise.add_read_out_error(matrix_2x2, qubit_index)
- circuit_stats: prog.depth(), prog.qubits_num()

## Next Steps (v0.2.0 remaining)
- [ ] QASM import/export (pyqpanda3.intermediate_compiler has this)
- [ ] GitHub Actions CI
- [ ] Update README with new features
- [ ] Combined example: passes + gate substitution + readout + ZNE together

## Next Phase (v0.3.0)
- Dynamical Decoupling (DD) sequences
- Physics visualization (noise heatmap, T1/T2 decay plots)
- OriginQ Cloud connection (pyqpanda3.qcloud)
