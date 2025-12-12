# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - AG Branch

### Changed
- **Project Structure Reorganization**: All Jupyter notebooks moved to `nbs/` directory
  - Updated `settings.ini` to reflect new notebook path (`nbs_path = nbs`)
  - Updated all auto-generated file headers to reference `nbs/` directory
  - All example data and resources remain in root-level directories
  
- **Path Fixes in Tests**: 
  - Fixed relative paths in notebooks to use `../` prefix for accessing root-level directories
  - Added `../` to data file paths (e.g., `../data/spinel.POSCAR`)
  - Added `../` to output directory paths (e.g., `../AUX/`)
  
- **Import Fixes**:
  - Added missing `import spglib` in `11_core.ipynb`
  
- **Documentation Updates**:
  - README.md restructured to include both Installation and Development sections
  - Installation instructions restored for end users (pip and conda)
  - Development section enhanced with nbdev workflow details
  
- **Test Configuration**:
  - Added `vasp_ase` to test flags in `settings.ini`
  - All tests with `#| asap` flag now pass successfully

### Added
- Planning documents in `planning/` directory
  - `implementation_plan.md`
  - `task.md`
  - `testing_improvement_plan.md`
  - `testing_improvement_tasks.md`
- AI development notes in `AI_notes/` directory
- New development notebooks:
  - `90_Development.ipynb`
  - `98_ase_smoketest.ipynb`
- Integration test infrastructure (`test_integration.py`)
- Helper scripts for documentation maintenance:
  - `append_docs_instruction.py`
  - `fix_cli_indentation.py`
  - `fix_cli_paths.py`
  - `fix_index_formatting.py`
  - `verify_imports.py`
- Example scripts for remote execution:
  - `example/scripts/run-calc-ssh.sh`
  - `example/scripts/test-*.sh`
- Mock VASP script for testing (`mock_vasp.sh`)

### Fixed
- Relative path issues in test execution due to notebook relocation
- Missing imports causing test failures
- Path references in auto-generated Python modules

## [Previous Versions]

### From devel branch
- Block nonsense combinations of parameters
- Fix workdir for parallel execution
- Fix CLI notebook
- Refuse to overwrite existing calculations in CLI

---

**Note**: This changelog documents changes specific to the AG branch. For a complete history, see git log and compare with the `devel` branch.
