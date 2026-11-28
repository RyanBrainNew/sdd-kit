$ErrorActionPreference = "Stop"
$kitRoot = Split-Path -Parent $PSScriptRoot
if ($env:PYTHONPATH) {
    $env:PYTHONPATH = "$kitRoot;$env:PYTHONPATH"
} else {
    $env:PYTHONPATH = $kitRoot
}
python -m sdd @args
exit $LASTEXITCODE
