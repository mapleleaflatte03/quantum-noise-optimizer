#!/usr/bin/env python3
"""Hardware experiment: Compare baseline vs optimized circuits on Wukong 180.

Submits multiple jobs to build a publishable comparison:
1. GHZ-3 on DEFAULT qubits (0,10,11) — baseline
2. GHZ-3 on OPTIMAL qubits (78,88,97) — calibration-selected
3. Bell on DEFAULT qubits — baseline
4. Bell on OPTIMAL qubits — calibration-selected

Auto-retries until all jobs complete. Results saved for paper.

Usage: nohup python3 scripts/hardware_experiment.py &
"""
import sys, json, time, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pyqpanda3 import qcloud, core, transpilation, quantum_info

API_KEY = "53a22e9d46d614d8a980cae6e4ddda2bb59f3f7f70286e5a106005ec3e4c399f446f43656e5971504863396654716865"
BASE_DIR = os.path.join(os.path.dirname(__file__), '..', 'results')
RESULT_FILE = os.path.join(BASE_DIR, 'hardware_experiment_results.json')
LOG_FILE = os.path.join(BASE_DIR, 'hardware_experiment.log')

MAX_RETRIES = 30
WAIT_BETWEEN = 300  # 5 min


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')


def run_job(backend, chip, transpiler, circuit_name, prog, shots=1000):
    """Submit one job and return result dict."""
    opts = qcloud.QCloudOptions()
    prog_t = transpiler.transpile(prog, chip)
    instr = prog_t.to_instruction(chip)

    log(f"  Submitting {circuit_name}...")
    job = backend.run_instruction(instr, shots, opts)
    log(f"  Job ID: {job.job_id()}")

    r = job.result()
    probs = r.get_probs()
    timing = r.timing_info()

    return {
        'circuit': circuit_name,
        'job_id': job.job_id(),
        'probs': probs,
        'timing': timing,
        'shots': shots,
    }


def build_experiments():
    """Define all circuits to run."""
    experiments = []

    # 1. Bell baseline (qubits 0, 10 — default transpiler mapping)
    prog = core.QProg()
    prog << core.H(0) << core.CNOT(0, 1) << core.measure([0, 1], [0, 1])
    experiments.append(('Bell_baseline', prog, {'00': 0.5, '11': 0.5}))

    # 2. Bell optimal (qubits 78, 88 — high T2 + readout)
    prog = core.QProg()
    prog << core.H(78) << core.CNOT(78, 88) << core.measure([78, 88], [0, 1])
    experiments.append(('Bell_optimal_q78_q88', prog, {'00': 0.5, '11': 0.5}))

    # 3. GHZ-3 baseline
    prog = core.QProg()
    prog << core.H(0) << core.CNOT(0, 1) << core.CNOT(1, 2) << core.measure([0, 1, 2], [0, 1, 2])
    experiments.append(('GHZ3_baseline', prog, {'000': 0.5, '111': 0.5}))

    # 4. GHZ-3 optimal (qubits 78, 88, 97)
    prog = core.QProg()
    prog << core.H(78) << core.CNOT(78, 88) << core.CNOT(88, 97) << core.measure([78, 88, 97], [0, 1, 2])
    experiments.append(('GHZ3_optimal_q78_q88_q97', prog, {'000': 0.5, '111': 0.5}))

    return experiments


def main():
    log("=" * 60)
    log("HARDWARE EXPERIMENT: Baseline vs Calibration-Optimized")
    log("Target: Origin Wukong 180 (superconducting, 180 qubits)")
    log("=" * 60)

    experiments = build_experiments()
    all_results = {'timestamp': '', 'backend': 'WK_C180', 'experiments': []}

    for attempt in range(1, MAX_RETRIES + 1):
        log(f"\nAttempt {attempt}/{MAX_RETRIES}")
        try:
            svc = qcloud.QCloudService(API_KEY)
            if not svc.backends().get('WK_C180'):
                log("WK_C180 offline")
                raise RuntimeError("offline")

            backend = svc.backend('WK_C180')
            chip = backend.chip_backend()
            t = transpilation.Transpiler()

            results = []
            for name, prog, ideal in experiments:
                r = run_job(backend, chip, t, name, prog, shots=1000)
                # Calculate fidelity
                fid = quantum_info.hellinger_fidelity(ideal, r['probs']) if r['probs'] else 0
                r['ideal'] = ideal
                r['fidelity'] = fid
                log(f"  {name}: fidelity={fid:.4f}, probs={r['probs']}")
                results.append(r)

            # All jobs completed!
            all_results['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S')
            all_results['experiments'] = results

            # Summary
            log("\n" + "=" * 60)
            log("EXPERIMENT COMPLETE — RESULTS")
            log("=" * 60)
            for r in results:
                log(f"  {r['circuit']}: fidelity={r['fidelity']:.4f}")

            # Comparison
            bell_base = next((r for r in results if 'Bell_baseline' in r['circuit']), None)
            bell_opt = next((r for r in results if 'Bell_optimal' in r['circuit']), None)
            ghz_base = next((r for r in results if 'GHZ3_baseline' in r['circuit']), None)
            ghz_opt = next((r for r in results if 'GHZ3_optimal' in r['circuit']), None)

            if bell_base and bell_opt:
                imp = ((bell_opt['fidelity'] - bell_base['fidelity']) / bell_base['fidelity']) * 100
                log(f"\n  Bell improvement (optimal vs baseline): {imp:+.2f}%")
                all_results['bell_improvement_pct'] = imp

            if ghz_base and ghz_opt:
                imp = ((ghz_opt['fidelity'] - ghz_base['fidelity']) / ghz_base['fidelity']) * 100
                log(f"  GHZ-3 improvement (optimal vs baseline): {imp:+.2f}%")
                all_results['ghz3_improvement_pct'] = imp

            # Save
            with open(RESULT_FILE, 'w') as f:
                json.dump(all_results, f, indent=2)
            log(f"\nSaved to {RESULT_FILE}")
            log("SUCCESS!")
            return

        except Exception as e:
            log(f"Failed: {type(e).__name__}: {e}")
            if attempt < MAX_RETRIES:
                log(f"Waiting {WAIT_BETWEEN}s...")
                time.sleep(WAIT_BETWEEN)

    log("All retries exhausted.")


if __name__ == '__main__':
    main()
