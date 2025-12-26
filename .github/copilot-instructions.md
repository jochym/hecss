# Copilot Instructions for HECSS

## Repository Overview

HECSS (High Efficiency Configuration Space Sampler) is a Python package implementing a Markov chain Monte-Carlo configuration space sampler using the Metropolis-Hastings algorithm for probability distribution sampling. It provides an alternative to expensive molecular dynamics simulations for creating representations of systems at thermal equilibrium.

**Key Technologies:**
- Python 3.6+
- ASE (Atomic Simulation Environment)
- nbdev (notebook-driven development)
- NumPy, SciPy for numerical computations
- Scientific computing for physics simulations

## Development Workflow

This project uses **nbdev**, a notebook-driven development framework where:
- Source code is written in Jupyter notebooks (`.ipynb` files)
- Library code is automatically generated from notebooks to the `hecss/` directory
- Documentation is auto-generated from the same notebooks

**Important:** 
- DO NOT manually edit files in the `hecss/` directory - they are auto-generated
- Make code changes in the corresponding `.ipynb` notebook files (e.g., `11_core.ipynb`, `12_monitor.ipynb`)
- The mapping between notebooks and modules:
  - `11_core.ipynb` → `hecss/core.py`
  - `12_monitor.ipynb` → `hecss/monitor.py`
  - `02_CLI.ipynb` → `hecss/cli.py`

## Build and Test Commands

### Building the Library
```bash
make hecss          # Build library from notebooks
nbdev_build_lib     # Alternative direct command
```

### Building Documentation
```bash
make docs           # Build documentation
nbdev_build_docs    # Alternative direct command
```

### Running Tests
```bash
make test           # Run all tests
nbdev_test_nbs      # Run tests directly

# Run specific test categories:
make test_asap      # Run ASAP3/OpenKIM tests only
make test_vasp      # Run VASP tests only
nbdev_test_nbs --flags asap  # Run tests with specific flags
```

### Cleaning Build Artifacts
```bash
make clean          # Clean distribution files
```

### Notebook Management
```bash
nbdev_clean_nbs     # Clean notebook outputs
nbdev_read_nbs      # Read all notebooks
nbdev_diff_nbs      # Check for differences between notebooks and library
```

## Code Style and Conventions

### General Python Style
- Follow PEP 8 conventions
- Use descriptive variable names
- Minimum Python version: 3.6

### Physics/Scientific Computing Conventions
- Use ASE units (`ase.units`) for physical quantities
- Energy values in eV (electron volts)
- Forces in eV/Angstrom
- Distances in Angstrom
- Temperature in Kelvin
- When writing displacement-force data, convert to Bohr/Rydberg units for ALAMODE compatibility

### Naming Conventions
- Classes: `PascalCase` (e.g., `HECSS_Sampler`, `HECSS`)
- Functions: `snake_case` (e.g., `calc_init_xscale`, `write_dfset`)
- Module-level constants: Use sparingly, document clearly

### Code Organization
- Keep related functionality in the same notebook
- Use clear docstrings for all public functions and classes
- Export symbols explicitly using `__all__` in notebooks
- Mark cells appropriately:
  - `# Cell` for exported code
  - `#export` directive for code to be included in the library

### Documentation
- Documentation is generated from notebooks
- Use markdown cells for narrative documentation
- Include code examples in notebooks
- Tutorial notebooks: `00_*.ipynb`, `01_*.ipynb`, etc.
- Core library notebooks: `11_*.ipynb`, `12_*.ipynb`, etc.

## Dependencies and Requirements

### Core Dependencies
Listed in `settings.ini`:
- `ase` - Atomic Simulation Environment
- `spglib` - Space group library
- `tqdm` - Progress bars
- `click` - CLI framework
- `matplotlib` - Plotting
- `numpy` - Numerical arrays
- `scipy` - Scientific computing
- `ipython` - Interactive Python

### Optional Dependencies
- `asap3` - ASAP3 calculator for LAMMPS potentials
- VASP - For VASP calculator integration

### Installation
```bash
pip install hecss                    # PyPI
conda install -c conda-forge hecss   # Conda-forge
```

## File Structure

```
.
├── .github/
│   ├── workflows/        # GitHub Actions CI
│   └── copilot-instructions.md
├── hecss/               # Auto-generated library code (DO NOT EDIT MANUALLY)
│   ├── core.py          # Generated from 11_core.ipynb
│   ├── monitor.py       # Generated from 12_monitor.ipynb
│   └── cli.py           # Generated from 02_CLI.ipynb
├── docs/                # Auto-generated documentation
├── example/             # Example data and scripts
├── data/                # Data files
├── *.ipynb              # Source notebooks
│   ├── 00_*.ipynb       # Setup and background
│   ├── 01_*.ipynb       # Tutorials
│   ├── 02_*.ipynb       # CLI documentation
│   ├── 03_*.ipynb       # Monitoring examples
│   ├── 11_core.ipynb    # Core library implementation
│   └── 12_monitor.ipynb # Monitoring implementation
├── settings.ini         # Project configuration
├── setup.py             # Package setup
├── Makefile             # Build commands
└── README.md            # Project readme
```

## Common Tasks

### Adding a New Feature
1. Identify the appropriate notebook (e.g., `11_core.ipynb` for core functionality)
2. Edit the notebook to add your feature
3. Run `nbdev_build_lib` to regenerate the library
4. Run `nbdev_test_nbs` to verify tests pass
5. Run `nbdev_build_docs` to update documentation

### Fixing a Bug
1. Locate the source notebook (not the generated .py file)
2. Fix the issue in the notebook
3. Rebuild library with `nbdev_build_lib`
4. Verify with tests: `nbdev_test_nbs`

### Adding Tests
- Add test code in the same notebook as the feature
- Use flags for slow or integration tests: `#slow`, `#vasp`, `#asap`, `#interactive`
- Tests are automatically discovered and run by `nbdev_test_nbs`

### Updating Documentation
- Edit narrative in markdown cells of notebooks
- Documentation is auto-generated from notebooks
- Run `make docs` to rebuild

## CI/CD

The project uses GitHub Actions (`.github/workflows/main.yml`):
- Runs on push and pull requests
- Installs dependencies with pip
- Checks notebook cleanliness
- Verifies library/notebook sync
- Runs test suite

## Important Notes

- **Primary repository:** GitLab (https://gitlab.com/jochym/hecss)
- **Mirror:** GitHub (https://github.com/jochym/hecss)
- **License:** GPL-3.0-or-later
- **Citation:** When using HECSS, cite the SciPost Physics paper (SciPost Phys. 10, 129 (2021))

## Getting Help

- Check the tutorials in `01_LAMMPS_Tutorial.ipynb` and `01_VASP_Tutorial.ipynb`
- Review the documentation at https://jochym.gitlab.io/hecss/
- See `CONTRIBUTING.md` for contribution guidelines
