import json
import re

nb_path = 'nbs/02_CLI.ipynb'

with open(nb_path, 'r') as f:
    nb = json.load(f)

changes_count = 0

for cell in nb['cells']:
    if 'source' in cell:
        new_source = []
        for line in cell['source']:
            original_line = line
            
            # Fix example paths
            # Replace "example/" with "../example/" but avoid double dots if already correct
            # We use a negative lookbehind or just simple replacement if we are careful.
            # Simple replacement: " example/" -> " ../example/" can be safer?
            # Or better: "example/VASP" -> "../example/VASP"
            if "example/" in line and "../example/" not in line:
                line = line.replace("example/", "../example/")
                
            # user mentioned "file CLI are numerous errors caused by changing paths to files. Convert absolute paths to relative."
            # and "Maybe TMP folder should be inside nbs?"
            # So we ensure TMP is relative.
            # Fix absolute paths to TMP if any exist in SOURCE (outputs are fine to be wrong until re-run)
            # Example absolute: /home/jochym/Projects/hecss/devel/TMP -> TMP
            # We can try to strip the absolute prefix if it matches the pattern
            
            line = re.sub(r'/home/jochym/Projects/hecss/devel/TMP', 'TMP', line)
             
            # Fix TemporaryDirectory usage if needed
            # "calc_dir = TemporaryDirectory(dir='TMP')" -> ensure TMP exists
            # We can add a line before this to create TMP
            if "TemporaryDirectory(dir='TMP')" in line:
                 # This is tricky to insert a line in a list comprehension.
                 # But we can change the directory to '.' or just ensure it exists elsewhere with a separate cell.
                 # OR, we replace it with "os.makedirs('TMP', exist_ok=True); calc_dir = TemporaryDirectory(dir='TMP')"
                 # But imports might be missing.
                 # A safer bet is to change dir='TMP' to dir='.' if we want to be safe,
                 # BUT user said "Maybe TMP should be inside nbs?".
                 # If we keep dir='TMP', we MUST ensure it exists.
                 # Let's see if we can inject the makedirs call.
                 pass

            if line != original_line:
                changes_count += 1
            new_source.append(line)
            
        cell['source'] = new_source

# Inject a cell at the top (after imports) to ensure TMP exists
# Find the import cell
insert_idx = -1
for i, cell in enumerate(nb['cells']):
    source_str = "".join(cell.get('source', []))
    if "from tempfile import TemporaryDirectory" in source_str:
        insert_idx = i
        break

if insert_idx != -1:
    # Check if we already have makedirs
    if "os.makedirs('TMP', exist_ok=True)" not in "".join(nb['cells'][insert_idx]['source']):
        # We can append it to this cell or insert a new one
        # Appending is safer for execution flow
        nb['cells'][insert_idx]['source'].insert(0, "import os\nos.makedirs('TMP', exist_ok=True)\n")
        changes_count += 1
        print("Injectedos.makedirs('TMP')")

print(f"Fixed {changes_count} lines/cells.")

with open(nb_path, 'w') as f:
    json.dump(nb, f, indent=1)
