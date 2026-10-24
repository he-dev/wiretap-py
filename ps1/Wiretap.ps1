
return # Prevents accidental execution of the entire script.


$ProjectPath = "$env:USERPROFILE\stuff\craft\coding\wiretap-py"

$PythonVer = "3.14"
$PythonExe = "$ProjectPath\.venv-v$PythonVer\Scripts\python.exe"


# mypy
. $PythonExe -m mypy $ProjectPath\wiretap\src\wiretap\__init__.py


# wiretap: build
. $PythonExe -m pip wheel $ProjectPath\wiretap -w $ProjectPath\.dist\wiretap

# the newer build tool
. $PythonExe -m build --wheel --outdir $ProjectPath\.dist\wiretap $ProjectPath\wiretap


# Gets the latest version.

$Packages = Get-ChildItem -Path $ProjectPath\.dist\wiretap\wiretap-*.whl
$LastPackage = $Packages | Sort-Object -Property { if ($_.Name -match "-([0-9\.]+)") { [version]$matches[1] } } -Descending | Select-Object -First 1
Write-Host $($LastPackage.Name)



# wiretap: check & upload
# note: Requires pypi-token in C:\Users\<USER>\.pypirc

. $PythonExe -m twine check $ProjectPath\.dist\wiretap\$($LastPackage.Name)

. $PythonExe -m twine upload $ProjectPath\.dist\wiretap\$($LastPackage.Name) 

