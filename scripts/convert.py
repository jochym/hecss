#!/usr/bin/env python3
"""
Generic tag-based conversion from marimo notebooks to Python modules.

Uses #| tags (default_exp, export, hide) as the source of information.
No hardcoded exceptions - the pipeline is generic and tag-driven.

The input is a marimo notebook (Python file with @app.cell decorators).
The output is a clean Python module with:
- #| export cells included
- #| hide cells excluded
- mo.md() calls removed
- Imports collected at top
- __all__ list generated from exported names

Usage:
    python scripts/convert.py                    # Convert all notebooks
    python scripts/convert.py notebooks/11_core.py  # Convert single notebook
"""

import re
import sys
import ast
import textwrap
from pathlib import Path
from typing import Optional, Tuple, List

PROJECT_ROOT = Path(__file__).parent.parent
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
OUTPUT_DIR = PROJECT_ROOT / "hecss"



def detect_module_merges(notebooks_dir: Path) -> dict:
    """
    Detect which notebooks should be merged based on #| default_exp tags.
    
    In nbdev, #| default_exp determines which module a notebook exports to.
    Multiple notebooks can export to the same module - they should be merged.
    
    Returns dict mapping module_name to list of notebook names.
    """
    import re
    from collections import defaultdict
    
    # Group notebooks by their #| default_exp target
    default_exp_groups = defaultdict(list)
    for nb in sorted(notebooks_dir.glob("*.py")):
        if nb.name.startswith('_'):
            continue
        
        source = nb.read_text()
        match = re.search(r'#\|\s+default_exp\s+(\S+)', source)
        if match:
            module_name = match.group(1)
            default_exp_groups[module_name].append(nb.name)
    
    # Merge notebooks that target the same module
    merges = {}
    for module_name, notebooks in default_exp_groups.items():
        if len(notebooks) > 1:
            merges[module_name] = notebooks
    
    return merges


def detect_cross_module_exports(notebooks_dir: Path) -> dict:
    """
    Detect cross-module exports from notebooks.
    
    In nbdev, #| exporti <module> exports to a specific module.
    These notebooks don't have #| default_exp, so they need special handling.
    
    Returns dict mapping target_module to list of (notebook_name, cells) tuples.
    """
    from collections import defaultdict
    
    cross_module_exports = defaultdict(list)
    
    for nb in sorted(notebooks_dir.glob("*.py")):
        if nb.name.startswith('_'):
            continue
        
        source = nb.read_text()
        parsed = parse_marimo_notebook(source)
        
        # Skip notebooks with #| default_exp (they are handled by detect_module_merges)
        if parsed['module_name']:
            continue
        
        # Collect cross-module exports
        for tag, code, target_module in parsed['cells']:
            if tag in ('export', 'exporti') and target_module:
                cross_module_exports[target_module].append((nb.name, tag, code))
    
    return cross_module_exports


def dedent_code(code: str) -> str:
    """
    Remove common indentation from code.
    
    The code inside @app.cell functions is indented because it's inside
    a function body. This function removes that indentation.
    """
    lines = code.split('\n')
    min_indent = None
    
    for line in lines:
        if line.strip():
            indent = len(line) - len(line.lstrip())
            if min_indent is None or indent < min_indent:
                min_indent = indent
    
    if min_indent is None or min_indent == 0:
        return code
    
    dedented = []
    for line in lines:
        if line.strip():
            dedented.append(line[min_indent:])
        else:
            dedented.append('')
    
    return '\n'.join(dedented)


def strip_cell_wrapper_return(code: str) -> str:
    """
    Strip the marimo cell wrapper 'return' statement at the end of cell code.
    
    In marimo notebooks, each cell function ends with:
        return (var1, var2, ...)
    
    This is just marimo's dependency tracking and should not be in the output.
    The wrapper return is identified by:
    1. Being the last non-empty line(s) in the code
    2. Being at the minimum indent level (top-level of the cell body)
    """
    lines = code.split('\n')
    
    last_idx = len(lines) - 1
    while last_idx >= 0 and not lines[last_idx].strip():
        last_idx -= 1
    
    if last_idx < 0:
        return code
    
    last_stripped = lines[last_idx].strip()
    
    # Check if this is a return statement or a closing paren of a return
    is_return = last_stripped.startswith('return')
    is_closing_paren = last_stripped == ')'
    
    if not is_return and not is_closing_paren:
        return code
    
    # Find the start of the return statement
    # If last line is ')', search backwards for 'return'
    if is_closing_paren:
        return_start = last_idx
        while return_start >= 0:
            if lines[return_start].strip().startswith('return'):
                break
            return_start -= 1
        if return_start < 0:
            return code
    else:
        return_start = last_idx
    
    # Check indentation - return should be at minimum indent level
    min_indent = None
    for line in lines:
        if line.strip():
            indent = len(line) - len(line.lstrip())
            if min_indent is None or indent < min_indent:
                min_indent = indent
    
    if min_indent is None:
        min_indent = 0
    
    return_indent = len(lines[return_start]) - len(lines[return_start].lstrip())
    
    if return_indent > min_indent:
        return code
    
    # Check parentheses balance from return statement to end
    paren_depth = 0
    for line in lines[return_start:]:
        for ch in line:
            if ch == '(':
                paren_depth += 1
            elif ch == ')':
                paren_depth -= 1
    
    if paren_depth == 0:
        return '\n'.join(lines[:return_start]).rstrip()
    
    return code
    
    start_idx = last_idx
    while start_idx >= 0 and paren_depth > 0:
        start_idx -= 1
        if start_idx < 0:
            break
        for ch in lines[start_idx]:
            if ch == '(':
                paren_depth -= 1
            elif ch == ')':
                paren_depth += 1
    
    if paren_depth == 0 and start_idx >= 0:
        all_wrapper = True
        for idx in range(start_idx, last_idx + 1):
            if lines[idx].strip():
                indent = len(lines[idx]) - len(lines[idx].strip())
                if indent > min_indent:
                    all_wrapper = False
                    break
        
        if all_wrapper:
            return '\n'.join(lines[:start_idx]).rstrip()
    
    return code


def parse_marimo_notebook(source: str) -> dict:
    """
    Parse a marimo notebook and extract cells with their tags.
    
    Each cell is a function decorated with @app.cell:
        @app.cell
        def _(param1, param2):
            #| export
            code...
            return (result1, result2)
    
    Returns dict with:
        - 'module_name': from #| default_exp
        - 'cells': list of (tag, code, target_module) tuples
    """
    lines = source.split('\n')
    cells = []
    module_name = None
    
    # Find module name from #| default_exp
    for line in lines:
        stripped = line.strip()
        if stripped.startswith('#| default_exp'):
            parts = stripped.split()
            if len(parts) >= 3:
                module_name = parts[2]
                break
    
    # Find all @app.cell positions
    cell_starts = []
    for i, line in enumerate(lines):
        if line.strip().startswith('@app.cell'):
            cell_starts.append(i)
    
    # Also find end-of-file boilerplate
    file_end = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        if stripped.startswith('if __name__') or stripped.startswith('app.run'):
            file_end = i
        elif stripped and not stripped.startswith('#'):
            break
    
    # Process each cell
    for ci, start in enumerate(cell_starts):
        # End of this cell = start of next cell (or end of file)
        end = cell_starts[ci + 1] if ci + 1 < len(cell_starts) else file_end
        
        # Find the function body start (after def line and parameter list)
        body_start = start + 1
        if body_start >= end:
            continue
        
        # Skip the 'def ...' line(s) — find the colon at paren_depth 0
        paren_depth = 0
        found_colon = False
        while body_start < end and not found_colon:
            for ch in lines[body_start]:
                if ch == '(':
                    paren_depth += 1
                elif ch == ')':
                    paren_depth -= 1
                elif ch == ':' and paren_depth == 0:
                    found_colon = True
                    break
            if not found_colon:
                body_start += 1
        
        if not found_colon:
            continue
        
        body_start += 1  # Move past the colon line
        
        if body_start >= end:
            continue
        
        # Extract cell body lines (between def body and end of cell)
        # Exclude the trailing 'return ...' line(s)
        cell_body_lines = []
        tag = None
        target_module = None
        
        for li in range(body_start, end):
            line = lines[li]
            stripped = line.strip()
            
            # Check for #| tags
            if stripped.startswith('#|'):
                tag_text = stripped[2:].strip()
                # Handle #| export module_name
                if tag_text.startswith('export '):
                    tag = 'export'
                    target_module = tag_text.split()[1]
                elif tag_text.startswith('exporti '):
                    tag = 'exporti'
                    target_module = tag_text.split()[1]
                elif tag_text in ('export', 'exporti', 'hide'):
                    tag = tag_text
                continue
            
            cell_body_lines.append(line)
        
        # Join and dedent
        code = '\n'.join(cell_body_lines)
        code = dedent_code(code)
        
        # Strip the marimo cell wrapper return at the end
        code = strip_cell_wrapper_return(code)
        
        # Remove leading/trailing empty lines
        code = code.strip()
        
        if code:
            cells.append((tag, code, target_module))
    
    return {'module_name': module_name, 'cells': cells}


def extract_exported_names(cells: list) -> list:
    """
    Extract names that should be exported from #| export cells.
    
    Follows nbdev semantics:
    - Functions/classes decorated with @patch are NOT included in __all__
    - Only functions/classes without @patch are included
    - Variable assignments are NOT included in __all__
    - Imports are NOT included in __all__
    - Names starting with _ are NOT included in __all__
    
    Returns list of (name, type) tuples where type is 'function' or 'class'.
    Only includes names from #| export cells, not #| exporti cells.
    """
    names = []
    
    for tag, code, target_module in cells:
        # Only include #| export cells, not #| exporti
        if tag != 'export':
            continue
        
        try:
            tree = ast.parse(code)
        except SyntaxError:
            continue
        
        for node in ast.iter_child_nodes(tree):
            # Check if decorated with @patch
            is_patch_decorated = False
            if hasattr(node, 'decorator_list'):
                for dec in node.decorator_list:
                    if hasattr(dec, 'id') and dec.id == 'patch':
                        is_patch_decorated = True
                    elif hasattr(dec, 'func') and hasattr(dec.func, 'id') and dec.func.id == 'patch':
                        is_patch_decorated = True
            
            # Skip @patch decorated functions/classes
            if is_patch_decorated:
                continue
            
            # Skip names starting with _
            if hasattr(node, 'name') and node.name.startswith('_'):
                continue
            
            if isinstance(node, ast.FunctionDef):
                names.append((node.name, 'function'))
            elif isinstance(node, ast.AsyncFunctionDef):
                names.append((node.name, 'function'))
            elif isinstance(node, ast.ClassDef):
                names.append((node.name, 'class'))
            # Skip Assign, Import, ImportFrom - not included in __all__
    
    return names


def collect_and_strip_imports(cells: list) -> Tuple[str, List[Tuple[str, str, str]]]:
    """
    Collect import statements from #| export and #| exporti cells.
    
    Returns (imports_code, remaining_cells) where imports_code is the
    collected imports (deduplicated, sorted) and remaining_cells has imports removed.
    
    Handles wildcard imports by converting them to TODO comments.
    """
    import_lines = set()
    remaining_cells = []
    
    for tag, code, target_module in cells:
        if tag not in ('export', 'exporti'):
            remaining_cells.append((tag, code, target_module))
            continue
        
        lines = code.split('\n')
        cell_import_lines = []
        other_lines = []
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith(('import ', 'from ')) and not line.startswith(' '):
                # Handle wildcard imports
                if ' import *' in stripped:
                    # Convert wildcard to TODO comment
                    module = stripped.split('from ')[1].split(' import')[0].strip()
                    other_lines.append(f"# TODO: Expand wildcard import: {stripped}")
                    other_lines.append(f"# Replace with explicit imports from {module}.__all__")
                else:
                    import_lines.add(line.rstrip())
            else:
                other_lines.append(line)
        
        other_code = '\n'.join(other_lines).strip()
        if other_code:
            remaining_cells.append((tag, other_code, target_module))
    
    # Sort imports: stdlib first, then third-party, then local (nbdev-style)
    def import_sort_key(imp: str) -> tuple:
        imp_lower = imp.lower()
        # stdlib (no dots, common stdlib modules)
        stdlib_modules = {'os', 'sys', 'pathlib', 'tempfile', 'traceback', 'ast', 'itertools', 
                         'collections', 'functools', 'math', 'random', 'json', 'csv', 're',
                         'typing', 'dataclasses', 'enum', 'abc', 'copy', 'hashlib', 'uuid',
                         'datetime', 'time', 'argparse', 'subprocess', 'shutil', 'glob',
                         'textwrap', 'pprint', 'inspect', 'importlib', 'pkgutil', 'warnings',
                         'contextlib', 'asyncio', 'concurrent', 'threading', 'multiprocessing',
                         'socket', 'ssl', 'urllib', 'http', 'email', 'html', 'xml', 'sqlite3',
                         'csv', 'pickle', 'shelve', 'marshal', 'types', 'weakref', 'gc',
                         'atexit', 'signal', 'locale', 'gettext', 'logging', 'unittest',
                         'doctest', 'optparse', 'getopt', 'string', 'fractions', 'decimal',
                         'numbers', 'itertools', 'functools', 'operator', 'statistics'}
        first_word = imp.split()[0] if imp else ''
        second_word = imp.split()[1] if len(imp.split()) > 1 else ''
        
        if second_word in stdlib_modules or (first_word == 'import' and second_word in stdlib_modules):
            return (0, imp)
        elif first_word == 'from' and '.' not in second_word and second_word in stdlib_modules:
            return (0, imp)
        elif first_word == 'import':
            # Third-party
            return (1, imp)
        elif first_word == 'from':
            # Could be third-party or local
            if '.' in second_word:
                return (2, imp)  # Local (has dots)
            return (1, imp)  # Third-party
        return (3, imp)
    
    sorted_imports = sorted(import_lines, key=import_sort_key)
    imports_code = '\n'.join(sorted_imports)
    return imports_code, remaining_cells


def clean_mo_md(code: str) -> str:
    """Remove mo.md() calls from code."""
    lines = code.split('\n')
    cleaned = []
    skip_until_close = False
    paren_depth = 0
    
    for line in lines:
        stripped = line.strip()
        
        if stripped.startswith('mo.md('):
            skip_until_close = True
            paren_depth = 0
            for ch in stripped:
                if ch == '(':
                    paren_depth += 1
                elif ch == ')':
                    paren_depth -= 1
            if paren_depth == 0:
                skip_until_close = False
            continue
        
        if skip_until_close:
            for ch in stripped:
                if ch == '(':
                    paren_depth += 1
                elif ch == ')':
                    paren_depth -= 1
            if paren_depth == 0:
                skip_until_close = False
            continue
        
        cleaned.append(line)
    
    return '\n'.join(cleaned)


def generate_module(source: str) -> Optional[str]:
    """
    Generate a Python module from a marimo notebook.
    
    Uses #| tags as the source of information:
    - #| default_exp <module> → output module name
    - #| export → include cell in output and __all__
    - #| exporti → include cell in output but NOT in __all__
    - #| hide → exclude cell from output
    
    Returns the generated module code, or None if no module name found.
    """
    parsed = parse_marimo_notebook(source)
    module_name = parsed['module_name']
    cells = parsed['cells']
    
    if not module_name:
        return None
    
    # Filter cells for this module (include both export and exporti)
    export_cells = []
    for tag, code, target_module in cells:
        if tag in ('export', 'exporti'):
            # Include if no target_module or if target_module matches
            if target_module is None or target_module == module_name:
                export_cells.append((tag, code, target_module))
    
    if not export_cells:
        return None
    
    # Clean mo.md() calls
    export_cells = [(tag, clean_mo_md(code), target_module) for tag, code, target_module in export_cells]
    
    # Strip marimo cell wrapper returns
    export_cells = [(tag, strip_cell_wrapper_return(code), target_module) for tag, code, target_module in export_cells]
    
    # Remove empty cells after cleaning
    export_cells = [(tag, code, target_module) for tag, code, target_module in export_cells if code.strip()]
    
    if not export_cells:
        return None
    
    # Collect imports to top (from both export and exporti cells)
    imports_code, remaining_cells = collect_and_strip_imports(export_cells)
    
    # Extract exported names for __all__ (only from #| export cells, not #| exporti)
    exported_names = extract_exported_names(cells)
    
    # Filter out imports from __all__
    all_names = [name for name, typ in exported_names if typ != 'import']
    
    # Build module
    lines = []
    
    # Add module docstring (empty for now)
    lines.append('"""Module docstring"""')
    lines.append('')
    
    # Add AUTOGENERATED comment
    lines.append('# AUTOGENERATED! DO NOT EDIT!')
    lines.append('')
    
    # Add __all__ (always generate, even if empty)
    all_str = ', '.join(f"'{name}'" for name in all_names)
    lines.append(f'__all__ = [{all_str}]')
    lines.append('')
    
    # Add collected imports
    if imports_code:
        lines.append(imports_code)
        lines.append('')
    
    # Add remaining cells
    for tag, code, target_module in remaining_cells:
        if code.strip():
            lines.append(code)
            lines.append('')
    
    return '\n'.join(lines)


def convert_notebook(notebook_path: Path, output_dir: Path) -> Optional[Path]:
    """
    Convert a single marimo notebook to a Python module.
    
    Returns the output path, or None if conversion failed.
    """
    source = notebook_path.read_text()
    module_code = generate_module(source)
    
    if module_code is None:
        return None
    
    parsed = parse_marimo_notebook(source)
    module_name = parsed['module_name']
    output_path = output_dir / f"{module_name}.py"
    
    output_path.write_text(module_code)
    return output_path


def convert_merged_module(module_name: str, notebook_names: list, output_dir: Path) -> Optional[Path]:
    """
    Convert multiple notebooks and merge them into a single module.
    
    Returns the output path, or None if conversion failed.
    """
    all_cells = []
    
    for nb_name in notebook_names:
        nb_path = NOTEBOOKS_DIR / nb_name
        if not nb_path.exists():
            print(f"  Warning: {nb_name} not found, skipping")
            continue
        
        source = nb_path.read_text()
        parsed = parse_marimo_notebook(source)
        
        # Collect cells from this notebook that target this module
        # Include both #| export and #| exporti cells
        for tag, code, target_module in parsed['cells']:
            if tag in ('export', 'exporti'):
                # Include if no target_module or if target_module matches
                if target_module is None or target_module == module_name:
                    all_cells.append((tag, code, target_module))
    
    if not all_cells:
        return None
    
    # Clean mo.md() calls
    all_cells = [(tag, clean_mo_md(code), target_module) for tag, code, target_module in all_cells]
    
    # Strip marimo cell wrapper returns
    all_cells = [(tag, strip_cell_wrapper_return(code), target_module) for tag, code, target_module in all_cells]
    
    # Remove empty cells after cleaning
    all_cells = [(tag, code, target_module) for tag, code, target_module in all_cells if code.strip()]
    
    if not all_cells:
        return None
    
    # Collect and strip imports (deduplicated, sorted, wildcard handled)
    imports_code, all_cells = collect_and_strip_imports(all_cells)
    
    if not all_cells:
        return None
    
    # Clean mo.md() calls
    all_cells = [(tag, clean_mo_md(code), target_module) for tag, code, target_module in all_cells]
    
    # Strip marimo cell wrapper returns
    all_cells = [(tag, strip_cell_wrapper_return(code), target_module) for tag, code, target_module in all_cells]
    
    # Remove empty cells after cleaning
    all_cells = [(tag, code, target_module) for tag, code, target_module in all_cells if code.strip()]
    
    if not all_cells:
        return None
    
    # Extract exported names for __all__
    exported_names = []
    for _, code, _ in all_cells:
        try:
            tree = ast.parse(code)
            for node in ast.iter_child_nodes(tree):
                if isinstance(node, ast.FunctionDef):
                    exported_names.append((node.name, 'function'))
                elif isinstance(node, ast.AsyncFunctionDef):
                    exported_names.append((node.name, 'function'))
                elif isinstance(node, ast.ClassDef):
                    exported_names.append((node.name, 'class'))
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            exported_names.append((target.id, 'variable'))
        except SyntaxError:
            pass
    
    # Filter out imports from __all__
    all_names = [name for name, typ in exported_names if typ != 'import']
    
    # Build module
    lines = []
    
    # Add module docstring (empty for now)
    lines.append('"""Module docstring"""')
    lines.append('')
    
    # Add AUTOGENERATED comment
    lines.append('# AUTOGENERATED! DO NOT EDIT!')
    lines.append('')
    
    # Build module
    lines = []
    
    # Add module docstring (empty for now)
    lines.append('"""Module docstring"""')
    lines.append('')
    
    # Add AUTOGENERATED comment
    lines.append('# AUTOGENERATED! DO NOT EDIT!')
    lines.append('')
    
    # Add __all__ (always generate, even if empty)
    all_str = ', '.join(f"'{name}'" for name in all_names)
    lines.append(f'__all__ = [{all_str}]')
    lines.append('')
    
    # Add collected imports
    if imports_code:
        lines.append(imports_code)
        lines.append('')
    
    # Add remaining cells
    for tag, code, target_module in all_cells:
        if code.strip():
            lines.append(code)
            lines.append('')
    
    module_code = '\n'.join(lines)
    output_path = output_dir / f"{module_name}.py"
    
    output_path.write_text(module_code)
    return output_path


def apply_cross_module_exports(output_dir: Path, cross_module_exports: dict) -> None:
    """
    Apply cross-module exports to existing modules.
    
    When a notebook has #| exporti <module> cells, those cells should be
    merged into the target module. This function applies those exports
    to existing modules, properly handling imports (deduplication, sorting).
    """
    for target_module, exports in cross_module_exports.items():
        output_path = output_dir / f"{target_module}.py"
        if not output_path.exists():
            print(f"  Warning: Target module {target_module}.py not found, skipping cross-module exports")
            continue
        
        # Read existing module
        existing_code = output_path.read_text()
        lines = existing_code.split('\n')
        original_lines = lines  # Save for later use
        
        # 1. Extract existing imports
        existing_imports = set()
        insert_idx = 0
        import_start = 0
        in_docstring = False
        import_started = False
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                quote = '"""' if stripped.startswith('"""') else "'''"
                if stripped.count(quote) >= 2:
                    continue
                else:
                    in_docstring = not in_docstring
                    continue
            if in_docstring:
                continue
            if stripped.startswith(('import ', 'from ')) and not line.startswith(' '):
                if not import_started:
                    import_started = True
                    import_start = i
                if ' import *' in stripped:
                    module = stripped.split('from ')[1].split(' import')[0].strip()
                    existing_imports.add(f"# TODO: Expand wildcard import: {stripped}")
                    existing_imports.add(f"# Replace with explicit imports from {module}.__all__")
                else:
                    existing_imports.add(stripped)
            elif stripped == '' or stripped.startswith('#') or stripped.startswith('__all__'):
                continue
            elif stripped:
                insert_idx = i
                break
        
        # If no non-import code found, import ends at end of file
        if insert_idx == 0:
            insert_idx = len(lines)
        
        # 2. Collect imports from cross-module exports
        new_cells = []
        for nb_name, tag, code in exports:
            # Clean the code
            code = clean_mo_md(code)
            code = strip_cell_wrapper_return(code)
            if not code.strip():
                continue
            
            # Extract imports from this export cell
            for line in code.split('\n'):
                stripped = line.strip()
                if stripped.startswith(('import ', 'from ')) and not line.startswith(' '):
                    if ' import *' in stripped:
                        module = stripped.split('from ')[1].split(' import')[0].strip()
                        existing_imports.add(f"# TODO: Expand wildcard import: {stripped}")
                        existing_imports.add(f"# Replace with explicit imports from {module}.__all__")
                    else:
                        existing_imports.add(stripped)
            
            # Remove imports from the cell code
            cell_lines = code.split('\n')
            non_import = [l for l in cell_lines 
                         if not (l.strip().startswith(('import ', 'from ')) and not l.startswith(' '))]
            if non_import:
                new_cells.append('\n'.join(non_import))
        
        if not new_cells and not existing_imports:
            continue
        
        # Sort imports nbdev-style
        def import_sort_key(imp: str) -> tuple:
            stdlib_modules = {'os', 'sys', 'pathlib', 'tempfile', 'traceback', 'ast', 'itertools', 
                             'collections', 'functools', 'math', 'random', 'json', 'csv', 're',
                             'typing', 'dataclasses', 'enum', 'abc', 'copy', 'hashlib', 'uuid',
                             'datetime', 'time', 'argparse', 'subprocess', 'shutil', 'glob',
                             'textwrap', 'pprint', 'inspect', 'importlib', 'pkgutil', 'warnings',
                             'contextlib', 'asyncio', 'concurrent', 'threading', 'multiprocessing',
                             'socket', 'ssl', 'urllib', 'http', 'email', 'html', 'xml', 'sqlite3',
                             'csv', 'pickle', 'shelve', 'marshal', 'types', 'weakref', 'gc',
                             'atexit', 'signal', 'locale', 'gettext', 'logging', 'unittest',
                             'doctest', 'optparse', 'getopt', 'string', 'fractions', 'decimal',
                             'numbers', 'itertools', 'functools', 'operator', 'statistics'}
            second_word = imp.split()[1] if len(imp.split()) > 1 else ''
            first_word = imp.split()[0] if imp else ''
            
            if second_word in stdlib_modules or (first_word == 'import' and second_word in stdlib_modules):
                return (0, imp)
            elif first_word == 'from' and '.' not in second_word and second_word in stdlib_modules:
                return (0, imp)
            elif first_word == 'import':
                return (1, imp)
            elif first_word == 'from':
                if '.' in second_word:
                    return (2, imp)
                return (1, imp)
            return (3, imp)
        
        if not new_cells and not existing_imports:
            continue
        
        # Find import_start (first import line) for proper merging
        import_start = 0
        in_docstring = False
        for i, line in enumerate(original_lines):
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''"):
                quote = '"""' if stripped.startswith('"""') else "'''"
                if stripped.count(quote) >= 2:
                    continue
                else:
                    in_docstring = not in_docstring
                    continue
            if in_docstring:
                continue
            if stripped.startswith(('import ', 'from ')) and not line.startswith(' '):
                import_start = i
                break
            elif stripped == '' or stripped.startswith('#') or stripped.startswith('__all__'):
                continue
            elif stripped:
                break
        
        # Sort imports nbdev-style
        def import_sort_key(imp: str) -> tuple:
            stdlib_modules = {'os', 'sys', 'pathlib', 'tempfile', 'traceback', 'ast', 'itertools', 
                             'collections', 'functools', 'math', 'random', 'json', 'csv', 're',
                             'typing', 'dataclasses', 'enum', 'abc', 'copy', 'hashlib', 'uuid',
                             'datetime', 'time', 'argparse', 'subprocess', 'shutil', 'glob',
                             'textwrap', 'pprint', 'inspect', 'importlib', 'pkgutil', 'warnings',
                             'contextlib', 'asyncio', 'concurrent', 'threading', 'multiprocessing',
                             'socket', 'ssl', 'urllib', 'http', 'email', 'html', 'xml', 'sqlite3',
                             'csv', 'pickle', 'shelve', 'marshal', 'types', 'weakref', 'gc',
                             'atexit', 'signal', 'locale', 'gettext', 'logging', 'unittest',
                             'doctest', 'optparse', 'getopt', 'string', 'fractions', 'decimal',
                             'numbers', 'itertools', 'functools', 'operator', 'statistics'}
            second_word = imp.split()[1] if len(imp.split()) > 1 else ''
            first_word = imp.split()[0] if imp else ''
            
            if second_word in stdlib_modules or (first_word == 'import' and second_word in stdlib_modules):
                return (0, imp)
            elif first_word == 'from' and '.' not in second_word and second_word in stdlib_modules:
                return (0, imp)
            elif first_word == 'import':
                return (1, imp)
            elif first_word == 'from':
                if '.' in second_word:
                    return (2, imp)
                return (1, imp)
            return (3, imp)
        
        # Build new lines: imports + new cells + rest
        new_imports = '\n'.join(sorted(existing_imports, key=import_sort_key))
        new_lines = []
        if new_imports:
            new_lines = new_imports.split('\n') + ['']
        
        for cell in new_cells:
            new_lines.extend(cell.split('\n'))
            new_lines.append('')
        
        # Merge: pre-imports + merged imports + post-imports
        pre_imports = original_lines[:import_start]
        post_imports = original_lines[insert_idx:]
        lines = pre_imports + new_lines + post_imports
        
        # Write back
        output_path.write_text('\n'.join(lines))
        print(f"  Applied cross-module exports to {target_module}.py from {', '.join(set(nb for nb, _, _ in exports))}")


def main():
    """Convert all notebooks or a single specified notebook."""
    output_dir = OUTPUT_DIR
    output_dir.mkdir(exist_ok=True)
    
    if len(sys.argv) > 1:
        notebook_path = Path(sys.argv[1])
        if not notebook_path.exists():
            notebook_path = NOTEBOOKS_DIR / sys.argv[1]
        if not notebook_path.exists():
            print(f"Error: Notebook not found: {sys.argv[1]}")
            sys.exit(1)
        
        result = convert_notebook(notebook_path, output_dir)
        if result:
            print(f"Converted: {notebook_path.name} -> {result}")
        else:
            print(f"Failed to convert: {notebook_path.name}")
    else:
        # Detect module merges automatically based on #| default_exp
        auto_merges = detect_module_merges(NOTEBOOKS_DIR)
        
        converted = 0
        failed = 0
        
        # Track which notebooks are part of merged modules
        merged_notebooks = set()
        for module_name, notebook_names in auto_merges.items():
            for nb_name in notebook_names:
                merged_notebooks.add(nb_name)
        
        # First, convert merged modules
        for module_name, notebook_names in auto_merges.items():
            result = convert_merged_module(module_name, notebook_names, output_dir)
            if result:
                print(f"Merged: {', '.join(notebook_names)} -> {result.name}")
                converted += 1
            else:
                print(f"Failed to merge: {module_name}")
                failed += 1
        
        # Then, convert individual notebooks (only canonical modules)
        for nb_path in sorted(NOTEBOOKS_DIR.glob("*.py")):
            if nb_path.name.startswith('_'):
                continue
            
            # Skip notebooks that are part of merged modules
            if nb_path.name in merged_notebooks:
                continue
            
            result = convert_notebook(nb_path, output_dir)
            if result:
                print(f"Converted: {nb_path.name} -> {result.name}")
                converted += 1
            else:
                print(f"Skipped: {nb_path.name} (no #| default_exp)")
                failed += 1
        
        # Finally, apply cross-module exports
        cross_module_exports = detect_cross_module_exports(NOTEBOOKS_DIR)
        if cross_module_exports:
            print("\nApplying cross-module exports:")
            apply_cross_module_exports(output_dir, cross_module_exports)
        
        print(f"\nConverted: {converted}, Skipped: {failed}")


if __name__ == '__main__':
    main()
