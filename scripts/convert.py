#!/usr/bin/env python3
"""
Generic tag-based conversion from marimo notebooks to Python modules.

Uses #| tags (default_exp, export, exporti, hide) as the source of information.
No hardcoded exceptions - the pipeline is generic and tag-driven.

The input is a marimo notebook (Python file with @app.cell decorators).
The output is a clean Python module with:
- #| export cells included and in __all__
- #| exporti cells included but NOT in __all__
- #| exporti <module> cells merged into cross-module targets
- #| hide cells excluded
- mo.md() calls removed
- Imports collected at top, deduplicated and sorted
- __all__ list generated from exported names

Usage:
    python scripts/convert.py                    # Convert all notebooks
    python scripts/convert.py notebooks/11_core.py  # Convert single notebook
"""

import re
import sys
import ast
from pathlib import Path
from typing import Optional, Tuple

PROJECT_ROOT = Path(__file__).parent.parent
NOTEBOOKS_DIR = PROJECT_ROOT / "notebooks"
OUTPUT_DIR = PROJECT_ROOT / "hecss"

# Cell tuple format: (tag, target_module, code)
#   tag:           'export' | 'exporti' | 'hide' | None
#   target_module: module name (for cross-module exporti) or None
#   code:          dedented, wrapper-stripped, trimmed source


# ---------------------------------------------------------------------------
# Module-level import sort key
# ---------------------------------------------------------------------------

def _import_sort_key(imp: str) -> tuple:
    """Sort key for imports: stdlib first, third-party second, local third."""
    first_word = imp.split()[0] if imp else ''
    second_word = imp.split()[1] if len(imp.split()) > 1 else ''

    if second_word in sys.stdlib_module_names:
        return (0, imp)
    elif first_word == 'from' and '.' not in second_word and second_word in sys.stdlib_module_names:
        return (0, imp)
    elif first_word == 'import':
        return (1, imp)
    elif first_word == 'from':
        if '.' in second_word:
            return (2, imp)
        return (1, imp)
    return (3, imp)


# ---------------------------------------------------------------------------
# detect_module_merges
# ---------------------------------------------------------------------------

def detect_module_merges(notebooks_dir: Path) -> dict:
    """
    Detect which notebooks should be merged based on #| default_exp tags.
    Multiple notebooks exporting to the same module are merged.
    Returns dict mapping module_name to list of notebook file names.
    """
    from collections import defaultdict

    groups = defaultdict(list)
    for nb in sorted(notebooks_dir.glob("*.py")):
        if nb.name.startswith('_'):
            continue
        source = nb.read_text()
        match = re.search(r'#\|\s*default_exp\s+(\S+)', source)
        if match:
            groups[match.group(1)].append(nb.name)

    return {m: nbs for m, nbs in groups.items() if len(nbs) > 1}


# ---------------------------------------------------------------------------
# detect_cross_module_exports
# ---------------------------------------------------------------------------

def detect_cross_module_exports(notebooks_dir: Path) -> dict:
    """
    Detect cross-module exports from ALL notebooks.
    Collects cells tagged #| exporti <module> (including from notebooks
    that also have #| default_exp).
    Returns dict mapping target_module to list of (nb_name, tag, code) tuples.
    """
    from collections import defaultdict

    result = defaultdict(list)

    for nb in sorted(notebooks_dir.glob("*.py")):
        if nb.name.startswith('_'):
            continue
        source = nb.read_text()
        parsed = parse_marimo_notebook(source)

        for tag, target_module, code in parsed['cells']:
            if tag in ('export', 'exporti') and target_module:
                result[target_module].append((nb.name, tag, code))

    return dict(result)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def dedent_code(code: str) -> str:
    """Remove common indentation from code."""
    lines = code.split('\n')
    min_indent = None
    for line in lines:
        if line.strip():
            indent = len(line) - len(line.lstrip())
            if min_indent is None or indent < min_indent:
                min_indent = indent
    if min_indent is None or min_indent == 0:
        return code
    # preserve whitespace-only lines verbatim (nbdev-style fidelity)
    return '\n'.join(line[min_indent:] if line.strip() else line for line in lines)


def strip_cell_wrapper_return(code: str) -> str:
    """Strip the marimo cell wrapper 'return (var1, var2, ...)' at end of cell."""
    lines = code.split('\n')

    last_idx = len(lines) - 1
    while last_idx >= 0 and not lines[last_idx].strip():
        last_idx -= 1
    if last_idx < 0:
        return code

    last_stripped = lines[last_idx].strip()
    is_return = last_stripped.startswith('return')
    is_closing_paren = last_stripped == ')'

    if not is_return and not is_closing_paren:
        return code

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

    paren_depth = 0
    for line in lines[return_start:]:
        for ch in line:
            if ch == '(':
                paren_depth += 1
            elif ch == ')':
                paren_depth -= 1

    if paren_depth == 0:
        return '\n'.join(lines[:return_start]).rstrip('\n')

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
            return '\n'.join(lines[:start_idx]).rstrip('\n')

    return code


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


# ---------------------------------------------------------------------------
# parse_marimo_notebook
# ---------------------------------------------------------------------------

def parse_marimo_notebook(source: str) -> dict:
    """
    Parse a marimo notebook and extract cells with their tags.

    Returns dict with:
        - 'module_name': from #| default_exp (or None)
        - 'cells': list of (tag, target_module, code) tuples
    """
    lines = source.split('\n')
    cells = []
    module_name = None

    for line in lines:
        stripped = line.strip()
        match = re.match(r'#\|\s*default_exp\s+(\S+)', stripped)
        if match:
            module_name = match.group(1)
            break

    cell_starts = []
    for i, line in enumerate(lines):
        if line.strip().startswith('@app.cell'):
            cell_starts.append(i)

    file_end = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        stripped = lines[i].strip()
        if stripped.startswith('if __name__') or stripped.startswith('app.run'):
            file_end = i
        elif stripped and not stripped.startswith('#'):
            break

    for ci, start in enumerate(cell_starts):
        end = cell_starts[ci + 1] if ci + 1 < len(cell_starts) else file_end

        body_start = start + 1
        if body_start >= end:
            continue

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
        body_start += 1
        if body_start >= end:
            continue

        cell_body_lines = []
        tag = None
        target_module = None

        for li in range(body_start, end):
            line = lines[li]
            stripped = line.strip()

            if stripped.startswith('#|'):
                tag_text = stripped[2:].strip()
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

        code = '\n'.join(cell_body_lines)
        code = dedent_code(code)
        code = strip_cell_wrapper_return(code)
        # trim surrounding blank lines only; preserve trailing whitespace
        # on the final content line (nbdev fidelity)
        code = code.strip('\n')

        if code:
            cells.append((tag, target_module, code))

    return {'module_name': module_name, 'cells': cells}


# ---------------------------------------------------------------------------
# extract_exported_names
# ---------------------------------------------------------------------------

def extract_exported_names(cells: list, target_module: str = None) -> list:
    """
    Extract names for __all__ from cells.

    Rules (nbdev semantics):
    - Only #| export cells (not #| exporti)
    - @patch decorated functions/classes excluded
    - Names starting with _ excluded
    - Variable assignments and imports excluded

    When target_module is given, only include cells matching that module.

    Returns list of (name, type) tuples.
    """
    names = []
    for tag, cell_target, code in cells:
        if tag != 'export':
            continue
        if target_module is not None and cell_target is not None and cell_target != target_module:
            continue

        try:
            tree = ast.parse(code)
        except SyntaxError:
            continue

        for node in ast.iter_child_nodes(tree):
            is_patch = False
            if hasattr(node, 'decorator_list'):
                for dec in node.decorator_list:
                    if hasattr(dec, 'id') and dec.id == 'patch':
                        is_patch = True
                    elif hasattr(dec, 'func') and hasattr(dec.func, 'id') and dec.func.id == 'patch':
                        is_patch = True
            if is_patch:
                continue
            if hasattr(node, 'name') and node.name.startswith('_'):
                continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                names.append((node.name, 'function'))
            elif isinstance(node, ast.ClassDef):
                names.append((node.name, 'class'))
    return names


# ---------------------------------------------------------------------------
# collect_and_strip_imports
# ---------------------------------------------------------------------------

def collect_and_strip_imports(cells: list) -> Tuple[str, list]:
    """
    Collect import statements from cells, deduplicate and sort them.

    Returns (imports_code, remaining_cells) where remaining_cells have
    imports stripped. Wildcard imports become TODO comments.
    """
    import_lines = set()
    remaining_cells = []

    for tag, target_module, code in cells:
        if tag not in ('export', 'exporti'):
            remaining_cells.append((tag, target_module, code))
            continue

        lines = code.split('\n')
        other_lines = []

        for line in lines:
            stripped = line.strip()
            if stripped.startswith(('import ', 'from ')) and not line.startswith(' '):
                if ' import *' in stripped:
                    module = stripped.split('from ')[1].split(' import')[0].strip()
                    other_lines.append(f"# TODO: Expand wildcard import: {stripped}")
                    other_lines.append(f"# Replace with explicit imports from {module}.__all__")
                else:
                    import_lines.add(line.rstrip())
            else:
                other_lines.append(line)

        other_code = '\n'.join(other_lines).strip('\n')
        if other_code:
            remaining_cells.append((tag, target_module, other_code))

    sorted_imports = sorted(import_lines, key=_import_sort_key)
    return '\n'.join(sorted_imports), remaining_cells


# ---------------------------------------------------------------------------
# _build_module_body
# ---------------------------------------------------------------------------

def _build_module_body(all_names: list, imports_code: str,
                       cells: list) -> str:
    """Build a complete module from extracted names, imports and cell code."""
    lines = []

    lines.append('"""Module docstring"""')
    lines.append('')
    lines.append('# AUTOGENERATED! DO NOT EDIT!')
    lines.append('')

    all_str = ', '.join(f"'{name}'" for name in all_names)
    lines.append(f'__all__ = [{all_str}]')
    lines.append('')

    if imports_code:
        lines.append(imports_code)
        lines.append('')

    for _tag, _target, code in cells:
        if code.strip():
            lines.append(code)
            lines.append('')

    return '\n'.join(lines)


# ---------------------------------------------------------------------------
# generate_module
# ---------------------------------------------------------------------------

def generate_module(source: str) -> Optional[str]:
    """
    Generate a Python module from a single marimo notebook.

    Returns the generated module code, or None if no module name found.
    """
    parsed = parse_marimo_notebook(source)
    module_name = parsed['module_name']
    cells = parsed['cells']

    if not module_name:
        return None

    # Filter: export/exporti cells targeting this module (or no target)
    export_cells = [
        (tag, tm, code) for tag, tm, code in cells
        if tag in ('export', 'exporti') and (tm is None or tm == module_name)
    ]

    if not export_cells:
        return None

    imports_code, remaining_cells = collect_and_strip_imports(export_cells)

    exported_names = extract_exported_names(cells, target_module=module_name)
    all_names = [name for name, typ in exported_names if typ != 'import']

    return _build_module_body(all_names, imports_code, remaining_cells)


# ---------------------------------------------------------------------------
# convert_notebook
# ---------------------------------------------------------------------------

def convert_notebook(notebook_path: Path, output_dir: Path) -> Optional[Path]:
    """Convert a single marimo notebook to a Python module."""
    source = notebook_path.read_text()
    module_code = generate_module(source)
    if module_code is None:
        return None

    parsed = parse_marimo_notebook(source)
    output_path = output_dir / f"{parsed['module_name']}.py"
    output_path.write_text(module_code)
    return output_path


# ---------------------------------------------------------------------------
# convert_merged_module
# ---------------------------------------------------------------------------

def convert_merged_module(module_name: str, notebook_names: list,
                          output_dir: Path) -> Optional[Path]:
    """Convert multiple notebooks and merge them into a single module."""
    all_cells = []

    for nb_name in notebook_names:
        nb_path = NOTEBOOKS_DIR / nb_name
        if not nb_path.exists():
            print(f"  Warning: {nb_name} not found, skipping")
            continue

        source = nb_path.read_text()
        parsed = parse_marimo_notebook(source)

        for tag, target_module, code in parsed['cells']:
            if tag in ('export', 'exporti'):
                if target_module is None or target_module == module_name:
                    all_cells.append((tag, target_module, code))

    if not all_cells:
        return None

    imports_code, all_cells = collect_and_strip_imports(all_cells)
    if not all_cells:
        return None

    exported_names = extract_exported_names(all_cells, target_module=module_name)
    all_names = [name for name, typ in exported_names if typ != 'import']

    module_code = _build_module_body(all_names, imports_code, all_cells)
    output_path = output_dir / f"{module_name}.py"
    output_path.write_text(module_code)
    return output_path


# ---------------------------------------------------------------------------
# apply_cross_module_exports
# ---------------------------------------------------------------------------

def _parse_imports_from_code(code: str) -> Tuple[set, list]:
    """Extract imports from code. Returns (import_set, non_import_lines)."""
    imports = set()
    non_import = []
    for line in code.split('\n'):
        stripped = line.strip()
        if stripped.startswith(('import ', 'from ')) and not line.startswith(' '):
            if ' import *' in stripped:
                module = stripped.split('from ')[1].split(' import')[0].strip()
                imports.add(f"# TODO: Expand wildcard import: {stripped}")
                imports.add(f"# Replace with explicit imports from {module}.__all__")
            else:
                imports.add(stripped)
        else:
            non_import.append(line)
    return imports, non_import


def apply_cross_module_exports(output_dir: Path, cross_module_exports: dict) -> None:
    """
    Apply cross-module exports to existing modules.

    Semantics: new imports are merged with existing imports (sorted into
    the right position). New cell code is appended at end of file
    (matching nbdev _make_exists append behavior).
    """
    for target_module, exports in cross_module_exports.items():
        output_path = output_dir / f"{target_module}.py"
        if not output_path.exists():
            print(f"  Warning: {target_module}.py not found, skipping cross-module exports")
            continue

        existing_code = output_path.read_text()
        original_lines = existing_code.split('\n')

        # --- Parse existing file structure ---
        existing_imports = set()
        first_import_idx = None
        first_code_idx = len(original_lines)
        in_docstring = False

        for i, line in enumerate(original_lines):
            stripped = line.strip()

            # Skip docstrings
            if stripped.startswith('"""') or stripped.startswith("'''"):
                quote = '"""' if stripped.startswith('"""') else "'''"
                if stripped.count(quote) >= 2:
                    continue
                in_docstring = not in_docstring
                continue
            if in_docstring:
                continue

            if stripped.startswith(('import ', 'from ')) and not line.startswith(' '):
                if first_import_idx is None:
                    first_import_idx = i
                imps, _ = _parse_imports_from_code(line)
                existing_imports |= imps
            elif stripped == '' or stripped.startswith('#') or stripped.startswith('__all__'):
                continue
            elif stripped and first_code_idx == len(original_lines):
                first_code_idx = i

        # --- Process cross-module export cells ---
        new_imports = set()
        new_code_cells = []

        for nb_name, tag, code in exports:
            code = clean_mo_md(code)
            code = strip_cell_wrapper_return(code)
            if not code.strip():
                continue

            imps, non_import_lines = _parse_imports_from_code(code)
            new_imports |= imps
            remaining = '\n'.join(non_import_lines).strip('\n')
            if remaining:
                new_code_cells.append(remaining)

        if not new_imports and not new_code_cells:
            continue

        # --- Merge imports at the right position ---
        all_imports = existing_imports | new_imports
        sorted_imports = sorted(all_imports, key=_import_sort_key)
        merged_import_lines = '\n'.join(sorted_imports).split('\n')

        # Build output: header (before import region) + merged imports (sole
        # copy) + code body + new cells appended at end
        header_end = first_import_idx if first_import_idx is not None else first_code_idx
        header = original_lines[:header_end]
        while header and not header[-1].strip():
            header.pop()

        body = original_lines[first_code_idx:]

        output_lines = header + [''] + merged_import_lines + [''] + body
        for cell in new_code_cells:
            output_lines.extend(cell.split('\n'))
            output_lines.append('')

        output_path.write_text('\n'.join(output_lines))
        print(f"  Applied cross-module exports to {target_module}.py from {', '.join(set(nb for nb, _, _ in exports))}")


# ---------------------------------------------------------------------------
# package __init__ generation
# ---------------------------------------------------------------------------

# Module whose namespace the package __init__ re-exports (package layout choice).
INIT_STAR_IMPORT = 'core'


def generate_init() -> str:
    """Generate package __init__.py content: version from pyproject.toml
    plus star-import of INIT_STAR_IMPORT."""
    version = '0.0.0'
    pyproject = PROJECT_ROOT / 'pyproject.toml'
    if pyproject.exists():
        m = re.search(r'^version\s*=\s*"([^"]+)"', pyproject.read_text(), re.M)
        if m:
            version = m.group(1)
    return f'__version__ = "{version}"\n\nfrom .{INIT_STAR_IMPORT} import *\n\n'


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

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
        auto_merges = detect_module_merges(NOTEBOOKS_DIR)

        converted = 0
        failed = 0

        merged_notebooks = set()
        for notebook_names in auto_merges.values():
            merged_notebooks.update(notebook_names)

        for module_name, notebook_names in auto_merges.items():
            result = convert_merged_module(module_name, notebook_names, output_dir)
            if result:
                print(f"Merged: {', '.join(notebook_names)} -> {result.name}")
                converted += 1
            else:
                print(f"Failed to merge: {module_name}")
                failed += 1

        for nb_path in sorted(NOTEBOOKS_DIR.glob("*.py")):
            if nb_path.name.startswith('_'):
                continue
            if nb_path.name in merged_notebooks:
                continue

            result = convert_notebook(nb_path, output_dir)
            if result:
                print(f"Converted: {nb_path.name} -> {result.name}")
                converted += 1
            else:
                print(f"Skipped: {nb_path.name} (no #| default_exp)")
                failed += 1

        cross_module_exports = detect_cross_module_exports(NOTEBOOKS_DIR)
        if cross_module_exports:
            print("\nApplying cross-module exports:")
            apply_cross_module_exports(output_dir, cross_module_exports)

        init_path = output_dir / '__init__.py'
        init_path.write_text(generate_init())
        print(f"Generated: {init_path.name}")

        print(f"\nConverted: {converted}, Skipped: {failed}")


if __name__ == '__main__':
    main()
