#!/usr/bin/env python3
"""Auto-retry hardware job until success. Runs in background.

Usage: nohup python3 scripts/hardware_retry.py &
Check: cat results/hardware_final_result.json
Log:   tail -f results/hardware_retry.log
"""
import sys, json, time, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from pyqpanda3 import qcloud, core, transpilation, quantum_info

API_KEY = "53a22e9d46d614d8a980cae6e4ddda2bb59f3f7f70286e5a106005ec3e4c399f446f43656e5971504863396654716865"
RESULT_FILE = os.path.join(os.path.dirname(__file__), '..', 'results', 'hardware_final_result.json')
LOG_FILE = os.path.join(os.path.dirname(__file__), '..', 'results', 'hardware_retry.log')

MAX_RETRIES = 50
WAIT_BETWEEN_RETRIES = 300  # 5 minutes between retries


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, 'a') as f:
        f.write(line + '\n')


def attempt_hardware_job():
    """Submit GHZ-3 on optimal qubits to Wukong 180. Returns result or None."""
    svc = qcloud.QCloudService(API_KEY)
    backends = svc.backends()
    if not backends.get('WK_C180'):
        log("WK_C180 offline, skipping")
        return None

    backend = svc.backend('WK_C180')
    chip = backend.chip_backend()
    t = transpilation.Transpiler()
    opts = qcloud.QCloudOptions()

    # GHZ-3 on optimal qubits (78, 88, 97)
    prog = core.QProg()
    prog << core.H(78) << core.CNOT(78, 88) << core.CNOT(88, 97)
    prog << core.measure([78, 88, 97], [0, 1, 2])
    prog_t = t.transpile(prog, chip)
    instr = prog_t.to_instruction(chip)

    log(f"Submitting GHZ-3 (qubits 78,88,97)...")
    job = backend.run_instruction(instr, 1000, opts)
    job_id = job.job_id()
    log(f"Job completed! ID: {job_id}")

    r = job.result()
    probs = r.get_probs()
    timing = r.timing_info()

    # Calculate fidelity
    ideal = {'000': 0.5, '111': 0.5}
    fid = quantum_info.hellinger_fidelity(ideal, probs) if probs else 0

    result = {
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'backend': 'WK_C180 (Origin Wukong 180)',
        'job_id': job_id,
        'circuit': 'GHZ-3',
        'qubits': [78, 88, 97],
        'qubit_selection': 'calibration-aware (best T2 + readout + CZ fidelity)',
        'shots': 1000,
        'probs': probs,
        'fidelity': fid,
        'timing': timing,
        'status': 'COMPLETED_ON_REAL_HARDWARE'
    }
    return result


def main():
    log("=" * 50)
    log("HARDWARE AUTO-RETRY STARTED")
    log(f"Max retries: {MAX_RETRIES}, interval: {WAIT_BETWEEN_RETRIES}s")
    log("=" * 50)

    for attempt in range(1, MAX_RETRIES + 1):
        log(f"Attempt {attempt}/{MAX_RETRIES}")
        try:
            result = attempt_hardware_job()
            if result:
                with open(RESULT_FILE, 'w') as f:
                    json.dump(result, f, indent=2)
                log(f"SUCCESS! Fidelity: {result['fidelity']:.4f}")
                log(f"Probs: {result['probs']}")
                log(f"Saved to {RESULT_FILE}")
                log("=" * 50)
                return
        except Exception as e:
            log(f"Failed: {type(e).__name__}: {e}")

        if attempt < MAX_RETRIES:
            log(f"Waiting {WAIT_BETWEEN_RETRIES}s before next attempt...")
            time.sleep(WAIT_BETWEEN_RETRIES)

    log("All retries exhausted. Hardware not available.")


if __name__ == '__main__':
    main()
