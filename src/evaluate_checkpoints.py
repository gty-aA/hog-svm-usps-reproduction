"""Re-evaluate every released checkpoint against the untouched USPS test split."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import joblib
import numpy as np
from sklearn.metrics import accuracy_score, f1_score

from hog_features import extract_hog, load_usps


ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    with (ROOT / "results" / "metrics.json").open(encoding="utf-8") as handle:
        metrics = json.load(handle)
    X_test, y_test = load_usps(str(ROOT / "data" / "usps.t.bz2"))
    raw = X_test.reshape(len(X_test), -1)
    hog = extract_hog(X_test)

    report = {}
    all_ok = True
    for key, expected in metrics["models"].items():
        path = ROOT / expected["checkpoint"]
        payload = joblib.load(path)
        features = raw if payload["representation"] == "raw" else hog
        prediction = payload["model"].predict(features)
        accuracy = float(accuracy_score(y_test, prediction))
        macro_f1 = float(f1_score(y_test, prediction, average="macro"))
        expected_accuracy = float(expected["metrics"]["accuracy"])
        expected_f1 = float(expected["metrics"]["macro_f1"])
        hash_matches = sha256(path) == expected["checkpoint_sha256"]
        metrics_match = np.isclose(accuracy, expected_accuracy, atol=1e-12) and np.isclose(
            macro_f1, expected_f1, atol=1e-12
        )
        ok = bool(hash_matches and metrics_match)
        all_ok = all_ok and ok
        report[key] = {
            "test_accuracy": accuracy,
            "test_macro_f1": macro_f1,
            "expected_accuracy": expected_accuracy,
            "expected_macro_f1": expected_f1,
            "sha256_matches": hash_matches,
            "metrics_match": bool(metrics_match),
            "pass": ok,
        }
        print(
            f"{key}: accuracy={accuracy:.6f}, macro_f1={macro_f1:.6f}, "
            f"hash={'OK' if hash_matches else 'FAIL'}, "
            f"metrics={'OK' if metrics_match else 'FAIL'}"
        )

    output = {"all_checks_passed": all_ok, "models": report}
    output_path = ROOT / "results" / "reproducibility_check.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(output, handle, indent=2)
    print(f"Wrote {output_path}")
    if not all_ok:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
