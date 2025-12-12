# How to contribute

## Did you find a bug?

* Ensure the bug was not already reported by searching on GitHub under Issues.
* If you're unable to find an open issue addressing the problem, open a new one. Be sure to include a title and clear description, as much relevant information as possible, and a code sample or an executable test case demonstrating the expected behaviour that is not occurring.
* Be sure to add the complete error messages.

#### Did you write a patch that fixes a bug?

* Open a new GitHub pull request with the patch.
* Ensure that your PR includes a test that fails without your patch, and pass with it.
* Ensure the PR description clearly describes the problem and solution. Include the relevant issue number if applicable.

## PR submission guidelines

* Keep each PR focused. While it's more convenient, do not combine several unrelated fixes together. Create as many branches as needing to keep each PR focused.
* Do not mix style changes/fixes with "functional" changes. It's very difficult to review such PRs and it most likely get rejected.
* Do not add/remove vertical whitespace. Preserve the original style of the file you edit as much as you can.
* Do not turn an already submitted PR into your development playground. If after you submitted PR, you discovered that more work is needed - close the PR, do the required work and then submit a new PR. Otherwise each of your commits requires attention from maintainers of the project.
* If, however, you submitted a PR and received a request for changes, you should proceed with commits inside that PR, so that the maintainer can see the incremental fixes and won't need to review the whole PR again. In the exception case where you realise it'll take many many commits to complete the requests, then it's probably best to close the PR, do the work and then submit it again. Use common sense where you'd choose one way over another.

## Do you want to contribute to the documentation?

* Docs are automatically created from the notebooks in the `nbs/` folder.

## Development Setup

### Project Structure

After the recent refactoring, the project follows this structure:

```
hecss/
├── nbs/              # All Jupyter notebooks (source of truth)
├── hecss/            # Generated Python modules (DO NOT EDIT)
├── _docs/            # Generated documentation
├── data/             # Example data files
├── example/          # Example scripts and workflows
└── planning/         # Development planning documents
```

### Setting Up Development Environment

1. **Clone the repository:**
   ```bash
   git clone https://github.com/jochym/hecss.git
   cd hecss
   ```

2. **Create the conda environment:**
   The repository includes an `environment.yml` file with all dependencies:
   ```bash
   conda env create -f environment.yml
   conda activate hecss-dev
   ```

3. **Install in editable mode:**
   The package is automatically installed in editable mode when creating the environment.

### Development Workflow

This project uses [nbdev](https://nbdev.fast.ai/). **All code changes must be made in notebooks** located in the `nbs/` directory.

#### After modifying notebooks:

1. **Export to Python modules:**
   ```bash
   nbdev_export
   ```

2. **Update README:**
   If you modified `nbs/index.ipynb`:
   ```bash
   nbdev_readme
   ```

3. **Generate documentation:**
   ```bash
   nbdev_docs
   ```

4. **Run tests:**
   ```bash
   nbdev_test           # Run all tests
   nbdev_test --flags asap  # Run only tests marked with #| asap
   ```

#### Test Flags

Tests in notebooks can be marked with flags to control when they run:

- `#| asap` - Fast tests using ASAP3/OpenKIM calculators
- `#| vasp` - Tests requiring VASP
- `#| vasp_ase` - Tests using VASP through ASE
- `#| slow` - Long-running tests
- `#| interactive` - Tests requiring user interaction
- `#| quick` - Quick validation tests

### Important Notes

- **Never edit files in `hecss/` directory directly** - they are auto-generated from notebooks
- **Paths in notebooks:** Since notebooks are in `nbs/`, use `../` prefix for accessing files in root directory (e.g., `../data/spinel.POSCAR`)
- **Documentation changes:** Edit the corresponding notebook in `nbs/`, not the HTML files in `_docs/`

### Useful Commands

```bash
nbdev_preview        # Preview documentation locally
nbdev_clean          # Clean notebooks (remove outputs)
nbdev_install_hooks  # Install git hooks for automatic cleaning
```

