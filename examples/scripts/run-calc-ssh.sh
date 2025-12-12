#!/bin/bash
# =============================================================================
# run-calc-ssh.sh - Remote VASP/calculation execution script
# =============================================================================
# This script:
# 1. Copies local working directory contents to remote server
# 2. Executes a job script on the remote system (optionally via SLURM)
# 3. Waits for job completion
# 4. Syncs results back to local directory
#
# Configuration: via run-calc.conf file or HECSS_* environment variables
# =============================================================================

set -euo pipefail

# =============================================================================
# Configuration Loading
# =============================================================================
# Load config files (priority: CWD, ~/.hecss, ~/ , script dir)
[[ -f ./run-calc.conf ]] && source ./run-calc.conf 
[[ -f ~/.hecss/run-calc.conf ]] && source ~/.hecss/run-calc.conf 
[[ -f ~/run-calc.conf ]] && source ~/run-calc.conf
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
[[ -f "${SCRIPT_DIR}/run-calc.conf" ]] && source "${SCRIPT_DIR}/run-calc.conf"

# Read configuration (environment variables take precedence)
REMOTE_HOST="${HECSS_REMOTE_HOST:-}"
REMOTE_BASE="${HECSS_REMOTE_BASE:-}"
USE_SLURM="${HECSS_USE_SLURM:-true}"
PARTITION="${HECSS_PARTITION:-standard}"
TASKS="${HECSS_TASKS:-64}"
NODES="${HECSS_NODES:-1}"
REMOTE_CMD="${HECSS_REMOTE_CMD:-run-vasp-script}"
INPUT_FILES="${HECSS_INPUT_FILES:-POSCAR INCAR POTCAR KPOINTS}"
EXCLUDE_SYNC="${HECSS_EXCLUDE_SYNC:-WAVECAR CHGCAR}"
CLEANUP_REMOTE="${HECSS_CLEANUP_REMOTE:-true}"

# =============================================================================
# Validation
# =============================================================================

validate_config() {
    local errors=0
    
    if [[ -z "$REMOTE_HOST" ]]; then
        echo "ERROR: HECSS_REMOTE_HOST not set (SSH alias or user@host)"
        errors=$((errors + 1))
    fi
    
    if [[ -z "$REMOTE_BASE" ]]; then
        echo "ERROR: HECSS_REMOTE_BASE not set (remote base directory)"
        errors=$((errors + 1))
    fi
    
    if [[ $errors -gt 0 ]]; then
        echo ""
        echo "Configuration can be set via:"
        echo "  1. File: ~/run-calc.conf or ./run-calc.conf"
        echo "  2. Environment variables: HECSS_REMOTE_HOST, HECSS_REMOTE_BASE, etc."
        echo ""
        echo "See run-calc.conf.example for all options."
        exit 1
    fi
}

# =============================================================================
# Helper Functions
# =============================================================================

log_step() {
    echo "[$1] $2"
}

log_error() {
    echo "ERROR: $1" >&2
}

# Build rsync exclude arguments
build_exclude_args() {
    local excludes=""
    for item in $EXCLUDE_SYNC; do
        excludes="$excludes --exclude=$item"
    done
    echo "$excludes"
}

# Cleanup function for remote directory (always executed via trap)
cleanup_remote() {
    if [[ -n "${REMOTE_DIR:-}" ]] && [[ -n "${REMOTE_HOST:-}" ]]; then
        if [[ "${CLEANUP_REMOTE:-true}" == "true" ]]; then
            # Remove files from EXCLUDE_SYNC list
            if [[ -n "${EXCLUDE_SYNC:-}" ]]; then
                for file in $EXCLUDE_SYNC; do
                    if ssh "${REMOTE_HOST}" "rm -f '${REMOTE_DIR}/${file}' 2>/dev/null"; then
                        echo "${file} removed: ${REMOTE_HOST}:${REMOTE_DIR}/${file}"
                    fi
                done
            fi
            # Try to remove directory (safe: rmdir only works on empty dirs)
            if ssh "${REMOTE_HOST}" "rmdir '${REMOTE_DIR}' 2>/dev/null"; then
                echo "Remote directory removed: ${REMOTE_HOST}:${REMOTE_DIR}"
            else
                # Directory not empty or already removed - non-fatal
                echo "Remote directory cleanup skipped (may contain files or already removed)"
            fi
        fi
    fi
}

# =============================================================================
# Main Script
# =============================================================================

# Validate configuration
validate_config

# Set up paths
JOB_NAME=$(basename "$(pwd)")
LOCAL_DIR=$(pwd)
# Generate unique remote directory name: hecss_timestamp_PID_random
UNIQUE_SUFFIX="$(date +%s)_$$_$((RANDOM % 10000))"
REMOTE_DIR="${REMOTE_BASE}/hecss_${UNIQUE_SUFFIX}"

# Set up cleanup trap to ensure remote directory is removed on exit
trap cleanup_remote EXIT

echo "=============================================="
echo "Remote Calculation: ${JOB_NAME}"
echo "=============================================="
echo "  Local:   ${LOCAL_DIR}"
echo "  Remote:  ${REMOTE_HOST}:${REMOTE_DIR}"
echo "  SLURM:   ${USE_SLURM}"
echo "=============================================="

# Step 1: Create remote directory
log_step "1/5" "Creating remote directory..."
if ! ssh "${REMOTE_HOST}" "mkdir -p '${REMOTE_DIR}'"; then
    log_error "Could not create remote directory"
    exit 1
fi

# Step 2: Transfer input files
log_step "2/5" "Transferring input files..."
EXCLUDE_ARGS=$(build_exclude_args)

# shellcheck disable=SC2086
if ! rsync -avz $EXCLUDE_ARGS $INPUT_FILES "${REMOTE_HOST}:${REMOTE_DIR}/"; then
    log_error "File transfer failed"
    exit 1
fi

# Step 3: Execute remote job
log_step "3/5" "Executing remote job..."
EXIT_CODE=0

if [[ "$USE_SLURM" == "true" ]]; then
    # Submit via SLURM with wait flag
    if ! ssh "${REMOTE_HOST}" "cd '${REMOTE_DIR}' && sbatch -W -J ${JOB_NAME} -p ${PARTITION} -N ${NODES} -n ${TASKS} ${REMOTE_CMD}"; then
        EXIT_CODE=$?
        log_error "SLURM job failed (exit code: ${EXIT_CODE})"
    fi
else
    # Direct execution (useful for testing without SLURM)
    if ! ssh "${REMOTE_HOST}" "cd '${REMOTE_DIR}' && ${REMOTE_CMD}"; then
        EXIT_CODE=$?
        log_error "Remote command failed (exit code: ${EXIT_CODE})"
    fi
fi

# Step 4: Sync results back (two passes to ensure file completeness)
log_step "4/5" "Syncing results (first pass)..."
# First pass: initial transfer (files may still be written)
# shellcheck disable=SC2086
rsync -avz $EXCLUDE_ARGS "${REMOTE_HOST}:${REMOTE_DIR}/" .

# Brief pause to allow files to stabilize
sleep 1

# Second pass: verify and finalize (ensures complete files)
log_step "4/5" "Syncing results (verification pass)..."
if [[ "$CLEANUP_REMOTE" == "true" ]]; then
    # Use --remove-source-files only on second pass after verification
    # shellcheck disable=SC2086
    rsync -avz --remove-source-files $EXCLUDE_ARGS "${REMOTE_HOST}:${REMOTE_DIR}/" .
else
    # Standard sync without cleanup
    # shellcheck disable=SC2086
    rsync -avz $EXCLUDE_ARGS "${REMOTE_HOST}:${REMOTE_DIR}/" .
fi

# Step 5: Cleanup handled by trap on exit
log_step "5/5" "Finalizing..."

echo "=============================================="
if [[ $EXIT_CODE -eq 0 ]]; then
    echo "Remote calculation completed successfully"
else
    echo "Remote calculation finished with errors (exit code: ${EXIT_CODE})"
fi
echo "=============================================="

exit $EXIT_CODE
