# HECSS GUI Specification

## Overview
A graphical user interface for the HECSS library to simplify configuration, execution, and monitoring of sampling tasks. The design follows the approved energetic dark-themed mock-up.

## Modules

### 1. Dashboard (Main View)
- **Status Summary**: Current project, active calculations, overall connection status.
- **Quick Actions**: "New Job", "Load Project", "Connect to Cluster".

### 2. Job Configuration (Center Panel)
- **Input Parameters**:
    - `Supercell File` (File picker)
    - `Target Temperature` (Float input, K)
    - `Sample Count` (Int input)
    - `Width Scale` (Optional float or "Estimate" toggle)
- **Cluster Settings** (Accordion/Popup):
    - `Remote Host` (Dropdown from ~/.ssh/config)
    - `Remote Path` (Text input)
    - `Partition/Resources` (Tasks/Nodes)
- **Action Buttons**:
    - `Start Sampling` (Primary)
    - `Estimate Width` (Secondary)

### 3. Monitoring & Visualization (Right Panel)
- **Real-time Stats**:
    - **Energy Histogram**: Distribution of sampled energies vs Gaussian fit.
    - **Convergence Plot**: Width scale (`w`) evolution over iterations.
    - **Phonon Dispersion** (Tabbed): Optional view for calculated bands.
- **Terminal/Log**:
    - Streaming output from `sbatch` or local process.
    - Progress bars for sampling.

### 4. Sampling & Reshaping (Sidebar Tools)
- **Reshape Tool**: Interface for `reshape` CLI calculations.
    - Source DFSET selection.
    - Target Temperature.
    - Output filename.
- **Analysis**: Advanced plotting controls (sqrN, sixel mode toggles).

## Technical Stack
**Selected Framework**: [NiceGUI](https://nicegui.io)
- **Rationale**: 
    - Pure Python (Frontend & Backend).
    - Fully Cross-Platform (runs on Linux, Windows, macOS).
    - Lightweight installation (pip-installable).
    - High-level element abstraction (Simple & Maintainable).
    - Modern Material Design aesthetics out-of-the-box.
    - Excellent support for async/await (crucial for long-running calculations).
    - No build step required (unlike React/Vue).

## Constraints & Requirements
- **Simplicity**: Code structure must be obvious. Logic should be easy to follow for a physicist/python developer.
- **Maintainability**: Avoid complex "magic" or heavy frameworks that require specialized knowledge (like complex React interactions).
- **Dependencies**: Keep the dependency tree relatively flat. Avoid system-level dependencies (like Qt) if possible.
- **Performance**: UI responsiveness is important, but calculation speed is determined by the backend. The UI should not block during calculations.


## Visual Style
- **Theme**: Dark Mode (#1e1e1e background).
- **Accents**: Electric Blue for primary actions/active states.
- **Layout**: 3-Column (Nav | Config | Viz).
