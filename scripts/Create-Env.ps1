
param(
    [Parameter()]
    [string]$Name = ".venv"
)

$EnvPath="$PSScriptRoot\$Name"

if(Test-Path $EnvPath) {
    Write-Error "This project already contains virtual environment '$Name'!" -InformationAction Continue
    return
}

Write-Information "Creating virtual environment..." -InformationAction Continue

"$env:PYTHON\v3.10\python.exe -m venv $EnvPath" | Invoke-Expression
Write-Information "Done!" -InformationAction Continue

Write-Information "Installing packages..." -InformationAction Continue

"$EnvPath\Scripts\python.exe -m pip install -r $PSScriptRoot\wiretap\requirements.txt" | Invoke-Expression
"$EnvPath\Scripts\python.exe -m pip install -r $PSScriptRoot\wiretap_sqlserver\requirements.txt" | Invoke-Expression

Write-Information "Done!" -InformationAction Continue
