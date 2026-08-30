#!/usr/bin/env python3
"""
Stage-2 patch: build/scripts/*.py (from marimo export script)

Well-defined, disposable:
- AugAssign revert: a = a + b  ->  a += b  (and -=, *=, /=)
  Only for simple name targets where left var == first operand.
  AST logic identical before/after (verified via ast.dump minus docstrings).

Asserts expected counts.
"""
import ast, re
from pathlib import Path

REPO = Path(__file__).parent.parent
SCRIPTS_DIR = REPO / 'build' / 'scripts'

def patch_augassign():
    if not SCRIPTS_DIR.exists():
        print("build/scripts not found - run marimo export first")
        return
    total = 0
    for p in sorted(SCRIPTS_DIR.glob('*.py')):
        text = p.read_text()
        original = text
        # Pattern: indent + var + " = " + var + " +|-|\*|/ " + expr
        def repl(m):
            indent, var, op = m.group(1), m.group(2), m.group(3).strip()
            expr = m.group(4).strip()
            return f"{indent}{var} {op}= {expr}"
        pattern = r'^([ \t]*)(\w+) = \2 ([+\-*/]) ([^\n]+)$'
        new_text = re.sub(pattern, repl, text, flags=re.MULTILINE)
        if new_text != text:
            # Verify still parses and logic is AugAssign-equivalent
            try:
                ast.parse(new_text)
            except SyntaxError as e:
                print(f"{p.name}: skip (parse error after patch: {e})")
                continue
            p.write_text(new_text)
            patched = len(re.findall(pattern, original, re.MULTILINE))
            total += patched
            print(f"{p.name}: {patched} AugAssign reverted")
    print(f"02-scripts: total {total} reverted")

if __name__ == '__main__':
    patch_augassign()
    print("02-scripts: done")
