#!/usr/bin/env python3
"""
Build hecss package from marimo notebooks.

Extracts class/function definitions from marimo notebook cells
and generates clean Python modules for the hecss/ package.
"""

import ast
import sys
import re
import textwrap
from pathlib import Path
from collections import defaultdict

PROJECT_ROOT = Path(__file__).parent.parent
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
OUTPUT_DIR = PROJECT_ROOT / "hecss"

# Map of notebook filename to target module name
NOTEBOOK_TO_MODULE = {
    "11_core.py": "core",
    "12_optimize.py": "optimize",
    "13_planner.py": "planner",
    "16_util.py": "util",
    "17_xscale.py": "xscale",
    "15_monitor.py": "monitor",
    "02_cli.py": "cli",
}

# Module-specific exports to include (public API)
MODULE_EXPORTS = {
    "core": ["HECSS"],
    "optimize": ["make_sampling", "get_sample_weights", "refit"],
    "planner": ["plan_T_scan"],
    "util": ["select_asap_model", "create_asap_calculator", "normalize_conf",
             "load_dfset", "get_dfset_len", "write_dfset", "calc_init_xscale",
             "get_cell_data", "flatten"],
    "xscale": ["plot_virial_stat"],
    "monitor": ["plot_band_set", "plot_bands", "plot_bands_file", "show_dc_conv",
                "build_bnd_lst", "build_omega", "plot_omega", "monitor_phonons",
                "plot_stats", "monitor_stats", "moving_average", "ewma", "plot_hist",
                "plot_virial_stat", "plot_acceptance_history", "plot_dofmu_stat", "plot_xs_stat",
                "THz"],
    "cli": ["hecss_sampler", "calculate_xscale", "reshape_sample", "plot_stats", "plot_bands",
            "dfset_writer", "run_cli_cmd", "_version_message"],
}

# Test/example variables that appear in notebooks but shouldn't be exported
TEST_VARIABLES = {
    'N', 'd', 'skip', 'm', 's', 'model', 'sys_size', 'sc', 'cryst', 'T', 'N_1', 
    'hecss', 'smpls', 'get_sample_weights', 'Tmu', 'wd_1', 'wd_2', 'wd_3', 'uni', 
    'e_dist', 'e_uni', 'usmp', 'wd_4', 'rv', 'plan', 'el', 'skip', 'NF', 'plan_1', 
    'smpls', 'ell', 'e_min', 'e_max', 'x', 'y', 'tdx', 'N_2', 'plan_2', 'smpll', 
    'ell_1', 'usmp', 'T_4', 'wd', 'x_1', 'y_1', 'tdx_1', 'x_2', 's_1', 'x_3', 
    'y_2', 'a', 'x0', 'b', 'nf_1', 'rv_1', 'N_3', 'plan_3', 'el_4', 'skip_3', 
    'NF_1', 'confs', 'b', 'c', 'unwrapped', 'model', 'oliv', 'N', 
    'sampler', 'wm', 'y', 'N_1', 'dofmu', 'xsl', 'supercell', 'sc', 'e0', 
    'eqdelta', 'eqsigma', 'nat', 'dim', 'symprec', 'symm', 'dofmap', 'dof', 
    'dofmu_1', 'mu', 'xscale', 'dofxs', 'vt', 'vta', 'mu_1', 'x', 'THz', 
    'calc_dir', 'calc_dir_2', 'CLEANUP', 'x', 'ampl', 'wdth', 
    'cryst', 'confs', 'b', 'c', 'unwrapped', 'get_cell_data',
    'app', 'ampl', 'wdth', 'd', 'e_dist', 'e_uni', 'wd_1', 'wd_2', 'wd_3', 'wd_4',
    'rv', 'plan', 'ell', 'e_min', 'e_max', 'tdx', 'N_2', 'plan_2', 'smpll',
    'ell_1', 'usmp', 'T_4', 'x_1', 'y_1', 'tdx_1', 'x_2', 's_1', 'x_3',
    'y_2', 'a', 'x0', 'b', 'nf_1', 'rv_1', 'N_3', 'plan_3', 'el_4', 'skip_3',
    'NF_1', 'e_dist', 'e_uni', 'usmp', 'wd', 'wd_1', 'wd_2', 'wd_3',
    'model', 'oliv', 'sampler', 'wm', 'y', 'dofmu', 'dofmu_1', 'dofxs',
    'vt', 'vta', 'mu_1', 'xscale', 'xscale', 'dofmap', 'dof', 'eqdelta',
    'eqsigma', 'nat', 'dim', 'symprec', 'symm', 'symm', 'dofmu', 'vt', 'vta',
    'mu', 'mu_1', 'x', 'y', 'x_1', 'y_1', 'x_2', 'y_1', 'x_2',
    'y_2', 'a', 'x0', 'b', 'nf_1', 'rv_1', 'N_3', 'plan_3', 'el_4', 'skip_3',
    'NF_1', 'e_dist', 'e_uni', 'usmp', 'wd', 'wd_1', 'wd_2', 'wd_3',
    'model', 'oliv', 'sampler', 'wm', 'y', 'dofmu', 'dofmu_1', 'dofxs',
    'vt', 'vta', 'mu_1', 'xscale', 'xscale', 'dofmap', 'dof', 'eqdelta',
    'eqsigma', 'nat', 'dim', 'symprec', 'symm', 'symm', 'dofmu', 'vt', 'vta',
    'mu', 'mu_1', 'x', 'y', 'x_1', 'y_1', 'x_2', 'y_1', 'x_2',
    'y_2', 'a', 'x0', 'b', 'nf_1', 'rv_1', 'N_3', 'plan_3', 'el_4', 'skip_3',
    'confs', 'b', 'c', 'unwrapped', 'x', 'y', 'x_1', 'y_1', 'x_2',
    'y_2', 'a', 'x0', 'b', 'nf_1', 'rv_1', 'el_4', 'skip_3', 'calc_dir',
    'calc_dir_2', 'CLEANUP', 'wdth', 'cryst', 'confs', 'b', 'c', 'unwrapped',
    'get_cell_data'
}


def should_export(name: str, module: str) -> bool:
    """Check if a name should be exported from a module."""
    # Allow names that start with _ if they're explicitly exported
    exports = MODULE_EXPORTS.get(module, [])
    if exports and name in exports:
        return True
    
    if name.startswith('_'):
        return False
    
    if name in TEST_VARIABLES:
        return False
    
    # Check if explicitly listed for this module
    if exports and name not in exports:
        return False
    
    return True


class NotebookExtractor:
    """Extract class/function definitions from marimo notebook."""
    
    def __init__(self, notebook_path: Path):
        self.notebook_path = notebook_path
        self.source = notebook_path.read_text()
        self.tree = ast.parse(self.source)
        self.definitions = {}  # name -> source code
        
    def extract(self):
        """Extract all definitions from notebook - both module-level and inside cells."""
        # First pass: module-level definitions
        for node in self.tree.body:
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                self._extract_definition(node)
            elif isinstance(node, ast.Assign):
                self._extract_module_assignment(node)
        
        # Second pass: definitions inside @app.cell decorated functions
        for node in ast.walk(self.tree):
            if isinstance(node, ast.FunctionDef) and self._is_app_cell(node):
                self._process_cell(node)
        
        return self.definitions
    
    def _is_app_cell(self, node: ast.FunctionDef) -> bool:
        """Check if function has @app.cell decorator."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if (isinstance(decorator.func, ast.Attribute) and 
                    decorator.func.attr == 'cell' and
                    isinstance(decorator.func.value, ast.Name) and
                    decorator.func.value.id == 'app'):
                    return True
            elif isinstance(decorator, ast.Attribute):
                if (decorator.attr == 'cell' and
                    isinstance(decorator.value, ast.Name) and
                    decorator.value.id == 'app'):
                    return True
        return False
    
    def _extract_definition(self, node):
        """Extract a class or function definition at module level."""
        source = ast.get_source_segment(self.source, node)
        if source:
            source = textwrap.dedent(source)
            self.definitions[node.name] = source
            
            # Also extract nested functions
            if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        nested_source = ast.get_source_segment(self.source, item)
                        if nested_source:
                            nested_source = textwrap.dedent(nested_source)
                            self.definitions[item.name] = nested_source
    
    def _extract_module_assignment(self, node):
        """Extract top-level assignments at module level."""
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if not name.startswith('_'):
                source = ast.get_source_segment(self.source, node)
                if source:
                    source = textwrap.dedent(source)
                    self.definitions[name] = source
    
    def _is_app_cell(self, node: ast.FunctionDef) -> bool:
        """Check if function has @app.cell decorator."""
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if (isinstance(decorator.func, ast.Attribute) and 
                    decorator.func.attr == 'cell' and
                    isinstance(decorator.func.value, ast.Name) and
                    decorator.func.value.id == 'app'):
                    return True
            elif isinstance(decorator, ast.Attribute):
                if (decorator.attr == 'cell' and
                    isinstance(decorator.value, ast.Name) and
                    decorator.value.id == 'app'):
                    return True
        return False
    
    def _process_cell(self, node: ast.FunctionDef):
        """Process a cell function to extract class/function definitions."""
        cell_source = ast.get_source_segment(self.source, node)
        if not cell_source:
            return
        
        cell_tree = ast.parse(cell_source)
        
        for item in cell_tree.body:
            if isinstance(item, ast.FunctionDef) and item.name == node.name:
                for stmt in item.body:
                    self._extract_from_statement(stmt, cell_source)
    
    def _extract_from_statement(self, stmt, cell_source: str):
        """Extract definitions from a statement inside a cell."""
        if isinstance(stmt, ast.ClassDef):
            self._extract_class(stmt, cell_source)
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._extract_function(stmt, cell_source)
        elif isinstance(stmt, ast.Assign):
            self._extract_assignment(stmt, cell_source)
    
    def _extract_class(self, node: ast.ClassDef, cell_source: str):
        source = ast.get_source_segment(cell_source, node)
        if source:
            source = textwrap.dedent(source)
            self.definitions[node.name] = source
            
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    method_source = ast.get_source_segment(cell_source, item)
                    if method_source:
                        method_source = textwrap.dedent(method_source)
                        self.definitions[f"{node.name}.{item.name}"] = method_source
    
    def _extract_function(self, node: ast.FunctionDef, cell_source: str):
        source = ast.get_source_segment(cell_source, node)
        if source:
            source = textwrap.dedent(source)
            self.definitions[node.name] = source
            
            # Also extract nested functions
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    nested_source = ast.get_source_segment(cell_source, item)
                    if nested_source:
                        nested_source = textwrap.dedent(nested_source)
                        self.definitions[item.name] = nested_source
    
    def _extract_assignment(self, node: ast.Assign, cell_source: str):
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            source = ast.get_source_segment(cell_source, node)
            if source:
                source = textwrap.dedent(source)
                self.definitions[name] = source
    
    def _extract_module_assignment(self, node):
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            source = ast.get_source_segment(self.source, node)
            if source:
                source = textwrap.dedent(source)
                self.definitions[name] = source


def generate_module(module_name: str, definitions: dict, exports: list) -> str:
    """Generate a clean module file from extracted definitions."""
    lines = [
        f'"""Generated from notebooks/{module_name}.py by build_package.py"""',
        '',
    ]
    
    # Core imports that most modules need
    lines.extend([
        'from __future__ import annotations',
        '',
        'import sys',
        'import pathlib',
        'import itertools',
        'from fastcore.basics import patch',
        'import numpy as np',
        'from numpy import log, exp, sqrt, linspace, dot',
        'import scipy',
        'from scipy import stats',
        'from scipy.special import expit',
        'from tqdm.auto import tqdm',
        'from itertools import islice',
        'from collections import Counter',
        'from matplotlib import pyplot as plt',
        'import ase',
        'import ase.units as un',
        'from ase.calculators import calculator',
        'from ase.data import chemical_symbols',
        'from ase import Atoms',
        'import spglib',
        'from spglib import find_primitive, get_symmetry_dataset',
        '',
    ])
    
    # Sort definitions: assignments first, then classes, then functions
    classes = {}
    functions = {}
    assignments = {}
    
    for name, source in definitions.items():
        if '.' in name:
            continue  # Skip methods (part of classes)
        if not should_export(name, module_name):
            continue
        
        source_stripped = source.strip()
        if source_stripped.startswith('class '):
            classes[name] = source
        elif source_stripped.startswith('def ') or source_stripped.startswith('async def '):
            functions[name] = source
        else:
            assignments[name] = source
    
    # Add assignments first (constants, dicts)
    for name in sorted(assignments.keys()):
        lines.append(definitions[name])
        lines.append('')
    
    # Add class definitions
    for name in sorted(classes.keys()):
        lines.append(classes[name])
        lines.append('')
    
    # Add function definitions
    for name in sorted(functions.keys()):
        lines.append(functions[name])
        lines.append('')
    
    # Add __all__ export list
    exported = [name for name in exports if name in definitions]
    if exported:
        lines.append('__all__ = [' + ', '.join(f'"{name}"' for name in exported) + ']')
    
    return '\n'.join(lines)


def should_export(name: str, module: str) -> bool:
    """Check if a name should be exported from a module."""
    # Allow names that start with _ if they're explicitly exported
    exports = MODULE_EXPORTS.get(module, [])
    if exports and name in exports:
        return True
    
    if name.startswith('_'):
        return False
    
    if name in TEST_VARIABLES:
        return False
    
    # Check if explicitly listed for this module
    if exports and name not in exports:
        return False
    
    return True


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    all_definitions = {}
    
    # Extract from each notebook
    for nb_file, module_name in NOTEBOOK_TO_MODULE.items():
        nb_path = NOTEBOOKS_DIR / nb_file
        if not nb_path.exists():
            print(f"Warning: {nb_file} not found, skipping")
            continue
        
        print(f"Processing {nb_file} -> {module_name}")
        extractor = NotebookExtractor(nb_path)
        definitions = extractor.extract()
        all_definitions[module_name] = definitions
        print(f"  Found {len(definitions)} definitions: {sorted(definitions.keys())}")
    
    # Generate modules
    for module_name, definitions in all_definitions.items():
        exports = MODULE_EXPORTS.get(module_name, [])
        module_content = generate_module(module_name, definitions, exports)
        output_path = OUTPUT_DIR / f"{module_name}.py"
        output_path.write_text(module_content)
        print(f"Generated {output_path}")
    
    # Generate __init__.py
    init_lines = [
        '__version__ = "0.5.29"',
        '',
    ]
    
    for module_name in sorted(NOTEBOOK_TO_MODULE.values()):
        exports = MODULE_EXPORTS.get(module_name, [])
        if exports:
            init_lines.append(f'from .{module_name} import {", ".join(exports)}')
    
    init_content = '\n'.join(init_lines)
    (OUTPUT_DIR / "__init__.py").write_text(init_content)
    print(f"Generated {OUTPUT_DIR / '__init__.py'}")
    
    # Verify
    import sys
    sys.path.insert(0, str(PROJECT_ROOT))
    try:
        import hecss
        print(f"\nhecss version: {hecss.__version__}")
        print("Available modules:", [x for x in dir(hecss) if not x.startswith('_')])
    except Exception as e:
        print(f"ERROR: Failed to import hecss: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    print("\nPackage build complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())