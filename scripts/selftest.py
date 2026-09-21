from pathlib import Path
import subprocess
import sys


project_root = Path(__file__).resolve().parents[1]
result = subprocess.run(
    ["node", "--env-file=.env", "mattehjelpen"],
    cwd=project_root,
)

sys.exit(result.returncode)