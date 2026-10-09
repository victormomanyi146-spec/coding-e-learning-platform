"""Turn Vite's built index into a Django template using static manifest paths."""
from pathlib import Path
import re
import sys

source = Path(sys.argv[1]).read_text(encoding="utf-8")
target = Path(sys.argv[2])

pattern = re.compile(r'((?:src|href)=")/static/react/assets/([^\"]+)(")')
source = pattern.sub(
    lambda match: f"{match.group(1)}{{% static 'react/assets/{match.group(2)}' %}}{match.group(3)}",
    source,
)
if "/static/react/assets/" in source:
    raise SystemExit("Unconverted React asset path remains in index.html")
source = "{% load static %}\n" + source

target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(source, encoding="utf-8")
print(f"Prepared Django React entry template: {target}")
