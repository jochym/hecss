#!/usr/bin/env python3
"""
Build documentation from marimo notebooks.

1. Export marimo notebooks to QMD format
2. Run quartodoc build for API reference
3. Render Quarto site
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
QUARTO_DIR = PROJECT_ROOT / "_quarto"
DOCS_DIR = PROJECT_ROOT / "_docs"

# Tutorial notebooks to export as QMD (for narrative docs)
TUTORIAL_NOTEBOOKS = [
    "01_vasp_tutorial.py",
    "05_vasp_workflow.py", 
    "10_background.py",
    "15_monitor.py",
    "00_setup.py",
    "index.py",
]

# Core notebooks for quartodoc (API reference)
# These are already handled by quartodoc directly from hecss package

def run_cmd(cmd, cwd=None):
    """Run a command and return result."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result


def export_notebooks():
    """Export marimo notebooks to QMD format."""
    print("=== Exporting notebooks to QMD ===")
    
    for nb in TUTORIAL_NOTEBOOKS:
        nb_path = NOTEBOOKS_DIR / nb
        if not nb_path.exists():
            print(f"Warning: {nb} not found, skipping")
            continue
        
        output = QUARTO_DIR / nb.replace('.py', '.qmd')
        result = run_cmd([
            "marimo", "export", "md", 
            str(nb_path), 
            "-o", str(output),
            "--flavor", "qmd"
        ])
        
        if result.returncode != 0:
            print(f"Failed to export {nb}")
            return False
    
    return True


def build_quartodoc():
    """Build API reference with quartodoc."""
    print("=== Building quartodoc API reference ===")
    
    result = run_cmd(["quartodoc", "build"], cwd=PROJECT_ROOT)
    return result.returncode == 0


def render_quarto():
    """Render Quarto site."""
    print("=== Rendering Quarto site ===")
    
    # Render all QMD files from _quarto directory
    result = run_cmd(["quarto", "render", "*.qmd", "--to", "html"], cwd=QUARTO_DIR)
    return result.returncode == 0


def main():
    # Ensure _quarto directory exists
    QUARTO_DIR.mkdir(exist_ok=True)
    DOCS_DIR.mkdir(exist_ok=True)
    
    # Step 1: Export notebooks to QMD
    if not export_notebooks():
        print("Notebook export failed!")
        return 1
    
    # Step 2: Build quartodoc API reference
    if not build_quartodoc():
        print("Quartodoc build failed!")
        return 1
    
    # Step 3: Render Quarto site
    if not render_quarto():
        print("Quarto render failed!")
        return 1
    
    print("\nDocumentation build complete!")
    print(f"Output: {DOCS_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())