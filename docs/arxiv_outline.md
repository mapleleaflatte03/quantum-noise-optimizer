# arXiv Preprint Outline

## Title (options)
- "Calibration-Aware Circuit Optimization for Superconducting Quantum Processors: A Physics-Informed Approach on Origin Wukong 180"
- "Physics-Informed Noise-Aware Compilation and Error Suppression for NISQ Devices"

## Abstract (~150 words)
We present an open-source, physics-informed quantum circuit optimization toolkit
that combines noise-aware compilation with error mitigation techniques, specifically
targeting superconducting NISQ processors. Our approach uses real-time hardware
calibration data (T1, T2, gate fidelity, readout fidelity) to make informed
decisions about qubit selection, gate decomposition, and error suppression.
We demonstrate on Origin Wukong 180 (180-qubit superconducting processor) that
calibration-aware qubit selection improves circuit fidelity by X% compared to
default qubit mapping. Our toolkit integrates rotation merging, gate cancellation,
noise-aware gate substitution, readout error mitigation, zero-noise extrapolation,
and dynamical decoupling in a unified pipeline. All code is open-source (MIT license)
and built on pyqpanda3.

## 1. Introduction
- NISQ era: noise is the bottleneck
- Existing tools (Mitiq, Q-CTRL Fire Opal, Qiskit transpiler) — what they do and don't do
- Gap: no open-source physics-informed error suppression for OriginQ/pyqpanda3 ecosystem
- Our contribution: unified toolkit + hardware validation on Wukong 180

## 2. Background
- 2.1 Quantum noise in superconducting processors (T1, T2, gate errors, readout errors)
- 2.2 Error suppression vs error mitigation vs error correction
- 2.3 Origin Wukong 180 hardware characteristics

## 3. Methods
- 3.1 Noise Profiling: per-gate error characterization
- 3.2 Calibration-Aware Qubit Selection
  - Scoring function: weighted combination of T2, readout fidelity, gate fidelity
  - Graph search for optimal connected subgraphs
  - Physics motivation: why T2 matters more than T1 for circuit fidelity
- 3.3 Circuit Optimization Passes
  - Rotation merging
  - Gate cancellation + commutation
  - Noise-aware gate substitution (CNOT ↔ CZ)
- 3.4 Error Mitigation
  - Readout error mitigation (confusion matrix)
  - Zero-Noise Extrapolation (unitary folding)
  - Dynamical Decoupling (XY4)

## 4. Experimental Setup
- 4.1 Hardware: Origin Wukong 180 (specs from calibration data)
  - 169 active qubits, 396 CZ gates
  - T1: 6.8-117.0 μs, T2: 0.6-26.3 μs
  - CZ fidelity: 0.93-1.00
- 4.2 Benchmark circuits: Bell, GHZ-3, GHZ-5, variational ansatz
- 4.3 Comparison: default qubits vs calibration-selected qubits

## 5. Results
- 5.1 Simulator results (already have)
  - Gate substitution: +21% avg, +191% max (asymmetric noise)
  - Circuit passes: 30% gate reduction
  - Readout mitigation: +25%
  - ZNE: +3.8%
  - Combined pipeline: +38%
- 5.2 Hardware results (pending — from hardware_experiment.py)
  - Bell: baseline vs optimal qubits
  - GHZ-3: baseline vs optimal qubits
  - Fidelity improvement from calibration-aware selection
- 5.3 Effective T2 analysis
  - Fidelity decay vs circuit depth
  - Comparison with theoretical prediction

## 6. Discussion
- Physics insight: why calibration-aware selection works
  - T2 variation across chip (0.6-26.3 μs = 44x range!)
  - Readout fidelity variation (0.77-0.99)
  - CZ fidelity variation (0.93-1.00)
- Comparison with Q-CTRL Fire Opal approach
- Limitations: free-tier access, limited shots, no pulse-level control
- Future: pulse optimization, ML-driven selection, multi-chip support

## 7. Conclusion
- First open-source physics-informed error suppression toolkit for pyqpanda3/OriginQ
- Demonstrated calibration-aware qubit selection on real hardware
- All code available: github.com/mapleleaflatte03/quantum-noise-optimizer

## References (~15-20)
- Temme et al. 2017 (ZNE)
- Endo et al. 2018 (PEC)
- Q-CTRL Fire Opal paper (2022)
- COGNAC paper (2024)
- Noise-adaptive compilation (Murali et al. 2019)
- Origin Wukong papers
- pyqpanda3 paper (2025)

---

## What's needed to complete the paper:

### Already have:
- [x] All simulator results
- [x] Real calibration data from Wukong 180
- [x] Calibration-aware qubit selection algorithm
- [x] Full toolkit implementation (8 modules)
- [x] Code on GitHub

### Still need:
- [ ] Hardware results (baseline vs optimized) — script running
- [ ] Statistical analysis (error bars, multiple runs if possible)
- [ ] Figures (circuit diagrams, fidelity comparison bar charts, T2 heatmap)
- [ ] Writing (2-3 weeks for first draft)
- [ ] Feedback from someone in the field (optional but helpful)

### Estimated timeline:
- Hardware results: 1-7 days (waiting for queue)
- First draft: 2-3 weeks after hardware results
- Submission to arXiv: 1 month from now
