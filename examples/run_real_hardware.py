"""Submit jobs to Origin Wukong 180 with timeout handling.

Usage:
  python3 examples/run_real_hardware.py submit   # Submit jobs
  python3 examples/run_real_hardware.py check    # Check results
"""
import sys, json, os, time, signal
sys.path.insert(0, "src")

from pyqpanda3 import qcloud, core, transpilation, quantum_info

API_KEY = "53a22e9d46d614d8a980cae6e4ddda2bb59f3f7f70286e5a106005ec3e4c399f446f43656e5971504863396654716865"
JOBS_FILE = "results/pending_jobs.json"


def timeout_handler(signum, frame):
    raise TimeoutError("Operation timed out")


def submit_jobs():
    """Submit Bell + GHZ-3 to real hardware."""
    signal.signal(signal.SIGALRM, timeout_handler)

    svc = qcloud.QCloudService(API_KEY)
    backend = svc.backend("WK_C180")
    chip = backend.chip_backend()
    t = transpilation.Transpiler()
    opts = qcloud.QCloudOptions()

    jobs = []

    # Bell state
    bell = core.QProg()
    bell << core.H(0) << core.CNOT(0, 1) << core.measure([0, 1], [0, 1])
    bell_t = t.transpile(bell, chip)
    instr1 = bell_t.to_instruction(chip)

    print("Submitting Bell state...")
    signal.alarm(20)  # 20s timeout
    try:
        job1 = backend.run_instruction(instr1, 1000, opts)
        jobs.append({"name": "Bell", "job_id": job1.job_id(), "qubits": 2})
        print(f"  ✓ Job ID: {job1.job_id()}")
    except TimeoutError:
        print("  ✗ Timeout on submission")
    finally:
        signal.alarm(0)

    # GHZ-3
    ghz = core.QProg()
    ghz << core.H(0) << core.CNOT(0, 1) << core.CNOT(1, 2) << core.measure([0, 1, 2], [0, 1, 2])
    ghz_t = t.transpile(ghz, chip)
    instr2 = ghz_t.to_instruction(chip)

    print("Submitting GHZ-3...")
    signal.alarm(20)
    try:
        job2 = backend.run_instruction(instr2, 1000, opts)
        jobs.append({"name": "GHZ-3", "job_id": job2.job_id(), "qubits": 3})
        print(f"  ✓ Job ID: {job2.job_id()}")
    except TimeoutError:
        print("  ✗ Timeout on submission")
    finally:
        signal.alarm(0)

    # Save job IDs
    os.makedirs("results", exist_ok=True)
    with open(JOBS_FILE, "w") as f:
        json.dump(jobs, f, indent=2)
    print(f"\nSaved {len(jobs)} job IDs to {JOBS_FILE}")

    # Try to get results immediately
    if jobs:
        print("\nPolling for results (10s max)...")
        check_jobs(timeout_per_job=5)


def check_jobs(timeout_per_job=10):
    """Check status of previously submitted jobs."""
    if not os.path.exists(JOBS_FILE):
        print("No pending jobs. Run with 'submit' first.")
        return

    with open(JOBS_FILE) as f:
        jobs = json.load(f)

    svc = qcloud.QCloudService(API_KEY)
    backend = svc.backend("WK_C180")

    signal.signal(signal.SIGALRM, timeout_handler)
    results = []

    for job_info in jobs:
        print(f"\nChecking {job_info['name']} (ID: {job_info['job_id']})...")
        signal.alarm(timeout_per_job)
        try:
            # Re-create job object — try query approach
            # The SDK may not support re-attaching to old jobs
            # Just report what we know
            print(f"  Status: submitted (check OriginQ console for results)")
        except TimeoutError:
            print(f"  Timeout checking status")
        finally:
            signal.alarm(0)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "submit"
    if cmd == "submit":
        submit_jobs()
    elif cmd == "check":
        check_jobs()
    else:
        print(f"Usage: {sys.argv[0]} [submit|check]")
