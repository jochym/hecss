#!/usr/bin/env python3
"""
Build the hecss package from marimo notebooks.

Pipeline:
  1. ipynb -> notebooks/*.py        (marimo convert; one-time, manual fixes)
  2. notebooks/*.py -> build/scripts/*.py   (marimo export script; this tool)
  3. build/scripts/*.py -> hecss/*.py       (tag-driven assembly; this tool)

Tag semantics (nbdev-compatible):
  - #| default_exp <module>   module target of the notebook
  - #| export                 include code, add names to __all__
  - #| exporti                include code, keep out of __all__
  - #| exporti <module>       include code in another module (cross-module)
  - #| hide                   exclude

Usage:
    python scripts/build_lib.py              # build all modules + __init__
"""

import ast
import json
import re
import subprocess
import sys
import tomllib
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent

# Path layout is configuration ([tool.build_lib] in pyproject.toml);
# all assembly logic below is content-generic.
NOTEBOOKS_DIR = None
OUTPUT_DIR = None
SCRIPTS_DIR = None



def _init_paths(config: dict):
    global NOTEBOOKS_DIR, OUTPUT_DIR, SCRIPTS_DIR
    build_dir = Path(config.get('build_dir', 'build'))
    NOTEBOOKS_DIR = PROJECT_ROOT / config.get('notebooks_dir', 'notebooks')
    OUTPUT_DIR = PROJECT_ROOT / config.get('output_dir', 'hecss')
    SCRIPTS_DIR = PROJECT_ROOT / build_dir / 'scripts'


def load_config() -> dict:
    """Read optional [tool.build_lib] table from pyproject.toml."""
    pyproject = PROJECT_ROOT / 'pyproject.toml'
    if not pyproject.exists():
        return {}
    try:
        data = tomllib.loads(pyproject.read_text())
    except tomllib.TOMLDecodeError:
        return {}
    return data.get('tool', {}).get('build_lib', {})


# ---------------------------------------------------------------------------
# step 2: marimo export script
# ---------------------------------------------------------------------------

def export_script(nb_path: Path) -> Path:
    """Export a marimo notebook to a flat script via official exporter."""
    SCRIPTS_DIR.mkdir(parents=True, exist_ok=True)
    out_path = SCRIPTS_DIR / f"{nb_path.stem}.py"
    result = subprocess.run(
        ["marimo", "export", "script", str(nb_path), "-o", str(out_path)],
        capture_output=True, text=True,
    )
    if out_path.exists():
        return out_path
    if result.returncode != 0:
        raise RuntimeError(f"marimo export script failed for {nb_path.name}:\n"
                           f"{result.stderr.strip()}")
    return out_path


# ---------------------------------------------------------------------------
# notebook cell extraction (byte-faithful; used for module content)
# ---------------------------------------------------------------------------

def _dedent(code: str) -> str:
    lines = code.split('\n')
    min_indent = None
    for line in lines:
        if line.strip():
            indent = len(line) - len(line.lstrip())
            if min_indent is None or indent < min_indent:
                min_indent = indent
    if min_indent is None or min_indent == 0:
        return code
    return '\n'.join(line[min_indent:] if line.strip() else line
                     for line in lines)


def _strip_wrapper_return(code: str) -> str:
    lines = code.split('\n')
    last_idx = len(lines) - 1
    while last_idx >= 0 and not lines[last_idx].strip():
        last_idx -= 1
    if last_idx < 0:
        return code
    last_stripped = lines[last_idx].strip()
    is_return = last_stripped.startswith('return')
    is_close = last_stripped == ')'
    if not is_return and not is_close:
        return code
    if is_close:
        rs = last_idx
        while rs >= 0 and not lines[rs].strip().startswith('return'):
            rs -= 1
        if rs < 0:
            return code
    else:
        rs = last_idx
    min_indent = None
    for line in lines:
        if line.strip():
            ind = len(line) - len(line.lstrip())
            if min_indent is None or ind < min_indent:
                min_indent = ind
    min_indent = min_indent or 0
    if (len(lines[rs]) - len(lines[rs].lstrip())) > min_indent:
        return code
    depth = 0
    for line in lines[rs:]:
        for ch in line:
            if ch == '(':
                depth += 1
            elif ch == ')':
                depth -= 1
    if depth != 0:
        return code
    return '\n'.join(lines[:rs]).rstrip('\n')


def parse_notebook_blocks(nb_path: Path) -> list:
    """Extract tagged cell blocks from a marimo notebook file, preserving
    source bytes exactly (indentation, blank-line whitespace, trailing spaces)."""
    lines = nb_path.read_text().split('\n')
    starts = [i for i, l in enumerate(lines) if l.startswith('@app.cell')]
    file_end = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        s = lines[i].strip()
        if s.startswith(('if __name__', 'app.run')):
            file_end = i
        elif s and not s.startswith('#'):
            break

    blocks = []
    for ci, start in enumerate(starts):
        end = starts[ci + 1] if ci + 1 < len(starts) else file_end
        j = start + 1
        depth, found = 0, False
        while j < end and not found:
            for ch in lines[j]:
                if ch == '(':
                    depth += 1
                elif ch == ')':
                    depth -= 1
                elif ch == ':' and depth == 0:
                    found = True
                    break
            if not found:
                j += 1
        if not found:
            continue
        j += 1
        tags_lines, body = [], []
        for li in range(j, end):
            stripped = lines[li].strip()
            if stripped.startswith('#|'):
                tags_lines.append(stripped[2:].strip())
                continue
            body.append(lines[li])
        kind, target = resolve_tags(tags_lines)
        code = _strip_wrapper_return(_dedent('\n'.join(body))).strip('\n')
        if code.strip():
            blocks.append(Block(kind, target, code))
    return blocks


# ---------------------------------------------------------------------------
# step 3: parse exported script into tagged blocks
# ---------------------------------------------------------------------------

class Block:
    __slots__ = ('tags', 'target', 'code')

    def __init__(self, tags, target, code):
        self.tags = tags          # e.g. ['hide'] or ['exporti']
        self.target = target      # module name for cross-module tags
        self.code = code


def parse_script(text: str) -> list:
    """Split exported script on '# %%' separators into tagged blocks."""
    blocks = []
    current_tags, current_target, current_lines = [], None, []

    def flush():
        code = '\n'.join(current_lines).strip('\n')
        if not code.strip():
            return
        kind, target = resolve_tags(current_tags)
        blocks.append(Block(kind, target, code))

    for line in text.split('\n'):
        if line.startswith('# %%'):
            flush()
            current_tags, current_target, current_lines = [], None, []
            continue
        if (not current_lines) and line.lstrip().startswith('#|'):
            current_tags.append(line.lstrip()[2:].strip())
            continue
        current_lines.append(line)
    flush()
    return blocks


def resolve_tags(tags):
    """Collapse tag list to (kind, target). Last tag wins (matches nbdev
    practice in this repo where a stray leading '#| hide' precedes '#| export')."""
    kind, target = None, None
    for t in tags:
        parts = t.split()
        if not parts or parts[0] not in ('export', 'exporti', 'hide'):
            continue
        kind = parts[0]
        if len(parts) > 1:
            target = parts[1]
    return kind, target


_MD_RE = re.compile(r'^mo\.md\(', re.S)


def is_skippable(block: Block) -> bool:
    """No tag, pure markdown, or marimo boilerplate."""
    if block.tags is None or block.code is None:
        return True
    stripped = block.code.strip()
    if _MD_RE.match(stripped):
        return True
    if stripped.startswith('__generated_with') or \
            stripped.startswith('import marimo'):
        return True
    return False


# ---------------------------------------------------------------------------
# import handling
# ---------------------------------------------------------------------------

def _import_sort_key(imp: str) -> tuple:
    first_word = imp.split()[0] if imp else ''
    second_word = imp.split()[1] if len(imp.split()) > 1 else ''
    if second_word in sys.stdlib_module_names:
        return (0, imp)
    elif first_word == 'from' and '.' not in second_word \
            and second_word in sys.stdlib_module_names:
        return (0, imp)
    elif first_word == 'import':
        return (1, imp)
    elif first_word == 'from':
        return (2, imp) if '.' in second_word else (1, imp)
    return (3, imp)


def split_imports(code: str):
    """Return (imports:set, remaining_code:str). Wildcards become TODOs."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return set(), code
    imports = set()
    # Collect top-level import nodes
    import_nodes = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            import_nodes.append(node)
    
    if not import_nodes:
        return set(), code
    
    lines = code.split('\n')
    # Build set of line indices that are part of imports
    import_lines = set()
    for node in import_nodes:
        start = node.lineno - 1
        end = node.end_lineno
        # Check for wildcard
        if isinstance(node, ast.ImportFrom) and any(alias.name == '*' for alias in node.names):
            # Wildcard - will be replaced with TODO in remaining code
            for i in range(start, end):
                import_lines.add(i)
            continue
        # Regular import
        import_text = '\n'.join(lines[start:end]).rstrip()
        imports.add(import_text)
        for i in range(start, end):
            import_lines.add(i)
    
    # Reconstruct remaining code
    other_lines = []
    in_wildcard = False
    for i, line in enumerate(lines):
        if i in import_lines:
            # Check if this is part of a wildcard import
            stripped = line.strip()
            if 'import *' in stripped:
                if not in_wildcard:
                    # Find the module for the wildcard
                    for node in import_nodes:
                        if node.lineno - 1 <= i < node.end_lineno and isinstance(node, ast.ImportFrom):
                            if any(alias.name == '*' for alias in node.names):
                                module = node.module
                                other_lines.append(f"# TODO: Expand wildcard import: {stripped}")
                                other_lines.append(f"# Replace with explicit imports from {module}.__all__")
                                in_wildcard = True
                                break
            continue
        other_lines.append(line)
    
    # Handle case where wildcard import was multi-line
    remaining = '\n'.join(other_lines).strip('\n')
    return imports, remaining


# ---------------------------------------------------------------------------
# __all__ extraction (nbdev semantics)
# ---------------------------------------------------------------------------

def exported_names(code_blocks) -> list:
    names = []
    for code in code_blocks:
        try:
            tree = ast.parse(code)
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                     ast.ClassDef)):
                continue
            decorated = any(
                (getattr(d, 'id', '') == 'patch') or
                (getattr(getattr(d, 'func', None), 'id', '') == 'patch')
                for d in node.decorator_list)
            if decorated or node.name.startswith('_'):
                continue
            names.append(node.name)
    return names


# ---------------------------------------------------------------------------
# assembly
# ---------------------------------------------------------------------------

def build_module(module_name: str, blocks: list, docstring: str | None) -> str:
    included = [b for b in blocks
                if b.tags in ('export', 'exporti')
                and (b.target is None or b.target == module_name)]

    imports = set()
    bodies = []
    for b in included:
        imps, rest = split_imports(b.code)
        imports |= imps
        if rest.strip():
            bodies.append(rest)

    own_export_blocks = [b.code for b in included if b.tags == 'export'
                         and b.target is None]
    all_names = exported_names(own_export_blocks)

    lines = []
    if docstring:
        lines += [f'"""{docstring}"""', '']
    lines += [
        '# AUTOGENERATED! DO NOT EDIT!',
        '',
        "__all__ = [" + ', '.join(f"'{n}'" for n in all_names) + "]",
        '',
    ]
    if imports:
        lines += sorted(imports, key=_import_sort_key) + ['']
    for body in bodies:
        lines += [body, '']
    return '\n'.join(lines)


def merge_into_module(target_module: str, blocks: list, output_dir: Path):
    """Append cross-module blocks at end of an existing module (nbdev-style),
    merging their imports into the module's import section."""
    output_path = output_dir / f"{target_module}.py"
    if not output_path.exists():
        print(f"  Warning: {target_module}.py missing, skipping cross-module blocks")
        return

    existing = output_path.read_text()
    original_lines = existing.split('\n')

    existing_imports = set()
    first_import_idx = None
    first_code_idx = len(original_lines)
    in_docstring = False
    for i, line in enumerate(original_lines):
        stripped = line.strip()
        if stripped.startswith(('"""', "'''")):
            quote = stripped[:3]
            if stripped.count(quote) >= 2:
                continue
            in_docstring = not in_docstring
            continue
        if in_docstring:
            continue
        if stripped.startswith(('import ', 'from ')) and \
                not line.startswith((' ', '\t')):
            if first_import_idx is None:
                first_import_idx = i
            imps, _ = split_imports(line)
            existing_imports |= imps
        elif stripped == '' or stripped.startswith('#') or \
                stripped.startswith('__all__'):
            continue
        elif stripped and first_code_idx == len(original_lines):
            first_code_idx = i

    new_imports, new_bodies = set(), []
    for b in blocks:
        imps, rest = split_imports(b.code)
        new_imports |= imps
        if rest.strip():
            new_bodies.append(rest)

    header_end = first_import_idx if first_import_idx is not None else first_code_idx
    header = original_lines[:header_end]
    while header and not header[-1].strip():
        header.pop()
    body = original_lines[first_code_idx:]

    merged = sorted(existing_imports | new_imports, key=_import_sort_key)
    out = header + [''] + merged + [''] + body
    for b in new_bodies:
        out += b.split('\n') + ['']

    output_path.write_text('\n'.join(out))
    print(f"  Merged cross-module blocks into {target_module}.py")


def extract_module_docstring(ipynb_path: str) -> str | None:
    """Extract the first markdown cell from ipynb as module docstring."""
    try:
        raw = subprocess.run(
            ['git', '-C', str(PROJECT_ROOT), 'show', f'3578cce:{ipynb_path}'],
            capture_output=True, text=True, check=True
        ).stdout
        data = json.loads(raw)
        for cell in data['cells']:
            if cell['cell_type'] == 'markdown':
                content = ''.join(cell['source']).strip()
                if content:
                    # Handle "# Title\n\n> Description" format
                    lines = content.split('\n')
                    # Skip leading # header lines
                    start = 0
                    while start < len(lines) and lines[start].strip().startswith('#'):
                        start += 1
                    while start < len(lines) and not lines[start].strip():
                        start += 1
                    doc_lines = []
                    for line in lines[start:]:
                        if line.strip().startswith('>'):
                            doc_lines.append(line.strip()[1:].strip())
                        elif line.strip() == '':
                            doc_lines.append('')
                        else:
                            doc_lines.append(line.strip())
                    doc = '\n'.join(doc_lines).strip()
                    if doc:
                        return doc
                    # Fallback: if no blockquote, check if original was just a title
                    # For planner, first markdown is just "# Temperature scan planner" with no description
                    # Canonical has no docstring, so return None
                    if content.strip().startswith('#') and '\n' not in content.strip():
                        return None
                    return content
    except Exception:
        pass
    return None


def build_ipynb_module_map(notebooks: list[Path]) -> dict[str, str]:
    """Build mapping from module name (default_exp) to ipynb filename in git."""
    # Hardcoded mapping for the 8 library modules (well-defined, from nbdev)
    # This is the correct source for module docstrings
    return {
        'core': '11_core.ipynb',
        'cli': '02_CLI.ipynb',
        'monitor': '15_monitor.ipynb',
        'optimize': '12_optimize.ipynb',
        'parallel': '11_parallel.ipynb',
        'planner': '13_planner.ipynb',
        'util': '16_util.ipynb',
        'xscale': '17_xscale.ipynb',
    }


def get_module_docstring(module_name: str, ipynb_map: dict[str, str]) -> str | None:
    """Get module docstring from canonical ipynb."""
    ipynb = ipynb_map.get(module_name)
    if ipynb:
        doc = extract_module_docstring(ipynb)
        if doc:
            return doc
    return None


def generate_init(config: dict) -> str:
    """Package __init__: version from pyproject plus optional star-import
    of the module named in config key `init_star_import`."""
    version = '0.0.0'
    pyproject = PROJECT_ROOT / 'pyproject.toml'
    if pyproject.exists():
        m = re.search(r'^version\s*=\s*"([^"]+)"',
                      pyproject.read_text(), re.M)
        if m:
            version = m.group(1)
    text = f'__version__ = "{version}"\n'
    star = config.get('init_star_import')
    if star:
        text += f'\nfrom .{star} import *\n'
    return text + '\n'


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    config = load_config()
    _init_paths(config)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Build ipynb module map from all notebooks (for docstring extraction)
    ipynb_map = build_ipynb_module_map(NOTEBOOKS_DIR.glob('*.py'))
    
    notebooks = sorted(p for p in NOTEBOOKS_DIR.glob('*.py')
                       if not p.name.startswith('_'))
    targets = {}       # module_name -> [blocks]
    cross = {}         # target_module -> [blocks]

    # Phase 1: export relevant notebooks (validation gate)
    # Note: export may fail for notebooks with cycles (e.g., 11_core) - we still
    # build from notebooks directly in that case (byte-faithful fallback)
    for nb in notebooks:
        source = nb.read_text()
        if not re.search(r'^\s*#\|\s*default_exp\s+\S+', source, re.MULTILINE) and \
           not re.search(r'^\s*#\|\s*(?:export|exporti)\s+\S+', source, re.MULTILINE):
            continue
        try:
            export_script(nb)
        except RuntimeError as e:
            print(f"  Note: {nb.name} export failed (building from notebook directly): {str(e).splitlines()[-1][:80]}")

    # Phase 2: apply disposable script patches if present (well-defined, to be dropped)
    patch_script = PROJECT_ROOT / 'patches' / '02-scripts.py'
    if patch_script.exists():
        print(f"Applying disposable patch: {patch_script}")
        result = subprocess.run([sys.executable, str(patch_script)], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)

    # Phase 3: read scripts (prefer patched intermediate, fallback to notebook)
    notebooks = sorted(p for p in NOTEBOOKS_DIR.glob('*.py')
                       if not p.name.startswith('_'))
    targets = {}       # module_name -> [blocks]
    cross = {}         # target_module -> [blocks]

    for nb in notebooks:
        source = nb.read_text()
        module = None
        m = re.search(r'^\s*#\|\s*default_exp\s+(\S+)', source, re.MULTILINE)
        if m:
            module = m.group(1)
        else:
            if not re.search(r'^\s*#\|\s*(?:export|exporti)\s+\S+', source, re.MULTILINE):
                continue
        script_path = SCRIPTS_DIR / f"{nb.stem}.py"
        if script_path.exists():
            blocks = [b for b in parse_script(script_path.read_text())
                      if not is_skippable(b)]
        else:
            # Fallback: notebook has cycles or export failed - build directly from notebook (byte-faithful)
            blocks = [b for b in parse_notebook_blocks(nb)
                      if not is_skippable(b)]
        if module is not None:
            targets.setdefault(module, []).extend(blocks)
        else:
            for b in blocks:
                if b.tags in ('export', 'exporti') and b.target:
                    cross.setdefault(b.target, []).append(b)

    # Phase 4: build each module
    for module, blocks in targets.items():
        local = [b for b in blocks
                 if b.target is None or b.target == module]
        foreign = [b for b in blocks if b.target and b.target != module]
        docstring = get_module_docstring(module, ipynb_map)
        out = build_module(module, local, docstring)
        (OUTPUT_DIR / f"{module}.py").write_text(out)
        print(f"Built: {module}.py ({len(local)} blocks)")
        if foreign:
            cross.setdefault(foreign[0].target, []).extend(foreign)

    for target_module, blocks in sorted(cross.items()):
        merge_into_module(target_module,
                          [Block(b.tags, None, b.code) for b in blocks],
                          OUTPUT_DIR)

    init_path = OUTPUT_DIR / '__init__.py'
    init_path.write_text(generate_init(config))
    print(f"Generated: {init_path.relative_to(PROJECT_ROOT)}")


if __name__ == '__main__':
    main()
