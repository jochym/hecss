#!/usr/bin/env python3
"""
Stage-1 patch: notebooks/*.py (fresh from marimo convert)

Well-defined, disposable, one concern per script.
Fixes _unparsable_cell wrappers by properly unwrapping or discarding.

Each asserts expected state before/after.
"""
import re
from pathlib import Path

REPO = Path(__file__).parent.parent

def fix_unparsable():
    count_kept = 0
    count_discarded = 0
    for p in (REPO / 'notebooks').glob('*.py'):
        text = p.read_text()
        original = text
        
        def replace_unparsable(m):
            inner = m.group(1)
            # Check if inner is nbdev boilerplate (discard)
            if 'from nbdev import' in inner or 'from nbdev.showdoc' in inner:
                return ''
            # For other content, unwrap to proper cell
            # Extract tags and code from inner
            lines = inner.strip().split('\n')
            tags = []
            code_lines = []
            for line in lines:
                if line.strip().startswith('#|'):
                    tags.append(line.strip())
                elif line.strip():
                    code_lines.append(line)
            if not code_lines:
                return ''
            # Reconstruct as proper marimo cell
            # Find a simple case: if inner has imports, make it a proper cell
            tag_str = '\n'.join(f"    {t}" for t in tags) + '\n' if tags else ''
            code_str = '\n'.join(f"    {l}" for l in code_lines)
            return f"@app.cell\ndef _():\n{tag_str}{code_str}\n    return\n\n"
        
        # Pattern for _unparsable_cell
        pattern = r'app\._unparsable_cell\(\s*r"""(.*?)""",\s*name="_"\s*\)\s*\n'
        new_text = re.sub(pattern, replace_unparsable, text, flags=re.DOTALL)
        
        if new_text != text:
            p.write_text(new_text)
            kept = new_text.count('@app.cell') - text.count('@app.cell')
            discarded = text.count('_unparsable_cell') - new_text.count('_unparsable_cell')
            count_kept += max(0, kept)
            count_discarded += discarded
    
    print(f"Unparsable cells: {count_discarded} discarded (nbdev boilerplate), {count_kept} unwrapped to proper cells")

def patch_99mh():
    p = REPO / 'notebooks/99_mh.py'
    text = p.read_text()
    if '#| default_exp mh' not in text:
        if 'Legacy reference' in text:
            print("99_mh: already patched")
            return
        print("99_mh: no default_exp found, adding legacy header")
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if line.strip() == 'app = marimo.App()':
                lines.insert(i+1, '')
                lines.insert(i+2, '#| hide')
                lines.insert(i+3, '# Legacy reference only (pre-0.6 sampler). Not built into the library:')
                lines.insert(i+4, '# this notebook carries no module-target tag, so build_lib skips it.')
                break
        p.write_text('\n'.join(lines))
        return
    assert text.count('#| default_exp mh') == 1
    text = text.replace(
        '#| default_exp mh',
        '#| hide\n# Legacy reference only (pre-0.6 sampler). Not built into the library:\n# this notebook carries no module-target tag, so build_lib skips it.'
    )
    p.write_text(text)
    assert '#| default_exp mh' not in p.read_text()
    print("99_mh: de-targeted")

def patch_parwidth():
    p = REPO / 'notebooks/11_parwidth.py'
    text = p.read_text()
    if 'async def _(N, hecss):' not in text:
        print("11_parwidth: already patched")
        return
    old = "async def _(N, hecss):\n    #|vasp\n    await hecss.__estimate_width_scale_aio(N//2, Tmax=2000, nwork=N//2)"
    new = "def _(N, asyncio, hecss):\n    asyncio.run(hecss.__estimate_width_scale_aio(N//2, Tmax=2000, nwork=N//2))"
    assert old in text, "parwidth async pattern not found"
    text = text.replace(old, new)
    p.write_text(text)
    assert 'async def _(N, hecss):' not in p.read_text()
    print("11_parwidth: async fixed")

def ensure_default_exp():
    mapping = {
        '11_core.py': 'core',
        '11_parallel.py': 'parallel',
        '02_cli.py': 'cli',
        '12_optimize.py': 'optimize',
        '13_planner.py': 'planner',
        '15_monitor.py': 'monitor',
        '16_util.py': 'util',
        '17_xscale.py': 'xscale',
    }
    for nb_name, module in mapping.items():
        p = REPO / 'notebooks' / nb_name
        text = p.read_text()
        has_proper = any(line.startswith('#| default_exp') for line in text.split('\n'))
        if has_proper:
            print(f"{nb_name}: already has proper default_exp")
            continue
        lines = text.split('\n')
        for i, line in enumerate(lines):
            if line.strip() == 'app = marimo.App()':
                lines.insert(i+1, '')
                lines.insert(i+2, f'#| default_exp {module}')
                lines.insert(i+3, '')
                break
        p.write_text('\n'.join(lines))
        print(f"{nb_name}: added default_exp {module}")

if __name__ == '__main__':
    fix_unparsable()
    ensure_default_exp()
    patch_99mh()
    patch_parwidth()
    print("01-notebooks: done")
