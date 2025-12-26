import json

nb_path = 'nbs/index.ipynb'

with open(nb_path, 'r') as f:
    nb = json.load(f)

# Find the markdown cell with "Development" section
target_cell = None
found = False
for cell in nb['cells']:
    if cell['cell_type'] == 'markdown':
        source = "".join(cell['source'])
        if "## Development" in source:
            target_cell = cell
            found = True
            break

if found:
    # Append the new instruction to the source list
    # Check if it ends with newline
    current_source = target_cell['source']
    
    # We want to add a list item for nbdev_docs
    new_lines = [
        "    *   To generate full documentation locally, run:\n",
        "        \n",
        "        ```bash\n",
        "        nbdev_docs\n",
        "        ```\n"
    ]
    
    # Extend the source
    current_source.extend(new_lines)
    
    print("Appended nbdev_docs instruction.")

    with open(nb_path, 'w') as f:
        json.dump(nb, f, indent=1)
else:
    print("Could not find Development section.")
