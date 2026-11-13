"""Reproduce a classical HOG + SVM handwritten-digit recognition study on USPS.

The script tunes four models on the training split, evaluates the untouched test
split, exports model weights, per-sample predictions and robustness results.
"""

from __future__ import annotations

import hashlib
import json
import logging
import platform
import time
from pathlib import Path

import joblib
import numpy as np
import scipy
import sklearn
from scipy.stats import binomtest
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import GridSearchCV, StratifiedKFold, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC, LinearSVC

from hog_features import extract_hog, hog_descriptor, load_usps
from perturbations import add_gaussian_noise, change_contrast, rotate_images, translate


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RESULT_DIR = ROOT / "results"
CHECKPOINT_DIR = ROOT / "checkpoints"


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        handlers=[
            logging.FileHandler(RESULT_DIR / "experiment.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def model_specs() -> dict[str, dict]:
    return {
        "baseline_raw_linear": {
            "display_name": "Raw pixels + Linear SVM",
            "representation": "raw",
            "estimator": Pipeline(
                [
                    ("scale", StandardScaler()),
                    ("clf", LinearSVC(dual="auto", max_iter=20000, random_state=42)),
                ]
            ),
            "grid": {"clf__C": [0.001, 0.01, 0.1, 1.0]},
        },
        "raw_rbf": {
            "display_name": "Raw pixels + RBF-SVM",
            "representation": "raw",
            "estimator": Pipeline(
                [
                    ("scale", StandardScaler()),
                    ("clf", SVC(kernel="rbf", cache_size=1024)),
                ]
            ),
            "grid": {
                "clf__C": [1.0, 10.0, 100.0],
                "clf__gamma": ["scale", 0.001, 0.01],
            },
        },
        "hog_linear": {
            "display_name": "HOG + Linear SVM",
            "representation": "hog",
            "estimator": LinearSVC(dual="auto", max_iter=20000, random_state=42),
            "grid": {"C": [0.0001, 0.001, 0.01, 0.1, 1.0]},
        },
        "proposed_hog_rbf": {
            "display_name": "HOG + RBF-SVM (proposed)",
            "representation": "hog",
            "estimator": SVC(kernel="rbf", cache_size=1024),
            "grid": {
                "C": [1.0, 10.0, 100.0],
                "gamma": ["scale", 0.01, 0.1],
            },
        },
    }


def predict(spec: dict, model, images: np.ndarray, hog_cache: dict) -> np.ndarray:
    if spec["representation"] == "raw":
        features = images.reshape(len(images), -1)
    else:
        key = id(images)
        if key not in hog_cache:
            hog_cache[key] = extract_hog(images)
        features = hog_cache[key]
    return model.predict(features)


def measure_end_to_end_latency(
    spec: dict, model, images: np.ndarray, repeats: int = 2
) -> float:
    """Measure feature extraction and single-image prediction in milliseconds."""
    for image in images[:20]:
        features = (
            image.reshape(1, -1)
            if spec["representation"] == "raw"
            else hog_descriptor(image).reshape(1, -1)
        )
        model.predict(features)

    start = time.perf_counter()
    for _ in range(repeats):
        for image in images:
            features = (
                image.reshape(1, -1)
                if spec["representation"] == "raw"
                else hog_descriptor(image).reshape(1, -1)
            )
            model.predict(features)
    elapsed = time.perf_counter() - start
    return float(elapsed / (len(images) * repeats) * 1000.0)


def evaluate_predictions(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro")),
        "balanced_accuracy": float(balanced_accuracy_score(y_true, y_pred)),
    }


def hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mcnemar_exact(y_true: np.ndarray, pred_a: np.ndarray, pred_b: np.ndarray) -> dict:
    correct_a = pred_a == y_true
    correct_b = pred_b == y_true
    a_only = int(np.sum(correct_a & ~correct_b))
    b_only = int(np.sum(~correct_a & correct_b))
    result = binomtest(a_only, a_only + b_only, p=0.5, alternative="two-sided")
    return {
        "baseline_correct_only": a_only,
        "proposed_correct_only": b_only,
        "p_value": float(result.pvalue),
    }


def main() -> None:
    RESULT_DIR.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    setup_logging()

    logging.info("Loading USPS data")
    X_train_raw, y_train = load_usps(str(DATA_DIR / "usps.bz2"))
    X_test_raw, y_test = load_usps(str(DATA_DIR / "usps.t.bz2"))
    logging.info("Train: %s, Test: %s", X_train_raw.shape, X_test_raw.shape)

    # A stratified, seeded validation split is reserved only for learning curves.
    X_fit, X_valid, y_fit, y_valid = train_test_split(
        X_train_raw,
        y_train,
        test_size=0.2,
        stratify=y_train,
        random_state=42,
    )
    X_fit_hog = extract_hog(X_fit)
    X_valid_hog = extract_hog(X_valid)
    X_test_hog = extract_hog(X_test_raw)
    X_train_hog = extract_hog(X_train_raw)
    logging.info("HOG dimension: %d", X_train_hog.shape[1])

    representations = {
        "raw": {
            "train": X_train_raw.reshape(len(X_train_raw), -1),
            "fit": X_fit.reshape(len(X_fit), -1),
            "valid": X_valid.reshape(len(X_valid), -1),
            "test": X_test_raw.reshape(len(X_test_raw), -1),
        },
        "hog": {
            "train": X_train_hog,
            "fit": X_fit_hog,
            "valid": X_valid_hog,
            "test": X_test_hog,
        },
    }

    cv = StratifiedKFold(n_splits=3, shuffle=True, random_state=42)
    specs = model_specs()
    fitted = {}
    summary = {}
    predictions = {}
    hog_cache = {id(X_test_raw): X_test_hog}

    for key, spec in specs.items():
        logging.info("Tuning %s", spec["display_name"])
        start = time.perf_counter()
        search = GridSearchCV(
            spec["estimator"],
            spec["grid"],
            scoring="accuracy",
            cv=cv,
            n_jobs=-1,
            refit=True,
            return_train_score=True,
            verbose=1,
        )
        search.fit(representations[spec["representation"]]["train"], y_train)
        train_seconds = time.perf_counter() - start

        best_index = int(search.best_index_)
        cv_mean = float(search.cv_results_["mean_test_score"][best_index])
        cv_std = float(search.cv_results_["std_test_score"][best_index])

        inference_start = time.perf_counter()
        y_pred = predict(
            spec, search.best_estimator_, X_test_raw, hog_cache
        )
        inference_seconds = time.perf_counter() - inference_start
        metrics = evaluate_predictions(y_test, y_pred)
        report = classification_report(
            y_test, y_pred, digits=4, output_dict=True, zero_division=0
        )

        checkpoint_path = CHECKPOINT_DIR / f"{key}.joblib"
        joblib.dump(
            {
                "model": search.best_estimator_,
                "model_key": key,
                "display_name": spec["display_name"],
                "representation": spec["representation"],
                "best_params": search.best_params_,
                "feature_dimension": int(
                    representations[spec["representation"]]["train"].shape[1]
                ),
                "training_split": "USPS training split (n=7291)",
                "test_split": "USPS test split (n=2007)",
                "random_seed": 42,
            },
            checkpoint_path,
            compress=3,
        )

        fitted[key] = search.best_estimator_
        predictions[key] = y_pred
        end_to_end_ms = measure_end_to_end_latency(
            spec, search.best_estimator_, X_test_raw
        )
        summary[key] = {
            "display_name": spec["display_name"],
            "representation": spec["representation"],
            "feature_dimension": int(
                representations[spec["representation"]]["train"].shape[1]
            ),
            "best_params": search.best_params_,
            "cv_accuracy_mean": cv_mean,
            "cv_accuracy_std": cv_std,
            "grid_search_and_fit_seconds": float(train_seconds),
            "batched_classifier_inference_seconds": float(inference_seconds),
            "end_to_end_ms_per_image": end_to_end_ms,
            "metrics": metrics,
            "per_class": report,
            "confusion_matrix": confusion_matrix(y_test, y_pred).tolist(),
            "chosen_cv_parameters": search.cv_results_["params"][best_index],
            "checkpoint": str(checkpoint_path.relative_to(ROOT)),
            "checkpoint_bytes": checkpoint_path.stat().st_size,
            "checkpoint_sha256": hash_file(checkpoint_path),
        }
        logging.info(
            "%s: CV %.4f, test %.4f, macro-F1 %.4f",
            spec["display_name"],
            cv_mean,
            metrics["accuracy"],
            metrics["macro_f1"],
        )

    # Test-time perturbations. The same fitted models are used throughout.
    scenarios = {
        "clean": X_test_raw,
        "noise_sigma_0.10": add_gaussian_noise(X_test_raw, 0.10),
        "noise_sigma_0.20": add_gaussian_noise(X_test_raw, 0.20),
        "noise_sigma_0.30": add_gaussian_noise(X_test_raw, 0.30),
        "contrast_0.60": change_contrast(X_test_raw, 0.60),
        "contrast_1.40": change_contrast(X_test_raw, 1.40),
        "shift_right_1px": translate(X_test_raw, 0, 1),
        "shift_down_1px": translate(X_test_raw, 1, 0),
        "rotate_plus_5deg": rotate_images(X_test_raw, 5.0),
        "rotate_minus_5deg": rotate_images(X_test_raw, -5.0),
    }
    robust = {}
    for scenario_name, images in scenarios.items():
        logging.info("Evaluating scenario %s", scenario_name)
        robust[scenario_name] = {}
        for key, spec in specs.items():
            y_pred = predict(spec, fitted[key], images, hog_cache)
            robust[scenario_name][key] = evaluate_predictions(y_test, y_pred)

    # Learning curves on the fixed training/validation split.
    learning_sizes = [500, 1000, 2000, 4000, len(X_fit)]
    learning_curves = {}
    rng = np.random.default_rng(42)
    for key in ["baseline_raw_linear", "proposed_hog_rbf"]:
        spec = specs[key]
        curve = []
        for size in learning_sizes:
            selected = []
            for cls in np.unique(y_fit):
                class_indices = np.flatnonzero(y_fit == cls)
                take = max(1, int(round(size * len(class_indices) / len(y_fit))))
                selected.extend(
                    rng.choice(class_indices, size=min(take, len(class_indices)), replace=False)
                )
            selected = np.asarray(selected)
            estimator = spec["estimator"]
            estimator.set_params(**summary[key]["best_params"])
            rep = representations[spec["representation"]]
            estimator.fit(rep["fit"][selected], y_fit[selected])
            train_acc = accuracy_score(y_fit[selected], estimator.predict(rep["fit"][selected]))
            valid_pred = estimator.predict(rep["valid"])
            curve.append(
                {
                    "train_size": int(len(selected)),
                    "train_accuracy": float(train_acc),
                    "validation_accuracy": float(accuracy_score(y_valid, valid_pred)),
                }
            )
        learning_curves[key] = curve

    comparison = mcnemar_exact(
        y_test,
        predictions["baseline_raw_linear"],
        predictions["proposed_hog_rbf"],
    )

    metadata = {
        "paper_reproduction": (
            "Histograms of Oriented Gradients for Human Detection "
            "(Dalal and Triggs, CVPR 2005), applied to USPS handwritten digits"
        ),
        "dataset": {
            "name": "USPS handwritten digits",
            "source": (
                "https://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/"
                "multiclass/usps.bz2"
            ),
            "train_samples": int(len(y_train)),
            "test_samples": int(len(y_test)),
            "classes": int(len(np.unique(y_train))),
            "image_shape": [16, 16],
            "train_label_counts": {
                str(int(k)): int(v)
                for k, v in zip(*np.unique(y_train, return_counts=True))
            },
            "test_label_counts": {
                str(int(k)): int(v)
                for k, v in zip(*np.unique(y_test, return_counts=True))
            },
            "train_sha256": hash_file(DATA_DIR / "usps.bz2"),
            "test_sha256": hash_file(DATA_DIR / "usps.t.bz2"),
        },
        "protocol": {
            "cross_validation": "3-fold stratified CV on the training split",
            "selection_metric": "mean CV accuracy",
            "holdout": "official 2007-image USPS test split, untouched during tuning",
            "deep_learning_used": False,
            "hog_configuration": {
                "cell_size": 4,
                "bins": 9,
                "block_size": 2,
                "block_stride": 1,
                "normalisation": "L2-Hys (L2 norm, clip 0.2, renormalise)",
            },
        },
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "scikit_learn": sklearn.__version__,
            "platform": platform.platform(),
        },
        "models": summary,
        "robustness": robust,
        "learning_curves": learning_curves,
        "mcnemar_baseline_vs_proposed": comparison,
    }

    with (RESULT_DIR / "metrics.json").open("w", encoding="utf-8") as handle:
        json.dump(metadata, handle, ensure_ascii=False, indent=2)

    np.savez_compressed(
        RESULT_DIR / "predictions.npz",
        y_test=y_test,
        **{f"pred_{key}": value for key, value in predictions.items()},
    )

    # Machine-readable manifest for GitHub Releases / reproducibility checks.
    manifest = []
    for key, info in summary.items():
        manifest.append(
            {
                "model": key,
                "file": info["checkpoint"],
                "sha256": info["checkpoint_sha256"],
                "bytes": info["checkpoint_bytes"],
                "best_params": info["best_params"],
                "test_accuracy": info["metrics"]["accuracy"],
            }
        )
    with (CHECKPOINT_DIR / "manifest.json").open("w", encoding="utf-8") as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)

    logging.info("Saved metrics to %s", RESULT_DIR / "metrics.json")
    logging.info("Saved checkpoints to %s", CHECKPOINT_DIR)


if __name__ == "__main__":
    main()
