$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectParent = Split-Path -Parent $projectRoot
$entryPoint = Join-Path $projectRoot "main.py"
$arguments = @(
    "-m", "PyInstaller",
    "--noconfirm",
    "--clean",
    "--onefile",
    "--windowed",
    "--name", "TheFivefoldDepths",
    "--paths", $projectParent,
    "--collect-all", "pygame"
)

$assetsDirectory = Join-Path $projectRoot "assets"
if (Test-Path $assetsDirectory -PathType Container) {
    $arguments += @("--add-data", "$assetsDirectory;assets")
}
$arguments += $entryPoint

Push-Location $projectParent
try {
    & python @arguments
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE."
    }
}
finally {
    Pop-Location
}

Write-Output "Built $projectParent\dist\TheFivefoldDepths.exe"
