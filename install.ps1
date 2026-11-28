[CmdletBinding()]
param(
    [string]$Repo = "RyanBrainNew/sdd-kit",
    [string]$Ref = "latest",
    [string]$InstallDir = (Join-Path $env:LOCALAPPDATA "sdd-kit"),
    [string]$SourcePath,
    [switch]$NoPath,
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

function Write-Step {
    param([string]$Message)
    Write-Host "[sdd] $Message"
}

function Stop-Install {
    param([string]$Message)
    throw "[sdd] $Message"
}

function Get-PythonCommand {
    $python = Get-Command python -ErrorAction SilentlyContinue
    if ($python) {
        return @{ Exe = $python.Source; Prefix = @() }
    }
    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        return @{ Exe = $py.Source; Prefix = @("-3") }
    }
    Stop-Install "Python 3.11+ is required, but neither python nor py was found."
}

function Invoke-Python {
    param(
        [hashtable]$Python,
        [string[]]$Arguments
    )
    $all = @()
    $all += $Python.Prefix
    $all += $Arguments
    return (& $Python.Exe @all)
}

$python = Get-PythonCommand
$version = (
    Invoke-Python $python @(
        "-c",
        "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')"
    )
).Trim()
if ([version]$version -lt [version]"3.11") {
    Stop-Install "Python 3.11+ is required; found $version."
}
Write-Step "Python $version"

$temp = Join-Path ([IO.Path]::GetTempPath()) (
    "sdd-kit-install-" + [guid]::NewGuid().ToString("N")
)
New-Item -ItemType Directory -Path $temp -Force | Out-Null

try {
    $sourceRoot = ""
    if ($SourcePath) {
        $candidate = (Resolve-Path -LiteralPath $SourcePath).Path
        if (-not (Test-Path (Join-Path $candidate "sdd/scripts/sdd.py"))) {
            Stop-Install "SourcePath is not an sdd-kit checkout: $candidate"
        }
        $sourceRoot = $candidate
        Write-Step "Using local source $sourceRoot"
    } else {
        $zip = Join-Path $temp "sdd-kit.zip"
        $urls = @()
        if ($Ref -eq "latest") {
            $urls += "https://github.com/$Repo/releases/latest/download/sdd-kit.zip"
            $urls += "https://github.com/$Repo/archive/refs/heads/main.zip"
        } elseif ($Ref -match '^v?[0-9]') {
            $urls += "https://github.com/$Repo/archive/refs/tags/$Ref.zip"
        } else {
            $urls += "https://github.com/$Repo/archive/refs/heads/$Ref.zip"
        }

        $downloaded = $false
        foreach ($url in $urls) {
            try {
                Write-Step "Downloading $url"
                Invoke-WebRequest -Uri $url -OutFile $zip -UseBasicParsing
                $downloaded = $true
                break
            } catch {
                Write-Step "Download failed: $($_.Exception.Message)"
            }
        }
        if (-not $downloaded) {
            Stop-Install "Could not download sdd-kit from $Repo ($Ref)."
        }

        $extract = Join-Path $temp "extract"
        Expand-Archive -LiteralPath $zip -DestinationPath $extract -Force
        $sourceRoot = Get-ChildItem -LiteralPath $extract -Directory -Force |
            Select-Object -First 1 -ExpandProperty FullName
        if (
            -not $sourceRoot -or
            -not (Test-Path (Join-Path $sourceRoot "sdd/scripts/sdd.py"))
        ) {
            Stop-Install "Downloaded archive does not look like sdd-kit."
        }
    }

    $installFull = [IO.Path]::GetFullPath($InstallDir)
    $sourceFull = [IO.Path]::GetFullPath($sourceRoot)
    $separator = [IO.Path]::DirectorySeparatorChar
    $installTrimmed = $installFull.TrimEnd("\", "/")
    $sourceTrimmed = $sourceFull.TrimEnd("\", "/")
    $driveRoot = [IO.Path]::GetPathRoot($installFull).TrimEnd("\", "/")
    if ($installTrimmed -eq $driveRoot) {
        Stop-Install "Refusing to install to a drive root: $installFull"
    }
    foreach ($protected in @($env:LOCALAPPDATA, $env:APPDATA, $env:USERPROFILE)) {
        if (
            $protected -and
            $installTrimmed -eq [IO.Path]::GetFullPath($protected).TrimEnd("\", "/")
        ) {
            Stop-Install "Refusing to install over a system profile directory: $installFull"
        }
    }
    if (
        $installTrimmed -eq $sourceTrimmed -or
        $installTrimmed.StartsWith("$sourceTrimmed$separator") -or
        $sourceTrimmed.StartsWith("$installTrimmed$separator")
    ) {
        Stop-Install "InstallDir and SourcePath must not contain each other."
    }

    if (Test-Path -LiteralPath $installFull) {
        $isKit = Test-Path (Join-Path $installFull "sdd/scripts/sdd.py")
        $entries = @(Get-ChildItem -LiteralPath $installFull -Force)
        if (-not $isKit -and $entries.Count -gt 0 -and -not $Force) {
            Stop-Install (
                "$installFull is not empty and is not an sdd-kit install; " +
                "use -Force to replace it."
            )
        }
        Remove-Item -LiteralPath $installFull -Recurse -Force
    }
    New-Item -ItemType Directory -Path $installFull -Force | Out-Null

    $skip = @(
        ".git",
        ".sdd",
        "build",
        "dist",
        "sdd_kit.egg-info"
    )
    Get-ChildItem -LiteralPath $sourceFull -Force |
        Where-Object { $skip -notcontains $_.Name } |
        Copy-Item -Destination $installFull -Recurse -Force

    $binDir = Join-Path $installFull "bin"
    $cmdShim = Join-Path $binDir "sdd.cmd"
    if (-not (Test-Path -LiteralPath $cmdShim)) {
        $shim = @'
@echo off
setlocal
set "SDD_KIT_ROOT=%~dp0.."
if defined PYTHONPATH (
  set "PYTHONPATH=%SDD_KIT_ROOT%;%PYTHONPATH%"
) else (
  set "PYTHONPATH=%SDD_KIT_ROOT%"
)
where python >nul 2>nul
if errorlevel 1 goto usepy
python -m sdd %*
exit /b %ERRORLEVEL%
:usepy
py -3 -m sdd %*
exit /b %ERRORLEVEL%
'@
        New-Item -ItemType Directory -Path $binDir -Force | Out-Null
        Set-Content -LiteralPath $cmdShim -Value $shim -Encoding ascii
    }

    if (-not $NoPath) {
        $userPath = [Environment]::GetEnvironmentVariable("Path", "User")
        $parts = @()
        if ($userPath) {
            $parts = $userPath -split ";" | Where-Object { $_ }
        }
        if ($parts -notcontains $binDir) {
            $newPath = if ($userPath) { "$userPath;$binDir" } else { $binDir }
            [Environment]::SetEnvironmentVariable("Path", $newPath, "User")
            Write-Step "Added $binDir to the user PATH"
        } else {
            Write-Step "PATH already contains $binDir"
        }
        $env:Path = "$binDir;$env:Path"
    }

    $oldPythonPath = $env:PYTHONPATH
    $env:PYTHONPATH = if ($oldPythonPath) {
        "$installFull;$oldPythonPath"
    } else {
        $installFull
    }
    try {
        $installed = (Invoke-Python $python @("-m", "sdd", "--version")).Trim()
    } finally {
        if ($null -eq $oldPythonPath) {
            Remove-Item Env:PYTHONPATH -ErrorAction SilentlyContinue
        } else {
            $env:PYTHONPATH = $oldPythonPath
        }
    }

    Write-Step "Installed sdd $installed to $installFull"
    Write-Host ""
    Write-Host "Next:"
    Write-Host "  cd <repo>"
    Write-Host "  sdd init"
    if (-not $NoPath) {
        Write-Host "Open a new terminal if 'sdd' is not found in this session."
    }
} finally {
    if (Test-Path -LiteralPath $temp) {
        Remove-Item -LiteralPath $temp -Recurse -Force
    }
}
