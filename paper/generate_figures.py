"""Generate publication-quality figures for the arXiv paper."""
import json
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# Load data
with open(Path(__file__).parent.parent / "results" / "paper_benchmark.json") as f:
    data = json.load(f)

results = data["results"]
metrics = data["metrics"]

# Matplotlib settings
plt.rcParams.update({
    "font.size": 8,
    "axes.labelsize": 9,
    "figure.figsize": (3.4, 2.5),
    "font.family": "serif",
    "text.usetex": False,
    "axes.facecolor": "white",
    "figure.facecolor": "white",
    "axes.grid": False,
})

COLORS = {"raw": "#0072B2", "linear": "#E69F00", "quadratic": "#009E73", "bounded": "#D55E00"}
LABELS = {"raw": "Raw", "linear": "Linear ZNE", "quadratic": "Quadratic ZNE", "bounded": "Bounded ZNE"}
OUTDIR = Path(__file__).parent / "figures"
OUTDIR.mkdir(exist_ok=True)

# --- Figure 1: MAE Comparison Bar Chart ---
fig, ax = plt.subplots()
methods = ["raw", "linear", "quadratic", "bounded"]

# Compute per-result absolute errors for error bars
errors_per_method = {}
for m in methods:
    key = m if m in ("raw",) else f"{m}_zne"
    ae = [abs(r[key] - r["ideal"]) for r in results]
    errors_per_method[m] = ae

maes = [np.mean(errors_per_method[m]) for m in methods]
stds = [np.std(errors_per_method[m]) / np.sqrt(len(errors_per_method[m])) for m in methods]

bars = ax.bar(range(4), maes, yerr=stds, color=[COLORS[m] for m in methods],
              edgecolor="black", linewidth=0.5, capsize=3)
ax.set_xticks(range(4))
ax.set_xticklabels([LABELS[m] for m in methods])
ax.set_ylabel("Mean Absolute Error")
ax.set_ylim(bottom=0)
plt.tight_layout()
fig.savefig(OUTDIR / "fig_mae_comparison.pdf", bbox_inches="tight")
plt.close(fig)

# --- Figure 2: Noise Scaling Line Plot ---
fig, ax = plt.subplots()
noise_levels = ["0.01", "0.03", "0.05", "0.08", "0.12"]
noise_pct = [1, 3, 5, 8, 12]
linestyles = {"raw": "-", "linear": "--", "quadratic": "-.", "bounded": ":"}
markers = {"raw": "o", "linear": "s", "quadratic": "^", "bounded": "D"}

for m in methods:
    key = f"mae_{m}"
    vals = [metrics["per_noise"][nl][key] for nl in noise_levels]
    ax.plot(noise_pct, vals, color=COLORS[m], linestyle=linestyles[m],
            marker=markers[m], markersize=4, linewidth=1.2, label=LABELS[m])

ax.set_xlabel("CX Error Rate (%)")
ax.set_ylabel("Mean Absolute Error")
ax.set_xticks(noise_pct)
ax.legend(fontsize=7, framealpha=0.9)
ax.set_ylim(bottom=0)
plt.tight_layout()
fig.savefig(OUTDIR / "fig_noise_scaling.pdf", bbox_inches="tight")
plt.close(fig)

# --- Figure 3: Unphysical Rate Bar Chart ---
fig, ax = plt.subplots()
x = np.arange(len(noise_levels))
width = 0.2

# raw has no unphysical (expectation values from simulation), compute from data
unphys = {"raw": [], "linear": [], "quadratic": [], "bounded": []}
for nl in noise_levels:
    subset = [r for r in results if str(r["p_cx"]) == nl]
    n = len(subset)
    unphys["raw"].append(sum(1 for r in subset if abs(r["raw"]) > 1) / n * 100)
    unphys["linear"].append(sum(1 for r in subset if abs(r["linear_zne"]) > 1) / n * 100)
    unphys["quadratic"].append(sum(1 for r in subset if abs(r["quadratic_zne"]) > 1) / n * 100)
    unphys["bounded"].append(sum(1 for r in subset if abs(r["bounded_zne"]) > 1) / n * 100)

for i, m in enumerate(methods):
    ax.bar(x + i * width, unphys[m], width, color=COLORS[m], edgecolor="black",
           linewidth=0.5, label=LABELS[m])

ax.set_xlabel("CX Error Rate (%)")
ax.set_ylabel("Unphysical Rate (%)")
ax.set_xticks(x + 1.5 * width)
ax.set_xticklabels([f"{p}%" for p in noise_pct])
ax.legend(fontsize=7, framealpha=0.9)
ax.set_ylim(bottom=0)
plt.tight_layout()
fig.savefig(OUTDIR / "fig_unphysical_rate.pdf", bbox_inches="tight")
plt.close(fig)

# --- Figure 4: Circuit Comparison Grouped Bar Chart ---
fig, ax = plt.subplots()
circuit_types = ["GHZ", "Random", "QFT"]
x = np.arange(len(circuit_types))
width = 0.2

for i, m in enumerate(methods):
    key = f"mae_{m}"
    vals = [metrics["per_circuit"][ct][key] for ct in circuit_types]
    ax.bar(x + i * width, vals, width, color=COLORS[m], edgecolor="black",
           linewidth=0.5, label=LABELS[m])

ax.set_xlabel("Circuit Type")
ax.set_ylabel("Mean Absolute Error")
ax.set_xticks(x + 1.5 * width)
ax.set_xticklabels(circuit_types)
ax.legend(fontsize=7, framealpha=0.9)
ax.set_ylim(bottom=0)
plt.tight_layout()
fig.savefig(OUTDIR / "fig_circuit_comparison.pdf", bbox_inches="tight")
plt.close(fig)

print("All 4 figures saved to", OUTDIR)
