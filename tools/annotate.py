"""Print a text file as one GitHub Actions annotation (readable without the log)."""
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass
from pathlib import Path

path = Path(sys.argv[1])
text = path.read_text(encoding='utf-8', errors='replace') if path.exists() else f'{path} not found'
text = text[-12000:].replace('%', '%25').replace('\r', '').replace('\n', '%0A')
print(f'::error title={sys.argv[2] if len(sys.argv) > 2 else path.name}::{text}')
