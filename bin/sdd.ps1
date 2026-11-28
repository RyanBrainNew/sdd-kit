$ErrorActionPreference = "Stop"
$kitRoot = Split-Path -Parent $PSScriptRoot
if ($env:PYTHONPATH) {
    $env:PYTHONPATH = "$kitRoot;$env:PYTHONPATH"
} else {
    $env:PYTHONPATH = $kitRoot
}
$python = Get-Command python -ErrorAction SilentlyContinue
if ($python) {
    & $python.Source -m sdd @args
} else {
    & py -3 -m sdd @args
}
exit $LASTEXITCODE
