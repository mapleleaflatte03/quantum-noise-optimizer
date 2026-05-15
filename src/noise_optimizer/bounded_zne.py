"""Physically Bounded Zero-Noise Extrapolation.

Based on arXiv:2604.24475 (Miranskyy et al., Apr 2026).
Constrains extrapolation to physically valid range during optimization,
preventing unphysical predictions and improving stability.

Key insight: Standard ZNE can extrapolate outside [-1,1] for Pauli observables.
Bounded ZNE enforces Ê(0) ∈ [lower_bound, upper_bound] during fitting.
"""

import numpy as np
from scipy.optimize import minimize


class PhysicallyBoundedZNE:
    """Physically bounded ZNE with multiple model families.

    Models supported:
    - polynomial: Ê(λ) = θ₀ + θ₁λ + ... + θ_d λ^d, bounded θ₀ ∈ [lb, ub]
    - exponential: Ê(λ) = a + (ζ-a)·exp(-cλ), bounded ζ,a ∈ [lb, ub]
    - poly_exp: Ê(λ) = a + (ζ-a)·exp(c₁λ + c₂λ²+...), bounded ζ,a ∈ [lb, ub]
    """

    def __init__(self, bounds=(-1.0, 1.0), model="poly_exp", degree=1):
        self.lb, self.ub = bounds
        self.model = model
        self.degree = degree
        self.params_ = None
        self.zero_noise_estimate_ = None

    def fit(self, scale_factors, expectation_values):
        """Fit bounded model to (scale_factor, expectation_value) data.

        Args:
            scale_factors: noise amplification factors [1, 2, 3, ...]
            expectation_values: measured <O> at each noise level
        """
        x = np.array(scale_factors, dtype=float)
        y = np.array(expectation_values, dtype=float)

        if self.model == "polynomial":
            self.params_ = self._fit_polynomial(x, y)
        elif self.model == "exponential":
            self.params_ = self._fit_exponential(x, y)
        elif self.model == "poly_exp":
            self.params_ = self._fit_poly_exp(x, y)
        else:
            raise ValueError(f"Unknown model: {self.model}")

        self.zero_noise_estimate_ = self.predict(0.0)
        return self

    def predict(self, scale_factor):
        """Predict expectation value at given noise scale."""
        if self.params_ is None:
            raise RuntimeError("Must call fit() first")

        x = float(scale_factor)
        if self.model == "polynomial":
            return sum(self.params_[i] * x**i for i in range(len(self.params_)))
        elif self.model == "exponential":
            zeta, a, c = self.params_
            return a + (zeta - a) * np.exp(-c * x)
        elif self.model == "poly_exp":
            zeta, a = self.params_[0], self.params_[1]
            coeffs = self.params_[2:]
            r = sum(coeffs[i] * x**(i+1) for i in range(len(coeffs)))
            return a + (zeta - a) * np.exp(r)

    def _fit_polynomial(self, x, y):
        """Bounded polynomial: constrain θ₀ ∈ [lb, ub]."""
        d = self.degree
        n_params = d + 1

        def objective(params):
            pred = sum(params[i] * x**i for i in range(n_params))
            return np.sum((y - pred)**2)

        # Bounds: θ₀ bounded, rest unbounded
        bounds = [(self.lb, self.ub)] + [(-np.inf, np.inf)] * d
        x0 = np.polyfit(x, y, d)[::-1]  # initial guess from unconstrained fit
        x0[0] = np.clip(x0[0], self.lb, self.ub)

        result = minimize(objective, x0, method='L-BFGS-B', bounds=bounds)
        return result.x

    def _fit_exponential(self, x, y):
        """Bounded exponential: Ê(λ) = a + (ζ-a)·exp(-cλ), ζ,a ∈ [lb,ub], c>0."""
        def objective(params):
            zeta, a, c = params
            pred = a + (zeta - a) * np.exp(-c * x)
            return np.sum((y - pred)**2)

        # Initial guess
        zeta0 = np.clip(y[0] + (y[0] - y[-1]) * 0.5, self.lb, self.ub)
        a0 = np.clip(y[-1] * 0.5, self.lb, self.ub)
        c0 = 0.5

        bounds = [(self.lb, self.ub), (self.lb, self.ub), (1e-6, 10.0)]
        result = minimize(objective, [zeta0, a0, c0], method='L-BFGS-B', bounds=bounds)
        return result.x

    def _fit_poly_exp(self, x, y):
        """Bounded poly-exponential: Ê(λ) = a + (ζ-a)·exp(c₁λ + c₂λ²+...)."""
        d = self.degree

        def objective(params):
            zeta, a = params[0], params[1]
            coeffs = params[2:]
            r = sum(coeffs[i] * x**(i+1) for i in range(d))
            pred = a + (zeta - a) * np.exp(r)
            return np.sum((y - pred)**2)

        # Initial guess
        zeta0 = np.clip(y[0] + (y[0] - y[-1]) * 0.3, self.lb, self.ub)
        a0 = 0.0
        c0 = [-0.1] * d

        bounds = [(self.lb, self.ub), (self.lb, self.ub)] + [(-5.0, 5.0)] * d
        x0 = [zeta0, a0] + c0
        result = minimize(objective, x0, method='L-BFGS-B', bounds=bounds)
        return result.x


def auto_select_model(scale_factors, expectation_values, bounds=(-1.0, 1.0)):
    """Automatically select the best bounded ZNE model.

    Tries all model families and returns the one with lowest residual error.
    This is our novel contribution: automated physics-informed model selection.
    """
    x = np.array(scale_factors)
    y = np.array(expectation_values)

    candidates = [
        ("polynomial_d1", PhysicallyBoundedZNE(bounds, "polynomial", 1)),
        ("polynomial_d2", PhysicallyBoundedZNE(bounds, "polynomial", 2)),
        ("exponential", PhysicallyBoundedZNE(bounds, "exponential", 1)),
        ("poly_exp_d1", PhysicallyBoundedZNE(bounds, "poly_exp", 1)),
        ("poly_exp_d2", PhysicallyBoundedZNE(bounds, "poly_exp", 2)),
    ]

    best_name, best_model, best_residual = None, None, np.inf
    for name, model in candidates:
        try:
            model.fit(x, y)
            pred = np.array([model.predict(xi) for xi in x])
            residual = np.sum((y - pred)**2)
            if residual < best_residual:
                best_name, best_model, best_residual = name, model, residual
        except Exception:
            continue

    return best_name, best_model
