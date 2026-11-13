# HOG-SVM USPS Reproduction

This repository contains a reproducible reproduction and empirical study of
classical HOG features with linear and RBF support-vector machines on the USPS
handwritten-digit dataset.

The implementation is deliberately dependency-light: features are extracted
with an explicit NumPy HOG implementation, and classification uses
scikit-learn. No GPU or deep-learning framework is required.

## Results

| Model | Feature dimension | Cross-validation | Test accuracy | Macro-F1 | Balanced accuracy |
|---|---:|---:|---:|---:|---:|
| Raw pixels + Linear SVM (baseline) | 256 | 94.91% | 91.68% | 91.08% | 90.97% |
| Raw pixels + RBF-SVM | 256 | 98.00% | 95.17% | 94.76% | 94.64% |
| HOG + Linear SVM | 324 | 97.67% | 95.22% | 94.89% | 94.79% |
| **HOG + RBF-SVM (proposed)** | **324** | **98.38%** | **96.26%** | **95.93%** | **95.91%** |

The proposed model makes 75 errors versus 167 for the raw-pixel linear
baseline. An exact McNemar test over paired test predictions gives
`p = 1.9626845888813069e-16`.

## Reproduce

Python 3.12 is recommended.

```powershell
python -m pip install -r requirements.txt
powershell -ExecutionPolicy Bypass -File .\src\run_all.ps1
```

On the original run, the system Python was available at `D:\python.exe`;
replace `python` with the interpreter available on your machine if needed.
Runtime is short on a normal CPU.

The full experiment is deterministic under the supplied data, random seed 42
and scikit-learn version. Exact timing depends on hardware and should only be
compared relatively.

## Released checkpoints

| File | Role | Best parameters | Test accuracy |
|---|---|---|---:|
| `checkpoints/baseline_raw_linear.joblib` | Baseline | C=0.1 | 91.68% |
| `checkpoints/raw_rbf.joblib` | Classifier control | C=10, gamma=scale | 95.17% |
| `checkpoints/hog_linear.joblib` | Representation control | C=1 | 95.22% |
| `checkpoints/proposed_hog_rbf.joblib` | Proposed model | C=10, gamma=scale | 96.26% |

`checkpoints/manifest.json` contains file sizes, full SHA-256 values and final
parameters. Re-evaluate all four checkpoints with:

```powershell
python .\src\evaluate_checkpoints.py
```

The command writes `results/reproducibility_check.json` and fails if a
checkpoint hash or recorded metric does not match.

## Project layout

```text
src/hog_features.py          HOG descriptor and USPS parser
src/perturbations.py         Controlled robustness perturbations
src/run_experiment.py        Tuning, training, evaluation and checkpoint export
src/make_figures.py          All paper figures
src/evaluate_checkpoints.py  Checkpoint and metric verification
src/build_paper.py           DOCX builder
src/build_pdf.py             Portable PDF rendering from the manuscript
src/audit_docx.py            DOCX structure and table-geometry audit
src/patch_docx_accessibility.py  Figure alt-text and table-width finalisation
paper/manuscript.md          Bilingual manuscript source
paper/*.docx / paper/*.pdf   Final paper artifacts
results/metrics.json         Full recorded metrics
results/predictions.npz      Per-sample predictions
results/reproducibility_check.json  Checkpoint re-evaluation report
results/docx_audit.json      Final DOCX structural audit
checkpoints/*.joblib         Trained model weights
figures/*.png                Publication figures
```

## Data and attribution

USPS data are downloaded from the public
[LIBSVM dataset repository](https://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/multiclass/usps.bz2)
and are not redistributed in this repository. The method follows:

> N. Dalal and B. Triggs, "Histograms of Oriented Gradients for Human
> Detection," CVPR, 2005.

## GitHub repository

The code, four model checkpoints, per-sample predictions, bilingual paper and
figures are published at:

https://github.com/gty-aA/hog-svm-usps-reproduction

The repository can be cloned with:

```powershell
git clone https://github.com/gty-aA/hog-svm-usps-reproduction.git
```

## License

Code is released under the MIT License. Third-party data retain their original
terms.
