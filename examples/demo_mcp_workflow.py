"""End-to-end demo: AI agent using Quantum Noise Intelligence MCP tools.

Simulates what happens when Claude/Cursor/Grok calls our MCP server
to optimize and mitigate errors in a quantum circuit.
"""
import sys
sys.path.insert(0, "src")
sys.path.insert(0, ".")

from mcp_server.server import (
    noise_profile, recommend_mitigation, run_bounded_zne,
    compare_strategies, wukong_status, optimize_circuit,
)

print("=" * 60)
print("  AI Agent Workflow: Quantum Noise Intelligence MCP")
print("=" * 60)

# Step 1: Agent checks hardware status
print("\n📡 Step 1: Agent checks Wukong 180 status")
status = wukong_status()
print(f"   Backend: {status['backend']}")
print(f"   Qubits: {status['qubits']}, CZ gates: {status['cz_gates']}")
print(f"   Online: {status['online']}")
print(f"   Best qubits: {status.get('best_qubits', 'N/A')}")

# Step 2: Agent gets noise profile
print("\n🔍 Step 2: Agent queries noise profile")
profile = noise_profile("aer_simulator", 5)
print(f"   1Q error: {profile['avg_1q_error']}")
print(f"   2Q error: {profile['avg_2q_error']}")
print(f"   Readout: {profile['avg_readout_error']}")

# Step 3: Agent optimizes a circuit
print("\n⚡ Step 3: Agent optimizes a quantum circuit")
qasm = """OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
creg c[4];
h q[0];
cx q[0],q[1];
cx q[1],q[2];
cx q[2],q[3];
h q[0]; h q[0];
cx q[0],q[1]; cx q[0],q[1];
barrier q;
measure q -> c;
"""
opt = optimize_circuit(qasm, "medium")
print(f"   Original: {opt['original']['total_gates']} gates, depth {opt['original']['depth']}")
print(f"   Optimized: {opt['optimized']['total_gates']} gates, depth {opt['optimized']['depth']}")
print(f"   Reduction: {opt['reduction']}")

# Step 4: Agent gets mitigation recommendation
print("\n🎯 Step 4: Agent asks for mitigation strategy")
rec = recommend_mitigation(n_qubits=4, depth=5, n_cx=3, noise_level="medium")
print(f"   Strategy: {rec['strategy']}")
print(f"   Reason: {rec['reason']}")

# Step 5: Agent runs bounded ZNE with measured data
print("\n📊 Step 5: Agent runs Physically-Bounded ZNE")
zne_result = run_bounded_zne(
    scale_factors=[1.0, 1.3, 1.6, 2.0, 2.5],
    expectation_values=[0.82, 0.71, 0.62, 0.50, 0.39],
    observable_bounds=[-1.0, 1.0],
)
print(f"   Raw value: {zne_result['raw_value']}")
print(f"   Zero-noise estimate: {zne_result['zero_noise_estimate']}")
print(f"   Model selected: {zne_result['model_selected']}")
print(f"   Bounds enforced: {zne_result['bounds_enforced']}")

# Step 6: Agent compares all strategies
print("\n🏆 Step 6: Agent benchmarks all methods")
comp = compare_strategies(n_qubits=4, circuit_type="ghz", noise_level="medium")
print(f"   Circuit: {comp['circuit']}-{comp['n_qubits']}, noise={comp['noise_level']}")
print(f"   Ideal: {comp['ideal']}")
for method, data in comp["methods"].items():
    print(f"   {method:15s}: value={data['value']:.4f}, error={data['error']:.4f}")
print(f"   Winner: {comp['winner']}")

print("\n" + "=" * 60)
print("  ✅ All 6 MCP tools demonstrated successfully!")
print("  This is what AI agents see when they call our server.")
print("=" * 60)
