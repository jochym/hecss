import json

nb_path = 'nbs/02_CLI.ipynb'

with open(nb_path, 'r') as f:
    nb = json.load(f)

for cell in nb['cells']:
    if 'source' in cell and len(cell['source']) > 0:
        # Check if this is the cell with the error (has source starting with import os and includes the indented line)
        source = "".join(cell['source'])
        if "from tempfile import TemporaryDirectory" in source and "import os" in source:
             new_source = []
             for line in cell['source']:
                 if "from tempfile import TemporaryDirectory" in line:
                     # Strip leading spaces
                     new_source.append(line.lstrip())
                 else:
                     new_source.append(line)
             cell['source'] = new_source
             print("Fixed indentation for TemporaryDirectory import.")

with open(nb_path, 'w') as f:
    json.dump(nb, f, indent=1)
