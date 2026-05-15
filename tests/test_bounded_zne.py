import sys
sys.path.insert(0, 'src')

import numpy as np
import pytest
from noise_optimizer.bounded_zne import PhysicallyBoundedZNE, auto_select_model
from noise_optimizer.auto_mitigator import AutoMitigator
from qiskit.circuit import QuantumCircuit


# --- bounded_zne.py tests ---

def test_polynomial_fit_within_bounds():
    scales = [1, 2, 3, 4, 5]
    values = [0.8, 0.6, 0.4, 0.2, 0.1]
    zne = PhysicallyBoundedZNE(bounds=(-1, 1), model="polynomial", degree=2)
    zne.fit(scales, values)
    est = zne.zero_noise_estimate_
    assert -1.0 <= est <= 1.0


def test_exponential_fit_within_bounds():
    scales = [1, 2, 3, 4, 5]
    values = [0.7, 0.5, 0.35, 0.25, 0.2]
    zne = PhysicallyBoundedZNE(bounds=(-1, 1), model="exponential", degree=1)
    zne.fit(scales, values)
    est = zne.zero_noise_estimate_
    assert -1.0 <= est <= 1.0


def test_poly_exp_fit_within_bounds():
    scales = [1, 2, 3, 4, 5]
    values = [0.75, 0.55, 0.38, 0.27, 0.18]
    zne = PhysicallyBoundedZNE(bounds=(-1, 1), model="poly_exp", degree=1)
    zne.fit(scales, values)
    est = zne.zero_noise_estimate_
    assert -1.0 <= est <= 1.0


def test_auto_select_picks_simple_model():
    scales = [1, 2, 3]
    values = [0.8, 0.5, 0.3]
    name, model = auto_select_model(scales, values)
    # With only 3 data points, AICc should prefer models with fewer params
    assert name in ("polynomial_d1", "exponential", "poly_exp_d1")
    assert "d2" not in name


def test_bounds_enforced_extreme_data():
    scales = [1, 2, 3, 4, 5]
    values = [0.95, 0.9, 0.85, 0.82, 0.8]  # barely decaying -> extrapolation could exceed 1
    zne = PhysicallyBoundedZNE(bounds=(-1, 1), model="polynomial", degree=2)
    zne.fit(scales, values)
    est = zne.zero_noise_estimate_
    assert -1.0 <= est <= 1.0


def test_predict_before_fit_raises():
    zne = PhysicallyBoundedZNE(bounds=(-1, 1), model="polynomial", degree=1)
    with pytest.raises(RuntimeError):
        zne.predict(0.0)


# --- auto_mitigator.py tests ---

def test_analyze_circuit_basic():
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    am = AutoMitigator()
    props = am.analyze_circuit(qc)
    for key in ('depth', 'n_qubits', 'n_cx', 'n_1q', 'cx_density', 'idle_periods'):
        assert key in props


def test_recommend_high_cx_density():
    qc = QuantumCircuit(2)
    for _ in range(5):
        qc.cx(0, 1)
    am = AutoMitigator()
    rec = am.recommend(qc, noise_profile={'avg_2q_error': 0.02, 'avg_readout_error': 0.01, 't2': 200e-6})
    assert rec['strategy'] == 'bounded_zne'


def test_recommend_low_noise():
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    am = AutoMitigator()
    rec = am.recommend(qc, noise_profile={'avg_2q_error': 0.001, 'avg_readout_error': 0.001})
    assert rec['strategy'] == 'none'


def test_recommend_high_readout():
    qc = QuantumCircuit(2)
    qc.h(0)
    qc.cx(0, 1)
    am = AutoMitigator()
    rec = am.recommend(qc, noise_profile={'avg_2q_error': 0.003, 'avg_readout_error': 0.08, 't2': 200e-6})
    assert rec['strategy'] == 'readout_mitigation'
