# HECSS Implementation Plan (v0.6.0 Prep)

## Goal
Prepare the HECSS repository for the version 0.6.0 release. The focus is on **establishing a robust local development environment**, **reorganizing the repository structure**, and enabling **efficient remote execution** for testing.

## User Review Required
> [!IMPORTANT]
> **Missing Features**: Please specify the "missing functions" functionality that needs to be implemented. I have created a placeholder (Phase 5) in the plan for this.

## Architecture Decisions (Confirmed)
*   **Package Manager**: **Conda (Mamba)**. User confirmed availability.
*   **Remote Execution**: **Option C (Local Submission Node)** is the primary target. Fallback to SSH-Wrapper if needed.

## Proposed Changes

### Phase 0: Local Environment & Architecture (Priority)
**Goal**: Functional local dev setup with remote capability.
- **Actions**:
  1.  **Environment Setup**: Create `hecss-dev` env using `environment.yml`.
  2.  **Remote Config**: Configure local machine as Slurm submitter or implement wrapper using `hecss.util`.

### Phase 1: Repository Reorganization (Completed)
**Goal**: Isolate notebooks to `nbs/`.
- **Status**: Notebooks moved, `settings.ini` updated.
- **Next**: Verify `nbdev_export` works.

### Phase 2: Code Cleanup
- **Nbdev Sync**: Ensure sync after reorg.
- **Linting**: Formatting and import cleanup.

### Phase 3: Documentation
- Update `README` and Tutorials to reflect the new Local/Remote workflow.

### Phase 4: CLI & Testing
- **Smoke Tests**: Local ASAP3/LJ tests (lightweight).
- **Integration Tests**: Remote VASP tests.

### Phase 5: Feature Implementation (TBD)
- **Pending**: User input needed.
