#!/usr/bin/env python3
"""
Synchronize nbdev markers from .ipynb to marimo .py notebooks.
Maps markers by content similarity between ipynb cells and marimo cells.
"""

import json
import re
import difflib
from pathlib import Path
from dataclasses import dataclass
from typing import List, Optional

NOTEBOOKS_DIR = Path("notebooks")
IPYNB_DIR = Path(".")

@dataclass
class Cell:
    index: int
    content: str
    marker: Optional[str] = None
    cell_type: str = "code"

def extract_ipynb_cells(ipynb_path: Path) -> List[Cell]:
    """Extract code cells with nbdev markers from .ipynb."""
    with open(ipynb_path) as f:
        nb = json.load(f)
    
    cells = []
    for i, cell in enumerate(nb['cells']):
        if cell['cell_type'] != 'code':
            continue
        source = ''.join(cell['source'])
        if not source.strip():
            continue
        
        # Skip marker-only cells (only contain #| comments)
        non_marker_lines = [l for l in source.split('\n') if not l.strip().startswith('#|')]
        if not any(l.strip() for l in non_marker_lines):
            continue
        
        # Find nbdev marker
        marker = None
        for line in source.split('\n'):
            line = line.strip()
            if line.startswith('#|'):
                marker = line[2:].strip()
                break
        
        cells.append(Cell(index=i, content=source, marker=marker, cell_type="code"))
    return cells

def extract_marimo_cells(py_path: Path) -> List[Cell]:
    """Extract cells from marimo .py notebook."""
    source = py_path.read_text()
    
    # Split by @app.cell decorators
    cells = []
    # Pattern matches @app.cell or @app.cell(...) followed by function
    pattern = r'(^@app\.cell[^\n]*\n(?:^def _\(.*?\n(?:^    .*\n)*^    return[^\n]*\n))'
    
    # Simpler: split by function definitions with @app.cell
    parts = re.split(r'(?=^@app\.cell)', source, flags=re.MULTILINE)
    
    cell_idx = 0
    for part in parts:
        part = part.strip()
        if not part or part.startswith('import marimo') or part.startswith('__generated_with') or part.startswith('app = marimo'):
            continue
        if not part.startswith('@app.cell'):
            continue
        
        # Extract the function body content (without decorator and return)
        lines = part.split('\n')
        body_lines = []
        in_function = False
        for line in lines:
            if line.strip().startswith('def _('):
                in_function = True
                continue
            if in_function:
                if line.strip().startswith('return'):
                    continue
                if line.startswith('    '):
                    body_lines.append(line[4:])  # Remove indent
                else:
                    break
        
        content = '\n'.join(body_lines).strip()
        if content:
            cells.append(Cell(index=cell_idx, content=content, marker=None))
            cell_idx += 1
    
    return cells

def normalize_marker(marker: Optional[str]) -> str:
    """Normalize nbdev marker to standard form."""
    if not marker:
        return "export"  # Default
    
    marker = marker.strip().lower()
    if marker in ('export', 'exporti'):
        return "export"
    elif marker == 'test':
        return "test"
    elif marker == 'hide':
        return "hide"
    elif marker.startswith('default_exp'):
        return marker  # Keep default_exp as-is
    else:
        return "export"  # Default fallback

def similarity(a: str, b: str) -> float:
    """Compute similarity between two strings."""
    return difflib.SequenceMatcher(None, a[:500], b[:500]).ratio()

def match_cells(ipynb_cells: List[Cell], marimo_cells: List[Cell]) -> List[tuple]:
    """Match ipynb cells to marimo cells by content similarity."""
    matches = []
    used_marimo = set()
    
    for ipynb_cell in ipynb_cells:
        if not ipynb_cell.marker:
            continue
            
        best_match = None
        best_score = 0.0
        
        for j, marimo_cell in enumerate(marimo_cells):
            if j in used_marimo:
                continue
            score = similarity(ipynb_cell.content, marimo_cell.content)
            if score > best_score and score > 0.3:  # Threshold
                best_score = score
                best_match = j
        
        if best_match is not None:
            matches.append((ipynb_cell, marimo_cells[best_match], best_score))
            used_marimo.add(best_match)
        else:
            print(f"  WARNING: No match for ipynb cell {ipynb_cell.index} (marker: {ipynb_cell.marker})")
            print(f"    Content preview: {ipynb_cell.content[:100]}")
    
    return matches

def apply_markers_to_py(py_path: Path, matches: List[tuple], marimo_cells: List[Cell]):
    """Apply normalized markers to marimo .py file."""
    source = py_path.read_text()
    
    # Build a map of cell index -> normalized marker (deduplicate)
    cell_markers = {}
    for ipynb_cell, marimo_cell, score in matches:
        if marimo_cell.index in cell_markers:
            continue  # Skip duplicate
        normalized = normalize_marker(ipynb_cell.marker)
        cell_markers[marimo_cell.index] = normalized
        print(f"  Cell {marimo_cell.index}: {ipynb_cell.marker} -> #{normalized} (score: {score:.2f})")
    
    # Apply markers by inserting inside function body (after def _():)
    lines = source.split('\n')
    output = []
    i = 0
    cell_idx = -1
    in_cell_def = False
    
    while i < len(lines):
        line = lines[i]
        
        # Detect @app.cell decorator
        if line.strip().startswith('@app.cell'):
            cell_idx += 1
            in_cell_def = True
        
        # Detect function definition (def _():)
        if in_cell_def and line.strip().startswith('def _('):
            output.append(line)
            # Insert marker comment inside function body
            if cell_idx in cell_markers:
                marker = cell_markers[cell_idx]
                output.append(f"    #| {marker}")
            in_cell_def = False
            i += 1
            continue
        
        output.append(line)
        i += 1
    
    py_path.write_text('\n'.join(output))
    print(f"  Applied {len(cell_markers)} markers to {py_path.name}")

# Notebook stem -> module name mapping for default_exp
DEFAULT_EXP_MAP = {
    "00_setup": "setup",
    "01_vasp_tutorial": "vasp_tutorial",
    "02_cli": "cli",
    "03_monitor_stats": "monitor_stats",
    "04_monitor_phonons": "monitor_phonons",
    "05_vasp_workflow": "vasp_workflow",
    "10_background": "background",
    "11_core": "core",
    "11_parallel": "parallel",
    "11_parsample": "parsample",
    "11_parwidth": "parwidth",
    "12_optimize": "optimize",
    "13_planner": "planner",
    "15_monitor": "monitor",
    "15_monitor_bands": "monitor_bands",
    "15_monitor_phonons": "monitor_phonons",
    "15_monitor_stats": "monitor_stats",
    "15_monitor_virial": "monitor_virial",
    "16_util": "util",
    "17_xscale": "xscale",
    "72_dof_map": "dof_map",
    "99_mh": "mh",
    "index": "index",
}

def ensure_default_exp(py_path: Path, stem: str):
    """Ensure notebook has #| default_exp marker."""
    source = py_path.read_text()
    if '#| default_exp' in source:
        return
    
    module_name = DEFAULT_EXP_MAP.get(stem)
    if not module_name:
        return
    
    # Insert after app = marimo.App()
    lines = source.split('\n')
    output = []
    for line in lines:
        output.append(line)
        if line.strip() == 'app = marimo.App()':
            output.append(f"#| default_exp {module_name}")
    
    py_path.write_text('\n'.join(output))
    print(f"  Added #| default_exp {module_name} to {py_path.name}")

def main():
    # Process all notebooks
    for py_file in sorted(NOTEBOOKS_DIR.glob("*.py")):
        stem = py_file.stem
        # Try multiple naming patterns
        candidates = [
            IPYNB_DIR / f"{stem}.ipynb",
            IPYNB_DIR / f"{stem.capitalize()}.ipynb",
            IPYNB_DIR / f"{stem.upper()}.ipynb",
            IPYNB_DIR / f"{stem.lower()}.ipynb",
        ]
        # Handle special cases with different naming conventions
        if stem == "00_setup":
            candidates.append(IPYNB_DIR / "00_Setup.ipynb")
        elif stem == "01_vasp_tutorial":
            candidates.append(IPYNB_DIR / "01_VASP_Tutorial.ipynb")
        elif stem == "10_background":
            candidates.append(IPYNB_DIR / "10_Background.ipynb")
        elif stem == "72_dof_map":
            candidates.append(IPYNB_DIR / "72_DOF_map.ipynb")
        
        ipynb_file = None
        for c in candidates:
            if c.exists():
                ipynb_file = c
                break
        if not ipynb_file:
            print(f"SKIP: {py_file.name} - no matching .ipynb")
            continue
        
        print(f"\nProcessing {py_file.name} <-> {ipynb_file.name}")
        
        ipynb_cells = extract_ipynb_cells(ipynb_file)
        marimo_cells = extract_marimo_cells(py_file)
        
        print(f"  ipynb cells with markers: {sum(1 for c in ipynb_cells if c.marker)}")
        print(f"  marimo cells: {len(marimo_cells)}")
        
        matches = match_cells(ipynb_cells, marimo_cells)
        apply_markers_to_py(py_file, matches, marimo_cells)
        
        # Ensure default_exp marker exists
        ensure_default_exp(py_file, stem)

if __name__ == "__main__":
    main()