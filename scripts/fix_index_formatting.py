import json

nb_path = 'nbs/index.ipynb'

with open(nb_path, 'r') as f:
    nb = json.load(f)

# Find the markdown cell with "Development" section
target_cell = None
for cell in nb['cells']:
    if cell['cell_type'] == 'markdown':
        source = "".join(cell['source'])
        if "## Development" in source:
            target_cell = cell
            break

if target_cell:
    new_source = [
        "## Development\n",
        "\n",
        "1.  **Clone the repository:**\n",
        "\n",
        "    ```\n",
        "    git clone https://gitlab.com/jochym/hecss.git\n",
        "    cd hecss\n",
        "    ```\n",
        "\n",
        "2.  **Create the environment:**\n",
        "    The repository includes an `environment.yml` file for creating a Conda environment with all dependencies and the package installed in editable mode.\n",
        "\n",
        "    ```\n",
        "    conda env create -f environment.yml\n",
        "    conda activate hecss-dev\n",
        "    ```\n",
        "\n",
        "3.  **Workflow:**\n",
        "    This project uses `nbdev`. All code changes should be made in the notebooks located in the `nbs/` directory.\n",
        "\n",
        "    *   After modifying notebooks, run:\n",
        "        ```\n",
        "        nbdev_export\n",
        "        ```\n",
        "    *   To update the README, modify `nbs/index.ipynb` and run:\n",
        "        ```\n",
        "        nbdev_readme\n",
        "        ```\n"
    ]
    target_cell['source'] = new_source
    print("Fixed Development section formatting (removed language tags and added spacing).")

    with open(nb_path, 'w') as f:
        json.dump(nb, f, indent=1)
else:
    print("Could not find Development section.")
