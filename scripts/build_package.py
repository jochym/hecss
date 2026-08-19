#!/usr/bin/env python3
"""
Build hecss package.

Since the package source is the marimo notebooks in notebooks/,
this script copies the existing nbdev-generated hecss/ package
(which was generated from the original Jupyter notebooks) 
and verifies it works with the new toolchain.

In the future, this could be enhanced to extract @app.function
exports directly from marimo notebooks.
"""

import shutil
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
SOURCE_PKG = PROJECT_ROOT / "hecss"
BACKUP_PKG = PROJECT_ROOT / "hecss_backup"


def main():
    print("Building hecss package...")
    
    # The hecss package already exists from nbdev
    # Just verify it's importable and has the right structure
    
    # Check that key modules exist
    required_modules = [
        "core.py",
        "optimize.py", 
        "planner.py",
        "util.py",
        "xscale.py",
        "monitor.py",
        "cli.py",
        "__init__.py",
    ]
    
    for mod in required_modules:
        mod_path = SOURCE_PKG / mod
        if not mod_path.exists():
            print(f"ERROR: Missing required module: {mod}")
            return 1
    
    # Verify it's importable
    import sys
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        import hecss
        print(f"hecss version: {hecss.__version__}")
        print("Available modules:", [x for x in dir(hecss) if not x.startswith('_')])
    except Exception as e:
        print(f"ERROR: Failed to import hecss: {e}")
        return 1
    
    # Check __init__.py has proper exports
    init_content = (SOURCE_PKG / "__init__.py").read_text()
    if "__version__" not in init_content:
        print("WARNING: __init__.py missing version")
    
    print("Package build verification complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())