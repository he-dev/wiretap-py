
function New-Env {
    param(
        [Parameter(Mandatory)]
        [ValidateNotNullOrWhiteSpace()]
        [ValidateScript({ Test-Path $_ -PathType Container })]
        [string]$PythonPath,

        [Parameter(Mandatory)]
        [ValidateNotNullOrWhiteSpace()]
        [ValidateScript({ Test-Path $_ -PathType Container })]
        [string]$ProjectPath,

        [Parameter()]
        [string]$Label,

        # Requirements filenames relative to ProjectPath.
        [Parameter()]
        [ValidateNotNullOrWhiteSpace()]
        [string[]]$Requirements = @("requirements.txt")
    )

    $PythonPath = (Resolve-Path $PythonPath).Path
    $ProjectPath = (Resolve-Path $ProjectPath).Path

    $EnvName = ".venv"
    if ($Label) {
        $EnvName = ".venv-$Label"
    }

    $PythonExe = Join-Path $PythonPath "python.exe"
    $EnvPath = Join-Path $ProjectPath $EnvName

    if (-not (Test-Path $PythonExe -PathType Leaf)) {
        Write-Error "Python.exe does not exist at '$PythonExe'."
        return
    }

    if (Test-Path $EnvPath) {
        Write-Information "Reusing the virtual environment at '$EnvPath'." -InformationAction Continue
    }
    else {
        Write-Information "Creating a virtual environment at '$EnvPath'..." -InformationAction Continue

        & $PythonExe -m venv $EnvPath

        if ($LASTEXITCODE -ne 0) {
            Write-Error "Could not create the virtual environment '$EnvName' in '$EnvPath' (Python exited with code $LASTEXITCODE)."
            return
        }
    }

    $PythonExe = Join-Path $EnvPath "Scripts\python.exe"
    if (-not (Test-Path -LiteralPath $PythonExe -PathType Leaf)) {
        Write-Error "The virtual environment's Python executable does not exist at '$PythonExe'."
        return
    }

    $PipArguments = @("-m", "pip", "install")
    foreach ($Requirement in $Requirements) {
        $RequirementsPath = Join-Path $ProjectPath $Requirement
        if (-not (Test-Path -LiteralPath $RequirementsPath -PathType Leaf)) {
            Write-Error "Requirements file does not exist at '$RequirementsPath'."
            return
        }
        $PipArguments += "--requirement", $RequirementsPath
    }

    Write-Information "Installing dependencies from '$($Requirements -join "', '")'..." -InformationAction Continue
    & $PythonExe @PipArguments

    if ($LASTEXITCODE -ne 0) {
        Write-Error "Could not install dependencies in '$EnvPath' (pip exited with code $LASTEXITCODE)."
        return
    }

    Write-Information "Dependencies installed successfully." -InformationAction Continue
}

New-Env `
    -PythonPath (Join-Path $env:PYTHONS "v3.14.7") `
    -Label "v3.14" `
    -ProjectPath (Join-Path $env:USERPROFILE\stuff\craft\coding "wiretap-py")
