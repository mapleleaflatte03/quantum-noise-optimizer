# Research Notes: Quantum Error Mitigation Literature Review

**Date:** 2026-05-15  
**Context:** Quantum Noise Optimizer project — physically-bounded ZNE with AICc model selection  

---

## 1. Core ZNE Papers

### 1.1 Physically Bounded ZNE (Our Primary Reference)

**Citation:** Miranskyy, A., Sorrenti, A., Thind, J., & Gravel, C. (2026). "Improving Zero-Noise Extrapolation via Physically Bounded Models." arXiv:2604.24475 [quant-ph].

**Summary:** Introduces physically bounded variants of polynomial, exponential, and polynomial–exponential extrapolation models for ZNE by explicitly parameterizing the zero-noise estimate and constraining it during optimization. Evaluated on a large synthetic benchmark of 180,000 circuits (~3.6 million ZNE experiments) under realistic IBM device noise models, plus preliminary hardware validation with GHZ and W-state circuits.

**Key Results:**
- Bounded extrapolation substantially reduces unphysical predictions
- Improves stability of exponential and poly-exponential models
- Polynomial models show little difference between bounded/unbounded variants
- Hardware experiments confirm bounded models avoid pathological extrapolations

**Relevance to Our Work:** **DIRECT PREDECESSOR.** Our project implements the same core idea (physically bounded ZNE) and extends it with AICc-based automatic model selection. Their work validates the approach at scale; we add the automated model selection layer and integrate it into a practical optimization pipeline with pyqpanda3.

---

### 1.2 Physics-Inspired Extrapolation (PIE)

**Citation:** Díez-Valle, P., Saxena, G., Baker, J. S., Lee, J.-H., & Kyaw, T. H. (2025/2026). "Physics-Inspired Extrapolation for efficient error mitigation and hardware certification." arXiv:2505.07977 [quant-ph]. Accepted in IOP Quantum Science and Technology.

**Summary:** Proposes PIE, a linear circuit runtime protocol building on the EMRE (error mitigation by restricted evolution) framework. Unlike heuristic ZNE, PIE provides theoretical foundations for fitting parameters — the slope corresponds to the max-relative entropy between ideal and noisy circuits. Achieves enhanced accuracy without substantial overhead and enables simultaneous hardware certification.

**Key Results:**
- Constant sampling overhead (vs. exponential for unbiased methods)
- Demonstrated on 84-qubit quantum dynamics on IBMQ hardware
- Converges to unbiased estimates as noise decreases
- Dual-purpose: error mitigation + hardware certification simultaneously

**Relevance to Our Work:** Complementary approach to ZNE. PIE provides theoretical grounding for *why* extrapolation works, while our bounded ZNE + AICc approach is more practical/empirical. PIE's hardware certification aspect could be integrated as a diagnostic tool alongside our optimizer. The 84-qubit demonstration sets a scalability benchmark we should target.

---

### 1.3 Digital Zero-Noise Extrapolation

**Citation:** Giurgica-Tiron, T., Hindy, Y., LaRose, R., Mari, A., & Zeng, W. J. (2020). "Digital zero noise extrapolation for quantum error mitigation." IEEE International Conference on Quantum Computing and Engineering (QCE), 2020. arXiv:2005.10921 [quant-ph].

**Summary:** Reviews ZNE fundamentals and proposes key improvements: unitary folding (digital noise scaling requiring only gate-level access) and an adaptive extrapolation protocol using statistical inference. This is the foundational paper for digital ZNE as implemented in Mitiq and widely adopted.

**Key Results:**
- 18X to 24X error reduction over non-mitigated circuits
- Unitary folding: global, local, and random variants
- Demonstrated ZNE at larger qubit numbers than previously tested
- Introduced the adaptive Richardson extrapolation framework

**Relevance to Our Work:** **FOUNDATIONAL.** Our ZNE implementation uses unitary folding (from this paper) for noise amplification. Our AICc model selection extends their adaptive protocol idea — instead of a fixed extrapolation order, we automatically select the best model family and complexity. Their 18-24X improvement is our baseline to beat.

---

## 2. Comprehensive Reviews & Software

### 2.1 Quantum Error Mitigation (Review)

**Citation:** Cai, Z., Babbush, R., Benjamin, S. C., Endo, S., Huggins, W. J., Li, Y., McClean, J. R., & O'Brien, T. E. (2023). "Quantum Error Mitigation." Reviews of Modern Physics, 95, 045005. arXiv:2210.00921 [quant-ph].

**Summary:** Comprehensive review surveying all QEM methods, assessing their efficacy, and describing hardware demonstrations. Identifies commonalities and limitations, discusses how methods can be chosen based on primary noise type, and outlines open problems for achieving quantum advantage through mitigation.

**Key Results:**
- Taxonomy of QEM methods: ZNE, PEC, CDR, symmetry verification, etc.
- Analysis of sampling overhead scaling for each method
- Identifies that combining methods is key to practical advantage
- Published in Rev. Mod. Phys. — the definitive reference

**Relevance to Our Work:** Essential background reference. Provides the theoretical framework for understanding where bounded ZNE fits in the QEM landscape. Their discussion of method selection based on noise type motivates our AICc approach — different extrapolation models suit different noise profiles, and automatic selection addresses this.

---

### 2.2 Mitiq: Error Mitigation Software

**Citation:** LaRose, R., Mari, A., Kaiser, S., Karalekas, P. J., Alves, A. A., Czarnik, P., El Mandouh, M., Gordon, M. H., Hindy, Y., Robertson, A., Thakre, P., Wahl, M., Samuel, D., Mistri, R., Tremblay, M., Gardner, N., Stemen, N. T., Shammah, N., & Zeng, W. J. (2022). "Mitiq: A software package for error mitigation on noisy quantum computers." Quantum, 6, 774. arXiv:2009.04417 [quant-ph].

**Summary:** Introduces Mitiq, a Python package providing an extensible toolkit for QEM including ZNE, probabilistic error cancellation (PEC), and Clifford data regression (CDR). Designed for backend-agnostic operation with interfaces to multiple quantum frameworks. Demonstrates error mitigation on IBM and Rigetti hardware.

**Key Results:**
- Supports ZNE, PEC, CDR (and later additions)
- Backend-agnostic design (Cirq, Qiskit, pyQuil, Braket)
- Open-source with active community (Unitary Fund)
- Standard reference implementation for ZNE

**Relevance to Our Work:** Mitiq is the primary existing tool we differentiate from. Our contribution adds: (1) physical bounds on extrapolation, (2) AICc-based automatic model selection, (3) integration with pyqpanda3/OriginQ ecosystem. We should ensure interoperability or at minimum benchmark against Mitiq's ZNE.

---

### 2.3 Unified Data-Driven QEM (vnCDR)

**Citation:** Lowe, A., Gordon, M. H., Czarnik, P., Arrasmith, A., Coles, P. J., & Cincio, L. (2021). "Unified approach to data-driven quantum error mitigation." Physical Review Research, 3, 033098. arXiv:2011.01157 [quant-ph].

**Summary:** Proposes variable-noise Clifford data regression (vnCDR), which unifies ZNE and CDR by generating training data via near-Clifford circuits at varying noise levels. Demonstrates significant improvements over individual methods.

**Key Results:**
- 33X improvement over unmitigated results (8-qubit Ising model)
- 20X improvement over ZNE alone, 1.8X over CDR alone
- 64-qubit random circuits: 2.7X over ZNE, 1.5X over CDR
- Scalable to larger systems via Clifford simulation

**Relevance to Our Work:** vnCDR represents the data-driven alternative to our physics-constrained approach. Our bounded ZNE + AICc is lighter-weight (no training data needed) but vnCDR achieves better accuracy when training data is available. These approaches could be complementary — bounded ZNE for quick estimates, vnCDR for high-accuracy needs.

---

## 3. Error Suppression & Hardware Optimization

### 3.1 Q-CTRL Fire Opal

**Citation:** Mundada, P. S., Barbosa, A., Maity, S., Wang, Y., Stace, T. M., Merkh, T., Nielson, F., Carvalho, A. R. R., Hush, M., Biercuk, M. J., & Baum, Y. (2023). "Experimental benchmarking of an automated deterministic error suppression workflow for quantum algorithms." Physical Review Applied, 20, 024034. arXiv:2209.06864 [quant-ph].

**Summary:** Describes Fire Opal, a fully autonomous error suppression workflow combining error-aware compilation, system-wide gate optimization, automated dynamical decoupling, and measurement-error mitigation. Demonstrates comprehensive benchmarks on IBM hardware across multiple algorithms.

**Key Results:**
- >1000X improvement over best alternative expert-configured techniques
- Tested on: Bernstein-Vazirani, QFT, Grover's, QAOA, VQE, QEC syndrome extraction, Quantum Volume
- Up to 16-qubit systems
- Reveals strong contribution of non-Markovian errors
- Deterministic (no sampling overhead)

**Relevance to Our Work:** Fire Opal represents the commercial state-of-the-art for integrated error suppression. Our approach is complementary — Fire Opal focuses on error *suppression* (preventing errors), while our ZNE focuses on error *mitigation* (correcting residual errors post-execution). The two can be stacked. Their dynamical decoupling integration is relevant to our v0.3.0 DD plans.

---

## 4. Machine Learning Approaches

### 4.1 ML for Practical QEM

**Citation:** Liao, H., Wang, D. S., Sitdikov, I., Salcedo, C., Seif, A., & Minev, Z. K. (2024). "Machine Learning for Practical Quantum Error Mitigation." Nature Machine Intelligence, 6, 1478–1486. arXiv:2309.17368 [quant-ph].

**Summary:** Demonstrates that ML-QEM drastically reduces the runtime cost of mitigation without sacrificing accuracy. Benchmarks multiple ML models (linear regression, random forests, MLPs, GNNs) on diverse circuits up to 100 qubits, using digital ZNE as reference. Proposes ML as a path to scalable mitigation by mimicking traditional methods.

**Key Results:**
- Up to 100 qubits on state-of-the-art hardware
- ML models match traditional mitigation accuracy at fraction of runtime
- GNNs show best generalization across circuit families
- Published in Nature Machine Intelligence

**Relevance to Our Work:** ML-QEM is a higher-complexity alternative to our AICc model selection. Our approach is interpretable and lightweight (statistical model selection), while ML-QEM requires training data but scales better. For our project, AICc is more appropriate given our focus on physical interpretability, but ML-QEM results set accuracy benchmarks.

---

### 4.2 GNN for Scalable QEM (GEM)

**Citation:** Wang, H., Wu, X., Liu, J., He, R., Shang, J., Guo, H., & Chen, Q. (2026). "Scalable Quantum Error Mitigation with Physically Informed Graph Neural Networks." arXiv:2604.16815 [quant-ph].

**Summary:** Constructs a graph-enhanced mitigation (GEM) framework encoding quantum circuits as attributed graphs with hardware-level physical information (T1, T2, readout errors as node features; two-qubit gate errors as edge features). Uses GNNs to model error propagation along physical coupling structure with dual-branch affine correction.

**Key Results:**
- Tested on 10-qubit and 16-qubit random circuits on superconducting processors
- Comparable accuracy to CDR at small scales
- Lower mean absolute error and improved stability in zero-shot transfer to larger systems
- Better scalability than global regression methods

**Relevance to Our Work:** GEM's use of physical device parameters (T1, T2, readout errors) as features parallels our noise_profiler module. Their graph-based approach to modeling error propagation could inform future extensions of our optimizer. The "physically informed" aspect aligns with our philosophy of physics-constrained mitigation.

---

## 5. Model Selection & Information Criteria

### 5.1 AIC Reliability in Cosmological Model Selection

**Citation:** Tan, M. Y. J. & Biswas, R. (2012). "The reliability of the AIC method in Cosmological Model Selection." Monthly Notices of the Royal Astronomical Society. arXiv:1105.5745 [astro-ph.CO].

**Summary:** Explores the impact of statistical errors in AIC estimation during model comparison for dark energy models. Uses parametric bootstrap to study distributions of AIC differences and success rates for different threshold parameters. Shows that investigating distributions of AIC differences (not just point estimates) is crucial for correct interpretation.

**Key Results:**
- AIC threshold of Δ=2 (commonly used) can be unreliable
- Distribution of AIC differences varies significantly across model pairs
- Bootstrap analysis reveals when AIC comparisons are trustworthy
- Recommends examining full distribution, not just point estimates

**Relevance to Our Work:** **DIRECTLY RELEVANT** to our AICc model selection for ZNE extrapolation. Their findings about AIC reliability with noisy data apply to our setting — ZNE data points are inherently noisy. We should consider: (1) using AICc (small-sample correction) as we do, (2) potentially reporting confidence in model selection, (3) being cautious about over-interpreting small AICc differences.

---

### 5.2 AICc (Corrected Akaike Information Criterion) — Foundational Reference

**Citation:** Hurvich, C. M. & Tsai, C.-L. (1989). "Regression and time series model selection in small samples." Biometrika, 76(2), 297–307.

**Summary:** Derives the bias correction to AIC for regression and autoregressive time series models. The correction (AICc = AIC + 2k²+2k/(n-k-1)) is particularly useful when sample size is small or when fitted parameters are a moderate-to-large fraction of sample size — exactly our ZNE setting where we have 3-7 noise levels and 2-4 model parameters.

**Key Results:**
- AICc correction prevents overfitting in small samples
- Converges to AIC as n→∞
- Critical when n/k < 40 (our ZNE setting: n=3-7, k=2-4)

**Relevance to Our Work:** **FOUNDATIONAL for our model selection.** With only 3-7 ZNE data points and 2-4 parameters per model, AICc correction is essential. Standard AIC would systematically favor overly complex models in our setting. This justifies our choice of AICc over AIC or BIC.

---

### 5.3 Burnham & Anderson — Model Selection Reference

**Citation:** Burnham, K. P. & Anderson, D. R. (2002). "Model Selection and Multimodel Inference: A Practical Information-Theoretic Approach." 2nd ed., Springer.

**Summary:** The definitive textbook on information-theoretic model selection. Establishes practical guidelines for AIC/AICc usage, multi-model averaging, and evidence ratios. Widely cited across sciences for justifying model selection methodology.

**Relevance to Our Work:** Provides the theoretical justification for our AICc-based model selection approach. Key principles we apply: (1) AICc for small samples, (2) Akaike weights for model averaging, (3) ΔAICc < 2 indicates substantial support for alternative models.

---

## 6. MCP (Model Context Protocol) in Scientific Computing

### 6.1 MCP Server for Quantum Execution

**Citation:** Shiraishi, M., Hamamura, I., Ishigaki, T., & Kadowaki, T. (2026). "A Model Context Protocol Server for Quantum Execution in Hybrid Quantum-HPC Environments." arXiv:2604.08318 [quant-ph]. Accepted at QC4C3 workshop, QCNC 2026.

**Summary:** Proposes an AI-driven framework using MCP to bridge the execution gap in quantum computing. Enables LLM agents to autonomously execute quantum workflows by invoking tools via MCP, including sampling and expectation value computation. Demonstrates with CUDA-Q on ABCI-Q hybrid platform and Quantinuum emulator.

**Key Results:**
- First MCP server specifically for quantum execution
- Supports OpenQASM interpretation pipeline
- Asynchronous execution on remote quantum hardware
- Validates AI agents can abstract hardware complexity

**Relevance to Our Work:** Demonstrates the emerging pattern of MCP-based quantum tool integration. Our quantum-noise-optimizer could be exposed as an MCP tool, allowing LLM agents to invoke our ZNE optimization as part of automated quantum workflows. This is a potential future integration path.

---

### 6.2 MCP for Science and HPC

**Citation:** Pan, H., Chard, R., Mello, R., Grams, C., He, T., Brace, A., Price Skelly, O., Engler, W., Holbrook, H., Oh, S. Y., Gonthier, M., Papka, M., Blaiszik, B., Chard, K., & Foster, I. (2025). "Experiences with Model Context Protocol Servers for Science and High Performance Computing." arXiv:2508.18489 [cs.DC].

**Summary:** Reports practical experience implementing MCP servers over mature scientific services (Globus Transfer, Compute, Search; facility status APIs; domain tools). Demonstrates use cases in computational chemistry, bioinformatics, quantum chemistry, and filesystem monitoring. Distills lessons learned for agent-led science.

**Key Results:**
- MCP as unifying interface for heterogeneous scientific CI
- Case studies across multiple scientific domains including quantum chemistry
- Identifies open challenges in evaluation and trust
- Pragmatic "thin server" approach over existing services

**Relevance to Our Work:** Validates MCP as the emerging standard for AI-scientific tool integration. Our project could benefit from an MCP interface layer, making our noise optimization tools discoverable and invokable by AI agents. Particularly relevant as quantum computing moves toward automated workflows.

---

## 7. NISQ Benchmarking (2025-2026)

### 7.1 Metriq: Collaborative Benchmarking Platform

**Citation:** (Unitary Fund, 2026). "A Collaborative Platform for Benchmarking Quantum Computers." arXiv:2603.08680.

**Summary:** Introduces Metriq, an open-source platform for reproducible cross-platform quantum benchmarking integrating benchmark definition, execution, data collection, and public presentation into a unified workflow.

**Relevance to Our Work:** Potential venue for publishing our ZNE benchmarks. Could submit our bounded ZNE results to Metriq for community comparison.

---

### 7.2 QEM Strategies for Variational PDE Circuits

**Citation:** Ukwatta Hewage, P. N. M., Chakkravarthy, M., & Abeysekara, R. K. (2026). "Quantum Error Mitigation Strategies for Variational PDE-Constrained Circuits on Noisy Hardware." arXiv:2604.10099 [quant-ph].

**Summary:** Systematic study of ZNE, PEC, and measurement error mitigation on variational circuits for PDEs (heat equation, Burgers', Saint-Venant). Demonstrates that physics-constrained circuits exhibit inherent noise resilience.

**Key Results:**
- ZNE reduces absolute error by 82-96% at low noise (p=0.001)
- Physics-constrained circuits maintain 25-47% higher fidelity than unconstrained
- PEC impractical beyond ~60 gates at p≥0.02
- Systematic errors dominate (43-58%) at all noise levels

**Relevance to Our Work:** Validates ZNE effectiveness on practical circuits and provides quantitative benchmarks. Their finding that physics constraints improve noise resilience supports our physically-bounded approach. The 82-96% error reduction at low noise is consistent with our +3.8% fidelity improvement (which is at higher noise levels).

---

## 8. Dynamical Decoupling (2025-2026)

### 8.1 Scalable QEM for Dynamical Decoupling

**Citation:** Ni, W., Li, Z., Qu, G., Equbal, A., Sun, Z., Dai, J., Shi, F., & Sun, L. (2025/2026). "Scalable quantum error mitigation for dynamical decoupling." arXiv:2511.12227 [quant-ph].

**Summary:** Presents Hadamard phase cycling, a scalable non-Markovian QEM method using group-structured phase configurations to filter spurious dynamics in DD sequences. Validated across molecular electron spins, NV centers, nuclear spins, trapped ions, and superconducting qubits.

**Key Results:**
- Reveals many reported "ultralong" decoherence times are artifacts
- Linear complexity scaling
- Cross-platform validation (5 different qubit technologies)
- Enables accurate decoherence time characterization

**Relevance to Our Work:** **DIRECTLY RELEVANT to v0.3.0 DD plans.** Their finding that DD can produce artifacts (coherence-population mixing) is critical — our DD implementation must account for this. Hadamard phase cycling could be integrated as a validation step for our DD sequences.

---

### 8.2 QEC + Dynamical Decoupling Combined

**Citation:** (2026). "Quantum Error Correction and Dynamical Decoupling." arXiv:2602.19042 [quant-ph].

**Summary:** Explores combining QEC/QED with DD to outperform either approach alone. Relevant to the trajectory from NISQ mitigation toward fault tolerance.

**Relevance to Our Work:** Forward-looking reference for how our DD implementation (v0.3.0) could eventually integrate with error correction as hardware improves.

---

### 8.3 Syncopated Dynamical Decoupling

**Citation:** (2024/2026). "Syncopated Dynamical Decoupling for Suppressing Crosstalk in Quantum Circuits." arXiv:2403.07836.

**Summary:** Develops syncopated DD technique that protects against decoherence while selectively targeting unwanted two-qubit interactions (crosstalk), addressing both decoherence and crosstalk simultaneously.

**Relevance to Our Work:** Relevant to our v0.3.0 DD implementation. Crosstalk suppression is important for multi-qubit circuits where our noise profiler identifies correlated errors.

---

## Summary Table

| Paper | Year | Method | Key Metric | Relevance |
|-------|------|--------|------------|-----------|
| Miranskyy et al. | 2026 | Bounded ZNE | 180K circuits, reduces unphysical predictions | **Direct predecessor** |
| Díez-Valle et al. | 2025 | PIE | 84 qubits, constant overhead | Complementary theory |
| Giurgica-Tiron et al. | 2020 | Digital ZNE | 18-24X error reduction | **Foundational** |
| Cai et al. | 2023 | Review | Comprehensive taxonomy | Background reference |
| LaRose et al. | 2022 | Mitiq software | ZNE/PEC/CDR toolkit | Primary comparison |
| Lowe et al. | 2021 | vnCDR | 33X improvement | Data-driven alternative |
| Mundada et al. | 2023 | Fire Opal | >1000X improvement | Commercial benchmark |
| Liao et al. | 2024 | ML-QEM | 100 qubits | ML alternative |
| Wang et al. | 2026 | GEM (GNN) | 16 qubits, zero-shot transfer | Physics-informed ML |
| Tan & Biswas | 2012 | AIC reliability | Bootstrap analysis | **Model selection theory** |
| Hurvich & Tsai | 1989 | AICc | Small-sample correction | **Core methodology** |
| Shiraishi et al. | 2026 | MCP+Quantum | First quantum MCP server | Future integration |
| Pan et al. | 2025 | MCP+Science | Multi-domain MCP | Architecture pattern |
| Ni et al. | 2025 | DD + QEM | Cross-platform, linear scaling | **v0.3.0 reference** |

---

## Key Takeaways for Our Project

1. **Our niche is clear:** Physically-bounded ZNE + AICc model selection fills a gap between simple ZNE (Mitiq) and heavy ML approaches. No existing work combines physical bounds with information-theoretic model selection.

2. **AICc is well-justified:** With 3-7 noise levels and 2-4 model parameters, we're firmly in the small-sample regime where AICc correction is essential (Hurvich & Tsai 1989).

3. **Scalability target:** PIE demonstrated 84 qubits, ML-QEM 100 qubits. Our approach should target similar scales.

4. **DD integration (v0.3.0):** Must account for artifacts identified by Ni et al. (2025). Hadamard phase cycling is a potential validation tool.

5. **MCP opportunity:** Emerging MCP standard for quantum tools (Shiraishi et al. 2026) suggests our optimizer could be exposed as an MCP tool for AI-driven quantum workflows.

6. **Benchmarking:** Should submit results to Metriq platform and compare against Mitiq's standard ZNE, Fire Opal (if accessible), and the bounded ZNE results from Miranskyy et al.
