# Quantum Noise Optimizer - Project State (2026-05-15)

## GitHub
- Repo: https://github.com/mapleleaflatte03/quantum-noise-optimizer
- Status: Public, initial release pushed
- User: mapleleaflatte03

## Environment
- Server: GCP Ubuntu instance at /home/ubuntu
- Python: 3.14.4
- Venv: ~/qpanda3-env (pyqpanda3 v0.3.5 installed)
- Extra dep needed: libgomp1

## pyqpanda3 API (verified correct)
- from pyqpanda3 import core, quantum_info
- prog = core.QProg()
- prog << core.H(0) << core.CNOT(0, 1)
- prog << core.measure([0, 1], [0, 1])
- machine = core.CPUQVM()
- machine.run(prog, shots=10000, model=noise_model)
- counts = machine.result().get_counts()
- Statevector: machine.run(prog, shots=0) then machine.result().get_state_vector()
- Fidelity: quantum_info.hellinger_fidelity(dict1, dict2)

## Noise API
- core.NoiseModel().add_quantum_error(error, GateType, [qubits])
- core.NoiseModel().add_all_qubit_quantum_error(error, GateType)
- Error functions: depolarizing_error(p), amplitude_damping_error(p), phase_damping_error(p), decoherence_error(t1,t2,gate_time), pauli_x/y/z_error(p)
- GateTypes: H, X, Y, Z, S, T, RX, RY, RZ, CNOT, CZ, SWAP, TOFFOLI

## Benchmark Results
- 36 scenarios tested (symmetric + asymmetric noise)
- 34/36 improved, avg +21.18%, max +190.98%

## Next Steps
- Add rotation merging, gate cancellation
- Add readout error mitigation
- Connect to OriginQ cloud for real hardware validation
- Write blog post / arXiv paper
- Add GitHub Actions CI
