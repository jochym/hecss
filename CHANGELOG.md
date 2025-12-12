# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] - AG Branch

### Status
- ✅ All basic tests passing: `nbdev_test --flags asap` (Success)
- ✅ All quick tests passing: `nbdev_test --flags quick` (Success)
- ✅ ASE+VASP smoke test passing: `nbdev_test --flags vasp_ase` (Success)
- ⚠️ VASP tests require actual VASP installation (not available in hecss-dev environment)
- 📚 Documentation generation: `nbdev_docs` successfully renders 22 notebooks to HTML

### Changed
- **Project Structure Reorganization**: Complete restructuring for better organization
  - All Jupyter notebooks moved to `nbs/` directory
  - Updated `settings.ini` to reflect new notebook path (`nbs_path = nbs`)
  - Updated all auto-generated file headers to reference `nbs/` directory
  - Renamed `example/` → `examples/` for consistency
  - Moved `data/` → `examples/data/` for logical grouping
  - Created `scripts/` directory for development scripts
  - Created `.tmp/` for test working directory (gitignored)
  - Created `.local/` for user-specific files (gitignored)
  - Moved `local/` → `.local/` to hide from main view
  - Updated `run-calc.sh` to reference `examples/scripts/run-calc-ssh.sh`
  
- **Path Fixes in Tests**: 
  - Fixed relative paths in notebooks to use `../` prefix for accessing root-level directories
  - Updated paths: `../data/` → `../examples/data/`
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
- Development scripts in `scripts/` directory:
  - `test_integration.py` - integration test infrastructure
  - `append_docs_instruction.py` - documentation helper
  - `fix_cli_indentation.py` - code formatting helper
  - `fix_cli_paths.py` - path fixing helper
  - `fix_index_formatting.py` - index formatting helper
  - `verify_imports.py` - import verification
  - `mock_vasp.sh` - mock VASP for testing
- Example scripts for remote execution:
  - `examples/scripts/run-calc-ssh.sh`
  - `examples/scripts/test-*.sh`
- New directory structure:
  - `.tmp/` - temporary test working directory
  - `.local/` - user-specific local files
  - `scripts/` - development and build scripts

### Removed
- Removed obsolete environment files (`asap_env.yaml`, `std_env.yaml`)
- Cleaned up cache directories (`TMP/`, `_proc/`, `index_files/`, `hecss.egg-info/`)
- Removed temporary test directory (`integration_test_workdir/`)

### Fixed
- Relative path issues in test execution due to notebook relocation
- Missing imports causing test failures
- Path references in auto-generated Python modules
- Updated all data paths from `data/` to `examples/data/`
- Fixed path reference in `run-calc.sh` from `example/` to `examples/`
- Fixed temporary directory paths from `../TMP` to `../.tmp` in notebooks
- Resolved smoketest notebook output rendering (executed successfully)

### Git History
- Rebased AG branch to create linear history:
  - `55e6225` - docs: Comprehensive documentation update
  - `60e090d` - refactor: Major project structure reorganization
  - `155879b` - fix: Update smoketest notebook and documentation rendering
- Force-pushed to origin to maintain linear commit history

## [Previous Versions]

### From devel branch
- Block nonsense combinations of parameters
- Fix workdir for parallel execution
- Fix CLI notebook
- Refuse to overwrite existing calculations in CLI

---

**Note**: This changelog documents changes specific to the AG branch. For a complete history, see git log and compare with the `devel` branch.
