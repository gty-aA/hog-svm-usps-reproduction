$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
$python = if (Test-Path "D:\python.exe") { "D:\python.exe" } else { "python" }

if (-not (Test-Path "data\usps.bz2")) {
    Invoke-WebRequest "https://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/multiclass/usps.bz2" -OutFile "data\usps.bz2"
}
if (-not (Test-Path "data\usps.t.bz2")) {
    Invoke-WebRequest "https://www.csie.ntu.edu.tw/~cjlin/libsvmtools/datasets/multiclass/usps.t.bz2" -OutFile "data\usps.t.bz2"
}

& $python "src\run_experiment.py"
& $python "src\make_figures.py"
Write-Host "Experiment and figures complete. Metrics: results\metrics.json"
