
function New-Env {
    param(
        [Parameter()]
        [string]$Suffix,

        [Parameter(Mandatory)]
        [ValidateNotNullOrWhiteSpace()]
        [ValidateScript({ Test-Path $_ -PathType Container })]
        [string]$PythonVersion,

        [Parameter(Mandatory)]
        [ValidateNotNullOrWhiteSpace()]
        [ValidateScript({ Test-Path $_ -PathType Container })]
        [string]$ProjectPath,

        [Parameter(Mandatory)]
        [ValidateNotNullOrWhiteSpace()]
        [string]$PackageName
    )

    $PythonVersion = (Resolve-Path $PythonVersion).Path
    $ProjectPath = (Resolve-Path $ProjectPath).Path

    $EnvName = ".venv"
    if ($Suffix) {
        $EnvName = ".venv-$Suffix"
    }

    $PythonExe = Join-Path $PythonVersion "python.exe"
    $EnvPath = Join-Path $ProjectPath $EnvName
    $PackagePath = Join-Path $ProjectPath $PackageName

    if (-not (Test-Path $PythonExe -PathType Leaf)) {
        Write-Error "Python.exe does not exist: $PythonExe"
        return
    }

    if (-not (Test-Path $PackagePath -PathType Container)) {
        Write-Error "Package does not exist: $PackagePath"
        return
    }

    if (Test-Path $EnvPath) {
        Write-Information "Virtual environment already exists: $EnvName" -InformationAction Continue
    }
    else {
        Write-Information "Creating venv: $EnvName..." -InformationAction Continue

        & $PythonExe -m venv $EnvPath

        Write-Information "Done!" -InformationAction Continue
    }

    Write-Information "Installing packages..." -InformationAction Continue

    # core: Switch python.exe to .venv
    $PythonExe = Join-Path $EnvPath "Scripts\python.exe"
    & $PythonExe -m pip install -e "${PackagePath}[dev]"

    Write-Information "Done!" -InformationAction Continue
}

New-Env `
    -Suffix "v3.14" `
    -PythonVersion (Join-Path $env:PYTHONS "v3.14") `
    -ProjectPath (Join-Path $env:PROJECTS "wiretap\wiretap-py") `
    -PackageName "wiretap"
