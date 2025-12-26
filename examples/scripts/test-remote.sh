#!/bin/bash
# =============================================================================
# test-remote.sh - Remote test for run-calc-ssh.sh (rsync/ssh, no SLURM)
# =============================================================================
# Tests the full remote workflow using actual SSH and rsync.
# Requires SSH access to the configured remote host.
#
# Usage: ./test-remote.sh [remote_host] [remote_base]
#
# If not provided, reads from environment or defaults to localhost.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR=$(mktemp -d)

# Remote configuration (can be overridden by arguments)
REMOTE_HOST="${1:-${HECSS_REMOTE_HOST:-localhost}}"
REMOTE_BASE="${2:-${HECSS_REMOTE_BASE:-/tmp/hecss_test_$$}}"

echo "=============================================="
echo "Remote Test for run-calc-ssh.sh"
echo "=============================================="
echo "Local test dir: ${TEST_DIR}"
echo "Remote host:    ${REMOTE_HOST}"
echo "Remote base:    ${REMOTE_BASE}"
echo "=============================================="

# Cleanup on exit
cleanup() {
    rm -rf "$TEST_DIR"
    # Try to clean up remote directory
    ssh "${REMOTE_HOST}" "rm -rf '${REMOTE_BASE}'" 2>/dev/null || true
    echo "Cleaned up test directories"
}
trap cleanup EXIT

# Test SSH connectivity first
echo ""
echo "Testing SSH connection to ${REMOTE_HOST}..."
if ! ssh -o ConnectTimeout=5 "${REMOTE_HOST}" "echo 'SSH connection OK'"; then
    echo "ERROR: Cannot connect to ${REMOTE_HOST} via SSH"
    echo "Please ensure:"
    echo "  1. SSH is configured for passwordless access"
    echo "  2. Host alias exists in ~/.ssh/config or use user@hostname"
    exit 1
fi

# Create test working directory
cd "$TEST_DIR"

# Create test input files
echo "Hello from local machine" > INPUT.txt
echo "Data file contents: $(date)" > DATA.txt

# Create job script to be executed remotely
cat > remote-job.sh << 'EOF'
#!/bin/bash
# This script runs on the remote machine
echo "Running on: $(hostname)" > OUTPUT.txt
echo "Working dir: $(pwd)" >> OUTPUT.txt
echo "Input contents:" >> OUTPUT.txt
cat INPUT.txt >> OUTPUT.txt
cat DATA.txt >> OUTPUT.txt
echo "Completed at: $(date)" >> OUTPUT.txt
EOF
chmod +x remote-job.sh

# Create local config for test
cat > run-calc.conf << EOF
HECSS_REMOTE_HOST=${REMOTE_HOST}
HECSS_REMOTE_BASE=${REMOTE_BASE}
HECSS_USE_SLURM=false
HECSS_REMOTE_CMD=./remote-job.sh
HECSS_INPUT_FILES="INPUT.txt DATA.txt remote-job.sh"
HECSS_EXCLUDE_SYNC=""
EOF

echo ""
echo "Running run-calc-ssh.sh with real SSH/rsync..."
echo ""

# Run the script
if "${SCRIPT_DIR}/run-calc-ssh.sh"; then
    echo ""
    echo "Script completed. Checking results..."
    
    # Verify output file was synced back
    if [[ -f OUTPUT.txt ]]; then
        echo "✓ OUTPUT.txt synced back"
        echo ""
        echo "--- OUTPUT.txt contents ---"
        cat OUTPUT.txt
        echo "--- end of OUTPUT.txt ---"
    else
        echo "✗ OUTPUT.txt missing! Remote sync failed."
        exit 1
    fi
    
    echo ""
    echo "=============================================="
    echo "REMOTE TEST PASSED"
    echo "=============================================="
else
    echo ""
    echo "=============================================="
    echo "REMOTE TEST FAILED: Script returned non-zero"
    echo "=============================================="
    exit 1
fi
