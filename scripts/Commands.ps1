

$EnvName=".venv"
$EnvPath="$PSScriptRoot\..\$EnvName"
$Python="$EnvPath\Scripts\python.exe"

Write-Host "$PSScriptRoot"

"$Python -m mypy .\wiretap\src\wiretap\wiretap.py" | Invoke-Expression
"$python -m mypy .\wiretap_sqlserver\src\wiretap_sqlserver\sqlserverhandler.py" | Invoke-Expression