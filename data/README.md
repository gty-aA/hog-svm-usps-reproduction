# USPS data

The experiment downloads the official USPS train/test files from the LIBSVM
dataset repository:

- https://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/multiclass/usps.bz2
- https://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/multiclass/usps.t.bz2

Expected samples: 7,291 training and 2,007 test images, each represented by
256 features in LIBSVM format. The data files are intentionally excluded from
Git because they are third-party artifacts. `src/run_all.ps1` downloads them
when missing.

Expected SHA-256:

```text
3771e9dd6ba685185f89867b6e249233dd74652389f263963b3b741e994b034f  usps.bz2
a9c0164e797d60142a50604917f0baa604f326e9a689698763793fa5d12ffc4e  usps.t.bz2
```
