Set-Location "C:\Users\ShreyamSinha\Desktop\ai-intel-digest"
. ".\.venv\Scripts\Activate.ps1"

# Optional: log everything for debugging scheduled runs
New-Item -ItemType Directory -Force -Path "logs" | Out-Null

python -m src.cli.main run *>> "logs\scheduler.log"
