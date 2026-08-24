#!/usr/bin/env python3
"""
Build hecss package from marimo notebooks.
AST-based extraction from marimo @app.cell functions.
"""

import ast
import textwrap
import re
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Set

PROJECT_ROOT = Path(__file__).parent.parent
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
OUTPUT_DIR = PROJECT_ROOT / "hecss"
TESTS_DIR = PROJECT_ROOT / "tests"

MODULE_EXPORTS = {
    "core": ["HECSS", "_disp_dists"],
    "optimize": ["make_sampling", "get_sample_weights", "refit"],
    "planner": ["plan_T_scan"],
    "util": ["select_asap_model", "create_asap_calculator", "normalize_conf",
             "load_dfset", "get_dfset_len", "write_dfset", "calc_init_xscale",
             "get_cell_data", "flatten"],
    "monitor": ["plot_band_set", "plot_bands", "plot_bands_file", "show_dc_conv",
                "build_bnd_lst", "build_omega", "plot_omega", "monitor_phonons",
                "plot_stats", "monitor_stats", "moving_average", "ewma", "plot_hist",
                "plot_virial_stat", "plot_acceptance_history", "plot_dofmu_stat",
                "plot_xs_stat", "THz"],
    "monitor_bands": ["plot_band_set", "plot_bands", "plot_bands_file"],
    "monitor_phonons": ["monitor_phonons", "plot_omega", "run_alamode"],
    "monitor_stats": ["monitor_stats", "plot_acceptance_history", "plot_stats"],
    "monitor_virial": ["plot_virial_stat", "plot_dofmu_stat", "plot_xs_stat"],
    "xscale": ["plot_virial_stat"],
    "dof_map": [],
    "mh": ["HECSS_MH_Sampler", "calc_init_xscale", "write_dfset"],
    "index": [],
    "cli": ["hecss_sampler", "calculate_xscale", "reshape_sample", "plot_stats",
            "plot_bands", "dfset_writer", "run_cli_cmd", "_version_message"],
}

CORE_IMPORTS = '''"""Generated from notebooks/{module}.py by build.py"""

from __future__ import annotations

import sys
import pathlib
import itertools
from fastcore.basics import patch
import numpy as np
from numpy import log, exp, sqrt, linspace, dot
import scipy
from scipy import stats
from scipy.special import expit
from tqdm.auto import tqdm
from itertools import islice
from collections import Counter
from matplotlib import pyplot as plt
import ase
import ase.units as un
from ase.calculators import calculator
from ase.data import chemical_symbols
from ase import Atoms
import spglib
from spglib import find_primitive, get_symmetry_dataset

'''

CLI_IMPORTS = '''"""Generated from notebooks/02_cli.py by build.py"""

from __future__ import annotations

import sys
import pathlib
import itertools
from fastcore.basics import patch
import numpy as np
from numpy import log, exp, sqrt, linspace, dot
import scipy
from scipy import stats
from scipy.special import expit
from tqdm.auto import tqdm
from itertools import islice
from collections import Counter
from matplotlib import pyplot as plt
import ase
import ase.units as un
from ase.calculators import calculator
from ase.data import chemical_symbols
from ase import Atoms
import spglib
from spglib import find_primitive, get_symmetry_dataset
import click
import hecss

'''

MONITOR_BANDS_IMPORTS = '''"Generated from notebooks/monitor_bands.py by build.py"

import sys
import pathlib
import itertools
from fastcore.basics import patch
import numpy as np
from numpy import log, exp, sqrt, linspace, dot
import scipy
from scipy import stats
from scipy.special import expit
from tqdm.auto import tqdm
from itertools import islice
from collections import Counter
from matplotlib import pyplot as plt
import ase
import ase.units as un
from ase.units import _hplanck, J
THz = 1e12 * _hplanck * J  # THz in eV
from ase.calculators import calculator
from ase.data import chemical_symbols
from ase import Atoms
import spglib
from spglib import find_primitive, get_symmetry_dataset
from numpy import loadtxt

'''

MONITOR_PHONONS_IMPORTS = '''"Generated from notebooks/monitor_phonons.py by build.py"

import sys
import pathlib
import itertools
from fastcore.basics import patch
import numpy as np
from numpy import log, exp, sqrt, linspace, dot
import scipy
from scipy import stats
from scipy.special import expit
from tqdm.auto import tqdm
from itertools import islice
from collections import Counter
from matplotlib import pyplot as plt
import ase
import ase.units as un
from ase.calculators import calculator
from ase.data import chemical_symbols
from ase import Atoms
import spglib
from spglib import find_primitive, get_symmetry_dataset
import subprocess

'''

MONITOR_STATS_IMPORTS = '''"Generated from notebooks/monitor_stats.py by build.py"

import sys
import pathlib
import itertools
from fastcore.basics import patch
import numpy as np
from numpy import log, exp, sqrt, linspace, dot
import scipy
from scipy import stats
from scipy.special import expit
from tqdm.auto import tqdm
from itertools import islice
from collections import Counter
from matplotlib import pyplot as plt
import ase
import ase.units as un
from ase.calculators import calculator
from ase.data import chemical_symbols
from ase import Atoms
import spglib
from spglib import find_primitive, get_symmetry_dataset
from hecss.util import get_dfset_len, load_dfset

'''

MONITOR_VIRIAL_IMPORTS = '''"Generated from notebooks/monitor_virial.py by build.py"

import sys
import pathlib
import itertools
from fastcore.basics import patch
import numpy as np
from numpy import log, exp, sqrt, linspace, dot
import scipy
from scipy import stats
from scipy.special import expit
from tqdm.auto import tqdm
from itertools import islice
from collections import Counter
from matplotlib import pyplot as plt
import ase
import ase.units as un
from ase.calculators import calculator
from ase.data import chemical_symbols
from ase import Atoms
import spglib
from spglib import find_primitive, get_symmetry_dataset
from hecss.util import get_cell_data
from collections import Counter

'''

MODULE_IMPORTS = {
    "cli": CLI_IMPORTS,
    "monitor_bands": MONITOR_BANDS_IMPORTS,
    "monitor_phonons": MONITOR_PHONONS_IMPORTS,
    "monitor_stats": MONITOR_STATS_IMPORTS,
    "monitor_virial": MONITOR_VIRIAL_IMPORTS,
}


def extract_module_name(source: str) -> Optional[str]:
    """Extract module name from #| default_exp marker."""
    for line in source.split('\n'):
        line = line.strip()
        if line.startswith('#| default_exp'):
            parts = line.split()
            if len(parts) >= 3:
                return parts[2]
    return None


def normalize_marker(marker: Optional[str]) -> str:
    if not marker:
        return "export"
    marker = marker.strip().lower()
    if marker in ('export', 'exporti'):
        return "export"
    elif marker == 'test':
        return "test"
    elif marker in ('hide', 'asap', 'default_exp'):
        return "hide"
    else:
        return "export"


def should_export(name: str, module_name: str) -> bool:
    """Check if a name should be exported from a module."""
    exports = MODULE_EXPORTS.get(module_name, None)
    if exports is None:
        # Module not in MODULE_EXPORTS -> use default behavior (export non-private)
        if name.startswith('_'):
            return False
        if name in ['app', '__generated_with', '_', 'mo', 'plt', 'np', 'stats', 'pd']:
            return False
        return True
    
    # Module has explicit exports list (including empty list = export nothing)
    if name in exports:
        return True
    if name.startswith('_'):
        return False
    if name in ['app', '__generated_with', '_', 'mo', 'plt', 'np', 'stats', 'pd']:
        return False
    return False


@dataclass
class NotebookExtractor:
    notebook_path: Path
    module_name: str
    
    definitions: Dict[str, str] = field(default_factory=dict)
    patches: List[Tuple[str, str, str]] = field(default_factory=list)  # (target_class, method_name, source)
    cell_markers: Dict[int, str] = field(default_factory=dict)
    
    def extract(self) -> Dict[str, str]:
        source = self.notebook_path.read_text()
        self._parse_markers(source)
        tree = ast.parse(source)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and self._is_app_cell(node):
                cell_source = ast.get_source_segment(source, node)
                if cell_source:
                    self._process_cell(node, cell_source, source)
        
        return self.definitions
    
    def _parse_markers(self, source: str):
        """Parse #| markers from source and associate with cell indices."""
        tree = ast.parse(source)
        cells = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and self._is_app_cell(node):
                cells.append((node.lineno, node))
        cells.sort(key=lambda x: x[0])
        
        lines = source.split('\n')
        current_marker = None
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('#|'):
                current_marker = stripped[2:].strip()
                if current_marker.startswith('default_exp'):
                    self.module_name = current_marker.split()[2] if len(current_marker.split()) >= 3 else self.module_name
            elif stripped.startswith('@app.cell'):
                for idx, (lineno, node) in enumerate(cells):
                    if lineno == i + 1:
                        self.cell_markers[idx] = normalize_marker(current_marker)
                        current_marker = None
                        break
    
    def _is_app_cell(self, node: ast.FunctionDef) -> bool:
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
    
    def _process_cell(self, node: ast.FunctionDef, cell_source: str, full_source: str):
        """Extract definitions from a cell."""
        cell_tree = ast.parse(cell_source)
        
        for item in cell_tree.body:
            if isinstance(item, ast.FunctionDef) and item.name == node.name:
                for stmt in item.body:
                    self._extract_from_statement(stmt, cell_source)
    
    def _extract_from_statement(self, stmt, cell_source: str):
        if isinstance(stmt, ast.ClassDef):
            self._extract_class(stmt, cell_source)
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._extract_function(stmt, cell_source)
        elif isinstance(stmt, ast.Assign):
            self._extract_assignment(stmt, cell_source)
    
    def _extract_class(self, node: ast.ClassDef, cell_source: str):
        source = self._get_source_with_decorators(node, cell_source)
        if source:
            source = textwrap.dedent(source)
            self.definitions[node.name] = source
            
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    method_source = self._get_source_with_decorators(item, cell_source)
                    if method_source:
                        method_source = textwrap.dedent(method_source)
                        self.definitions[f"{node.name}.{item.name}"] = method_source
    
    def _extract_function(self, node: ast.FunctionDef, cell_source: str):
        # Get source including decorators
        source = self._get_source_with_decorators(node, cell_source)
        if source:
            source = textwrap.dedent(source)
            self.definitions[node.name] = source
            
            # Check for @patch decorator
            for decorator in node.decorator_list:
                if isinstance(decorator, ast.Name) and decorator.id == 'patch':
                    if node.args.args:
                        first_arg = node.args.args[0]
                        if first_arg.annotation:
                            if isinstance(first_arg.annotation, ast.Name):
                                target_class = first_arg.annotation.id
                            elif isinstance(first_arg.annotation, ast.Attribute):
                                target_class = first_arg.annotation.attr
                            else:
                                target_class = None
                            if target_class:
                                self.patches.append((target_class, node.name, source))
                            break
    
    def _get_source_with_decorators(self, node: ast.FunctionDef, source: str) -> str:
        """Get function source including decorators."""
        if not node.decorator_list:
            return ast.get_source_segment(source, node)
        
        lines = source.splitlines(keepends=True)
        start_line = node.decorator_list[0].lineno - 1
        end_line = node.end_lineno if hasattr(node, 'end_lineno') else node.body[-1].end_lineno
        end_line = end_line - 1
        
        extracted = ''.join(lines[start_line:end_line + 1])
        return textwrap.dedent(extracted)
    
    def _extract_assignment(self, node: ast.Assign, cell_source: str):
        if len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            source = ast.get_source_segment(cell_source, node)
            if source:
                source = textwrap.dedent(source)
                self.definitions[name] = source


def generate_module(module_name: str, definitions: Dict[str, str], patches: List[Tuple[str, str, str]]) -> str:
    """Generate a clean module file from extracted definitions."""
    lines = [
        f'"""Generated from notebooks/{module_name}.py by build.py"""',
        '',
    ]
    
# Module-specific imports
    if module_name == 'cli':
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
            'import click',
            'import hecss',
            '',
        ])
    elif module_name in MODULE_IMPORTS:
        # Add the module-specific imports (without __future__ which we add below)
        lines.extend(MODULE_IMPORTS[module_name].split('\n'))
    else:
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
    patch_functions = set()
    patch_sources = {}
    
    for target_class, method_name, source in patches:
        patch_functions.add(method_name)
        patch_sources[method_name] = source
    
    for name, source in definitions.items():
        if '.' in name:
            continue  # Skip methods (part of classes)
        # Skip patch functions - they'll be added in patch application
        if name in patch_functions:
            continue
        if not should_export(name, module_name):
            continue
        
        source_stripped = source.strip()
        if source_stripped.startswith('class '):
            classes[name] = source
        elif source_stripped.startswith('def ') or source_stripped.startswith('async def '):
            functions[name] = source
        else:
            assignments[name] = source
    
    # Add assignments first
    for name in sorted(assignments.keys()):
        lines.append(definitions[name])
        lines.append('')
    
    # Add class definitions
    for name in sorted(classes.keys()):
        lines.append(classes[name])
        lines.append('')
    
    # Add function definitions (non-patch)
    for name in sorted(functions.keys()):
        lines.append(functions[name])
        lines.append('')
    
    # Apply patches
    if patches:
        lines.append('')
        lines.append('# Apply patches from @patch decorators')
        lines.append('from fastcore.basics import patch as _patch')
        for target_class, method_name, source in patches:
            if target_class in definitions:
                if method_name in patch_sources:
                    lines.append(patch_sources[method_name])
                    lines.append('')
                lines.append(f'{target_class}.{method_name} = _patch({method_name})')
        lines.append('del _patch')
    
    # Add __all__
    exports = MODULE_EXPORTS.get(module_name, [])
    if exports:
        lines.append('')
        lines.append('__all__ = [' + ', '.join(f'"{name}"' for name in exports) + ']')
    
    return '\n'.join(lines)


def generate_init(modules: List[str]) -> str:
    lines = ['__version__ = "0.5.29"', '']
    
    for module in modules:
        exports = MODULE_EXPORTS.get(module, [])
        for exp in exports:
            lines.append(f'from .{module} import {exp}')
    
    lines.append('')
    return '\n'.join(lines)


def main():
    OUTPUT_DIR.mkdir(exist_ok=True)
    TESTS_DIR.mkdir(exist_ok=True)
    
    all_modules = []
    
    # Skip old monolithic monitor (replaced by split modules)
    SKIP_MODULES = {"monitor"}
    
    for nb_path in sorted(NOTEBOOKS_DIR.glob("*.py")):
        source = nb_path.read_text()
        module_name = extract_module_name(source)
        
        if not module_name:
            print(f"  WARNING: {nb_path.name} has no #| default_exp, skipping")
            continue
        
        if module_name in SKIP_MODULES:
            print(f"  Skipping {module_name} (replaced by split modules)")
            continue
        
        print(f"Processing {nb_path.name} -> {module_name}")
        extractor = NotebookExtractor(nb_path, module_name)
        definitions = extractor.extract()
        patches = extractor.patches
        
        print(f"  Found {len(definitions)} definitions, {len(patches)} patches")
        
        module_code = generate_module(module_name, definitions, patches)
        (OUTPUT_DIR / f"{module_name}.py").write_text(module_code)
        print(f"  Generated {OUTPUT_DIR / f'{module_name}.py'}")
        
        all_modules.append(module_name)
    
    # Generate __init__.py
    init_code = generate_init(all_modules)
    (OUTPUT_DIR / "__init__.py").write_text(init_code)
    print(f"Generated {OUTPUT_DIR / '__init__.py'}")
    
    print("\nBuild complete!")


if __name__ == "__main__":
    from typing import Optional
    OUTPUT_DIR = Path(__file__).parent.parent / "hecss"
    TESTS_DIR = Path(__file__).parent.parent / "tests"
    main()