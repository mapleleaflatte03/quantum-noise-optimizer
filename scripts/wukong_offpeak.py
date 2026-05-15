"""Smart Wukong 180 hardware submission with off-peak detection.

Strategy:
- Off-peak hours for China (UTC+8): 22:00-08:00 CST = 14:00-00:00 UTC
- Uses signal-based timeout (not blocking forever)
- Submits multiple circuit variants for bounded ZNE comparison
- Saves results immediately on success

Usage:
  nohup python3 scripts/wukong_offpeak.py &
  tail -f results/wukong_offpeak.log
"""
import sys, os, json, time, signal
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

API_KEY = "53a22e9d46d614d8a980cae6e4ddda2bb59f3f7f70286e5a106005ec3e4c399f446f43656e5971504863396654716865"
LOG = os.path.join(os.path.dirname(__file__), '..', 'results', 'wukong_offpeak.log')
RESULT = os.path.join(os.path.dirname(__file__), '..', 'results', 'wukong_hardware_data.json')
TIMEOUT_SEC = 90  # Kill job after 90s (queue shouldn't take this long if off-peak)


class TimeoutError(Exception):
    pass


def timeout_handler(signum, frame):
    raise TimeoutError("Job timed out")


def log(msg):
    ts = time.strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG, 'a') as f:
        f.write(line + '\n')


def is_offpeak():
    """Check if current time is off-peak for China (22:00-08:00 CST)."""
    utc_now = datetime.now(timezone.utc)
    cst_hour = (utc_now.hour + 8) % 24
    return cst_hour >= 22 or cst_hour < 8


def submit_job(circuit_name, prog, qubits):
    """Submit a single job with timeout."""
    from pyqpanda3 import qcloud, core, transpilation, quantum_info

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(TIMEOUT_SEC)

    try:
        svc = qcloud.QCloudService(API_KEY)
        backend = svc.backend('WK_C180')
        chip = backend.chip_backend()
        t = transpilation.Transpiler()
        opts = qcloud.QCloudOptions()

        prog_t = t.transpile(prog, chip)
        instr = prog_t.to_instruction(chip)

        log(f"  Submitting {circuit_name} (qubits {qubits})...")
        job = backend.run_instruction(instr, 1000, opts)
        job_id = job.job_id()
        log(f"  Job ID: {job_id}, waiting for result...")

        r = job.result()
        probs = r.get_probs()
        signal.alarm(0)  # Cancel timeout

        log(f"  ✓ Got result! Probs: {probs}")
        return {'job_id': job_id, 'probs': probs, 'circuit': circuit_name, 'qubits': qubits}

    except TimeoutError:
        signal.alarm(0)
        log(f"  ✗ Timeout after {TIMEOUT_SEC}s (queue still busy)")
        return None
    except Exception as e:
        signal.alarm(0)
        log(f"  ✗ Error: {type(e).__name__}: {e}")
        return None


def main():
    from pyqpanda3 import core

    log("=" * 50)
    log("WUKONG OFF-PEAK SMART SUBMISSION")
    log(f"Timeout: {TIMEOUT_SEC}s per job")
    log(f"Off-peak check: China 22:00-08:00 CST")
    log("=" * 50)

    # Circuits to submit
    circuits = []

    # GHZ-3 on best qubits
    prog = core.QProg()
    prog << core.H(78) << core.CNOT(78, 88) << core.CNOT(88, 97)
    prog << core.measure([78, 88, 97], [0, 1, 2])
    circuits.append(("GHZ-3", prog, [78, 88, 97]))

    # Bell pair
    prog2 = core.QProg()
    prog2 << core.H(78) << core.CNOT(78, 88)
    prog2 << core.measure([78, 88], [0, 1])
    circuits.append(("Bell", prog2, [78, 88]))

    max_attempts = 24  # Try for up to 12 hours (every 30 min)
    results = []

    for attempt in range(1, max_attempts + 1):
        offpeak = is_offpeak()
        cst_hour = (datetime.now(timezone.utc).hour + 8) % 24
        log(f"\nAttempt {attempt}/{max_attempts} (CST hour: {cst_hour:02d}:00, {'OFF-PEAK ✓' if offpeak else 'PEAK ✗'})")

        if not offpeak:
            wait = 1800  # 30 min during peak
            log(f"  Peak hours — waiting {wait//60} min for off-peak...")
            time.sleep(wait)
            continue

        for name, prog, qubits in circuits:
            result = submit_job(name, prog, qubits)
            if result:
                result['timestamp'] = time.strftime('%Y-%m-%d %H:%M:%S UTC')
                result['attempt'] = attempt
                results.append(result)

        if results:
            with open(RESULT, 'w') as f:
                json.dump(results, f, indent=2)
            log(f"\n✓ SUCCESS! {len(results)} results saved to {RESULT}")
            break

        # Wait 30 min before retry
        log(f"  Waiting 30 min before next attempt...")
        time.sleep(1800)

    if not results:
        log("\nAll attempts exhausted. No hardware data obtained.")


if __name__ == '__main__':
    main()
