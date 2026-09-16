#!/usr/bin/env python3
"""Build a shareable installer archive, excluding local generated configurations."""
from pathlib import Path
import hashlib
import zipfile
from install import VERSION

root = Path(__file__).resolve().parent.parent
output = root / "dist" / f"kobil-sdk-xcode-{VERSION}.zip"
output.parent.mkdir(exist_ok=True)
files = ["xcode-plugin/install.py", "xcode-plugin/README.md", "docs/backend.md"]
with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
    for name in files:
        entry = zipfile.ZipInfo(name, date_time=(2026, 1, 1, 0, 0, 0))
        entry.compress_type = zipfile.ZIP_DEFLATED
        entry.external_attr = 0o100644 << 16
        archive.writestr(entry, (root / name).read_bytes())
digest = hashlib.sha256(output.read_bytes()).hexdigest()
output.with_suffix(".zip.sha256").write_text(f"{digest}  {output.name}\n")
print(output)
print(f"SHA-256: {digest}")
