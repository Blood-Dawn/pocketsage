param([string]$Src="pocketsage",[string]$Out="docs/uml",[string]$Project="PocketSage")
$ErrorActionPreference="Stop"
New-Item -ItemType Directory -Force -Path $Out | Out-Null
if (!(Test-Path ".\.venv\Scripts\python.exe")) { py -m venv .venv }
$py = ".\.venv\Scripts\python.exe"
$pyreverse = ".\.venv\Scripts\pyreverse.exe"
& $py -m pip install -U pylint | Out-Default
& $pyreverse -o puml -d $Out -p $Project $Src | Out-Default
& $pyreverse -o mmd  -d $Out -p $Project $Src | Out-Default
if (Get-Command dot -ErrorAction SilentlyContinue) {
  & $pyreverse -o png -d $Out -p $Project $Src | Out-Default
} else {
  Write-Host "Graphviz 'dot' not found; skipping PNG. Use VS Code PlantUML export."
}
