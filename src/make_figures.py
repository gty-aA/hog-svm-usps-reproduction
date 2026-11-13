"""Generate publication-ready figures from the recorded experiment metrics."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from hog_features import load_usps, visualise_hog


ROOT = Path(__file__).resolve().parents[1]
RESULT_DIR = ROOT / "results"
FIGURE_DIR = ROOT / "figures"

MODEL_ORDER = [
    "baseline_raw_linear",
    "raw_rbf",
    "hog_linear",
    "proposed_hog_rbf",
]
MODEL_LABELS = {
    "baseline_raw_linear": "Raw + Linear",
    "raw_rbf": "Raw + RBF",
    "hog_linear": "HOG + Linear",
    "proposed_hog_rbf": "HOG + RBF (ours)",
}
COLORS = {
    "baseline_raw_linear": "#8C8C8C",
    "raw_rbf": "#73A2C6",
    "hog_linear": "#E2A656",
    "proposed_hog_rbf": "#1F6F8B",
}


def configure_style() -> None:
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9.5,
            "axes.titlesize": 11,
            "axes.labelsize": 9.5,
            "axes.spines.top": False,
            "axes.spines.right": False,
            "figure.facecolor": "white",
            "axes.facecolor": "white",
            "savefig.facecolor": "white",
            "legend.frameon": False,
        }
    )


def save(fig: plt.Figure, name: str) -> None:
    path = FIGURE_DIR / name
    fig.savefig(path, dpi=260, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved {path}")


def draw_framework() -> None:
    fig, ax = plt.subplots(figsize=(10.6, 2.9))
    ax.set_xlim(0, 11)
    ax.set_ylim(0, 3)
    ax.axis("off")
    boxes = [
        (0.15, 0.90, 1.35, 1.20, "16 x 16\ninput image", "#EEF3F6"),
        (1.85, 0.90, 1.55, 1.20, "Gradient\nmagnitude + angle", "#D9E8EF"),
        (3.75, 0.90, 1.45, 1.20, "4 x 4 cells\n9 orientation bins", "#C7DDE8"),
        (5.55, 0.90, 1.65, 1.20, "2 x 2 blocks\nL2-Hys normalisation", "#AFD0DD"),
        (7.55, 0.90, 1.35, 1.20, "324-D\nHOG feature", "#98C2D2"),
        (9.20, 0.90, 1.55, 1.20, "RBF-SVM\nclassifier", "#1F6F8B"),
    ]
    for x, y, w, h, text, fill in boxes:
        color = "white" if fill == "#1F6F8B" else "#17394A"
        ax.add_patch(
            FancyBboxPatch(
                (x, y),
                w,
                h,
                boxstyle="round,pad=0.03,rounding_size=0.12",
                linewidth=1.0,
                edgecolor="#7DA5B5",
                facecolor=fill,
            )
        )
        ax.text(
            x + w / 2,
            y + h / 2,
            text,
            ha="center",
            va="center",
            color=color,
            fontsize=10,
            fontweight="semibold" if fill == "#1F6F8B" else "normal",
        )
    for left, right in zip(boxes[:-1], boxes[1:]):
        start = (left[0] + left[2] + 0.05, left[1] + left[3] / 2)
        end = (right[0] - 0.06, right[1] + right[3] / 2)
        ax.add_patch(
            FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=11,
                color="#4C6C7A",
                linewidth=1.2,
            )
        )
    ax.text(
        5.45,
        0.35,
        "Representation learning by hand-crafted local gradients",
        ha="center",
        va="center",
        color="#4A4A4A",
        fontsize=10,
        style="italic",
    )
    save(fig, "fig01_framework.png")


def draw_samples_and_hog(X_test: np.ndarray, y_test: np.ndarray) -> None:
    fig = plt.figure(figsize=(10.5, 4.8))
    grid = fig.add_gridspec(2, 10, height_ratios=[1.0, 1.38], hspace=0.36, wspace=0.12)
    for cls in range(10):
        index = int(np.flatnonzero(y_test == cls)[0])
        ax = fig.add_subplot(grid[0, cls])
        ax.imshow(X_test[index], cmap="gray_r", vmin=0, vmax=1)
        ax.set_title(f"Digit {cls}", fontsize=8.5, pad=3)
        ax.set_xticks([])
        ax.set_yticks([])
    bottom_axes = [
        fig.add_subplot(grid[1, 0:2]),
        fig.add_subplot(grid[1, 2:4]),
        fig.add_subplot(grid[1, 4:6]),
        fig.add_subplot(grid[1, 6:8]),
        fig.add_subplot(grid[1, 8:10]),
    ]
    for col, ax in enumerate(bottom_axes[:-1]):
        index = int(np.flatnonzero(y_test == 2)[0])
        if col == 0:
            ax.imshow(X_test[index], cmap="gray_r", vmin=0, vmax=1)
            ax.set_title("Raw intensity", fontsize=9.5)
        elif col == 1:
            magnitude, _ = visualise_hog(X_test[index])
            ax.imshow(magnitude, cmap="magma")
            ax.set_title("Gradient magnitude", fontsize=9.5)
        elif col == 2:
            ax.imshow(X_test[index], cmap="gray_r", vmin=0, vmax=1)
            magnitude, orientation = visualise_hog(X_test[index])
            for cy in range(4):
                for cx in range(4):
                    y0, y1 = cy * 4, (cy + 1) * 4
                    x0, x1 = cx * 4, (cx + 1) * 4
                    mag = float(magnitude[y0:y1, x0:x1].mean())
                    angle = float(orientation[y0:y1, x0:x1].mean())
                    dx, dy = np.cos(angle) * 1.25, -np.sin(angle) * 1.25
                    ax.arrow(
                        cx * 4 + 1.5,
                        cy * 4 + 1.5,
                        dx,
                        dy,
                        color="#D94801",
                        width=0.08,
                        head_width=0.38,
                        length_includes_head=True,
                        alpha=min(0.95, 0.35 + mag * 8),
                    )
            ax.set_title("Dominant cell directions", fontsize=9.5)
        elif col == 3:
            from hog_features import extract_hog

            desc = extract_hog(X_test[index : index + 1])[0].reshape(-1, 9)
            ax.imshow(desc.T, aspect="auto", cmap="Blues")
            ax.set_xlabel("Block index", labelpad=1)
            ax.set_ylabel("Bin", labelpad=1)
            ax.set_title("Normalised HOG descriptor", fontsize=9.5)
        else:
            ax.axis("off")
            ax.text(
                0.02,
                0.84,
                "Design rationale",
                fontsize=10,
                fontweight="bold",
                color="#17394A",
                transform=ax.transAxes,
            )
            ax.text(
                0.02,
                0.67,
                "Local orientation statistics encode stroke shape.\n"
                "Overlapping block normalisation suppresses\n"
                "global contrast and local illumination effects.\n"
                "The resulting 324-D vector is compact, explicit,\n"
                "and inexpensive for an RBF-SVM.",
                fontsize=8.7,
                color="#394A52",
                va="top",
                transform=ax.transAxes,
                linespacing=1.45,
            )
        ax.set_xticks([])
        ax.set_yticks([])
    last = bottom_axes[-1]
    last.axis("off")
    last.text(
        0.02,
        0.84,
        "Design rationale",
        fontsize=10,
        fontweight="bold",
        color="#17394A",
        transform=last.transAxes,
    )
    last.text(
        0.02,
        0.67,
        "Local orientation statistics encode stroke shape.\n"
        "Overlapping block normalisation suppresses\n"
        "global contrast and local illumination effects.\n"
        "The resulting 324-D vector is compact, explicit,\n"
        "and inexpensive for an RBF-SVM.",
        fontsize=8.7,
        color="#394A52",
        va="top",
        transform=last.transAxes,
        linespacing=1.45,
    )
    fig.suptitle(
        "USPS digit samples and the hand-crafted HOG representation",
        fontsize=12,
        fontweight="bold",
        y=1.01,
    )
    save(fig, "fig02_samples_hog.png")


def draw_main_results(metrics: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9.2, 3.7), gridspec_kw={"wspace": 0.30})
    values = [metrics["models"][key]["metrics"]["accuracy"] * 100 for key in MODEL_ORDER]
    f1s = [metrics["models"][key]["metrics"]["macro_f1"] * 100 for key in MODEL_ORDER]
    x = np.arange(len(MODEL_ORDER))
    width = 0.37
    axes[0].bar(x - width / 2, values, width, color="#4C86A8", label="Accuracy")
    axes[0].bar(x + width / 2, f1s, width, color="#E2A656", label="Macro-F1")
    for i, (value, f1) in enumerate(zip(values, f1s)):
        axes[0].text(i - width / 2, value + 0.7, f"{value:.2f}", ha="center", fontsize=7.8)
        axes[0].text(i + width / 2, f1 + 0.7, f"{f1:.2f}", ha="center", fontsize=7.8)
    axes[0].set_xticks(x, ["Raw\nLinear", "Raw\nRBF", "HOG\nLinear", "HOG\nRBF"], fontsize=8.2)
    axes[0].set_ylim(88, 99)
    axes[0].set_ylabel("Test score (%)")
    axes[0].set_title("(a) Clean test performance", loc="left")
    axes[0].legend(loc="lower right", ncol=2)
    axes[0].grid(axis="y", color="#E6EAED", linewidth=0.8)
    axes[0].set_axisbelow(True)

    sizes = [
        metrics["models"][key]["checkpoint_bytes"] / 1024 for key in MODEL_ORDER
    ]
    bars = axes[1].barh(
        np.arange(len(MODEL_ORDER)),
        sizes,
        color=[COLORS[key] for key in MODEL_ORDER],
        height=0.55,
    )
    for bar, size in zip(bars, sizes):
        axes[1].text(size + 35, bar.get_y() + bar.get_height() / 2, f"{size:.0f} KB", va="center", fontsize=8)
    axes[1].set_yticks(
        np.arange(len(MODEL_ORDER)),
        ["Raw + Linear", "Raw + RBF", "HOG + Linear", "HOG + RBF"],
        fontsize=8.4,
    )
    axes[1].set_xlabel("Serialised model size (KB)")
    axes[1].set_title("(b) Deployment footprint", loc="left")
    axes[1].invert_yaxis()
    axes[1].grid(axis="x", color="#E6EAED", linewidth=0.8)
    axes[1].set_axisbelow(True)
    save(fig, "fig03_main_results.png")


def draw_robustness(metrics: dict) -> None:
    robust = metrics["robustness"]
    fig, axes = plt.subplots(2, 2, figsize=(9.4, 6.8), gridspec_kw={"wspace": 0.28, "hspace": 0.48})
    labels = [MODEL_LABELS[key] for key in MODEL_ORDER]
    scenario_groups = [
        (
            "(a) Global contrast",
            ["contrast_0.60", "clean", "contrast_1.40"],
            ["0.6x", "1.0x", "1.4x"],
            "Contrast scale",
        ),
        (
            "(b) Additive Gaussian noise",
            ["clean", "noise_sigma_0.10", "noise_sigma_0.20", "noise_sigma_0.30"],
            ["0.00", "0.10", "0.20", "0.30"],
            "Noise standard deviation",
        ),
    ]
    for ax, (title, scenarios, xlabels, xlabel) in zip(axes[0], scenario_groups):
        for key in MODEL_ORDER:
            scores = [robust[s][key]["accuracy"] * 100 for s in scenarios]
            ax.plot(
                np.arange(len(scenarios)),
                scores,
                marker="o" if key == "proposed_hog_rbf" else "o",
                markersize=4.6 if key == "proposed_hog_rbf" else 3.7,
                linewidth=2.2 if key == "proposed_hog_rbf" else 1.2,
                color=COLORS[key],
                label=MODEL_LABELS[key],
            )
        ax.set_xticks(np.arange(len(scenarios)), xlabels)
        ax.set_ylim(15, 100)
        ax.set_ylabel("Accuracy (%)")
        ax.set_xlabel(xlabel)
        ax.set_title(title, loc="left")
        ax.grid(color="#E6EAED", linewidth=0.8)
        ax.set_axisbelow(True)
    axes[0, 0].legend(loc="lower left", fontsize=7.6)

    shift_scenarios = ["clean", "shift_right_1px", "shift_down_1px"]
    shift_labels = ["Clean", "Right 1 px", "Down 1 px"]
    x = np.arange(len(shift_scenarios))
    bar_width = 0.19
    for i, key in enumerate(MODEL_ORDER):
        scores = [robust[s][key]["accuracy"] * 100 for s in shift_scenarios]
        axes[1, 0].bar(
            x + (i - 1.5) * bar_width,
            scores,
            bar_width,
            color=COLORS[key],
            label=MODEL_LABELS[key],
        )
    axes[1, 0].set_xticks(x, shift_labels)
    axes[1, 0].set_ylim(60, 100)
    axes[1, 0].set_ylabel("Accuracy (%)")
    axes[1, 0].set_title("(c) One-pixel translation", loc="left")
    axes[1, 0].grid(axis="y", color="#E6EAED", linewidth=0.8)
    axes[1, 0].set_axisbelow(True)

    rotation_scenarios = ["clean", "rotate_plus_5deg", "rotate_minus_5deg"]
    rotation_labels = ["Clean", "+5 deg", "-5 deg"]
    for i, key in enumerate(MODEL_ORDER):
        scores = [robust[s][key]["accuracy"] * 100 for s in rotation_scenarios]
        axes[1, 1].bar(
            x + (i - 1.5) * bar_width,
            scores,
            bar_width,
            color=COLORS[key],
            label=MODEL_LABELS[key],
        )
    axes[1, 1].set_xticks(x, rotation_labels)
    axes[1, 1].set_ylim(60, 100)
    axes[1, 1].set_ylabel("Accuracy (%)")
    axes[1, 1].set_title("(d) Small rotation", loc="left")
    axes[1, 1].grid(axis="y", color="#E6EAED", linewidth=0.8)
    axes[1, 1].set_axisbelow(True)
    save(fig, "fig04_robustness.png")


def draw_confusion(metrics: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9.8, 4.15), gridspec_kw={"wspace": 0.16})
    for ax, key, title in zip(
        axes,
        ["baseline_raw_linear", "proposed_hog_rbf"],
        ["(a) Raw pixels + Linear SVM", "(b) HOG + RBF-SVM"],
    ):
        cm = np.asarray(metrics["models"][key]["confusion_matrix"])
        row_norm = cm / cm.sum(axis=1, keepdims=True)
        image = ax.imshow(row_norm, cmap="Blues", vmin=0, vmax=1)
        for row in range(10):
            for col in range(10):
                value = cm[row, col]
                if row == col or value >= 4:
                    ax.text(
                        col,
                        row,
                        str(value),
                        ha="center",
                        va="center",
                        fontsize=6.8,
                        color="white" if row_norm[row, col] > 0.55 else "#22313A",
                    )
        ax.set_xticks(range(10))
        ax.set_yticks(range(10))
        ax.set_xlabel("Predicted digit")
        ax.set_ylabel("True digit")
        ax.set_title(title, loc="left")
    cbar = fig.colorbar(image, ax=axes, fraction=0.025, pad=0.025)
    cbar.set_label("Row-normalised fraction")
    save(fig, "fig05_confusion.png")


def draw_learning_curves(metrics: dict) -> None:
    fig, ax = plt.subplots(figsize=(6.5, 3.7))
    labels = {
        "baseline_raw_linear": "Raw + Linear",
        "proposed_hog_rbf": "HOG + RBF",
    }
    for key in ["baseline_raw_linear", "proposed_hog_rbf"]:
        points = metrics["learning_curves"][key]
        sizes = [point["train_size"] for point in points]
        validation = [point["validation_accuracy"] * 100 for point in points]
        ax.plot(
            sizes,
            validation,
            marker="o",
            linewidth=2.0,
            color=COLORS[key],
            label=labels[key],
        )
    ax.set_xlabel("Number of training samples")
    ax.set_ylabel("Validation accuracy (%)")
    ax.set_ylim(86, 100)
    ax.set_title("Validation learning curves", loc="left")
    ax.grid(color="#E6EAED", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(loc="lower right")
    save(fig, "fig06_learning_curve.png")


def draw_per_class(metrics: dict) -> None:
    fig, ax = plt.subplots(figsize=(8.4, 3.6))
    x = np.arange(10)
    width = 0.36
    for offset, key, label in [
        (-width / 2, "baseline_raw_linear", "Raw + Linear"),
        (width / 2, "proposed_hog_rbf", "HOG + RBF"),
    ]:
        f1s = [
            metrics["models"][key]["per_class"][str(cls)]["f1-score"] * 100
            for cls in range(10)
        ]
        ax.bar(x + offset, f1s, width, label=label, color=COLORS[key])
    ax.set_xticks(x, [str(cls) for cls in range(10)])
    ax.set_xlabel("Digit class")
    ax.set_ylabel("Per-class F1 (%)")
    ax.set_ylim(82, 100)
    ax.set_title("Class-wise F1 comparison", loc="left")
    ax.grid(axis="y", color="#E6EAED", linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(loc="lower right", ncol=2)
    save(fig, "fig07_per_class_f1.png")


def main() -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    configure_style()
    with (RESULT_DIR / "metrics.json").open(encoding="utf-8") as handle:
        metrics = json.load(handle)
    X_test, y_test = load_usps(str(ROOT / "data" / "usps.t.bz2"))
    draw_framework()
    draw_samples_and_hog(X_test, y_test)
    draw_main_results(metrics)
    draw_robustness(metrics)
    draw_confusion(metrics)
    draw_learning_curves(metrics)
    draw_per_class(metrics)


if __name__ == "__main__":
    main()
