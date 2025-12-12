#!/bin/bash
# =============================================================================
# test-local.sh - Local mock test for run-calc-ssh.sh
# =============================================================================
# Tests the script flow using localhost as "remote" host.
# No SSH or rsync over network - just validates the logic.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR=$(mktemp -d)
REMOTE_BASE=$(mktemp -d)

echo "=============================================="
echo "Local Mock Test for run-calc-ssh.sh"
echo "=============================================="
echo "Test directory: ${TEST_DIR}"
echo "Mock remote:    ${REMOTE_BASE}"
echo "=============================================="

# Cleanup on exit
cleanup() {
    rm -rf "$TEST_DIR" "$REMOTE_BASE"
    echo "Cleaned up test directories"
}
trap cleanup EXIT

# Create test working directory
cd "$TEST_DIR"

# Create test input files
echo "test input content" > INPUT.txt
echo "another file" > DATA.txt

# Create mock job script (will be transferred and executed)
cat > mock-job.sh << 'EOF'
#!/bin/bash
# Mock job: concatenate inputs to output
cat INPUT.txt DATA.txt > OUTPUT.txt
echo "Mock job completed at $(date)" >> job.log
EOF
chmod +x mock-job.sh

# Create local config for test
cat > run-calc.conf << EOF
HECSS_REMOTE_HOST=localhost
HECSS_REMOTE_BASE=${REMOTE_BASE}
HECSS_USE_SLURM=false
HECSS_REMOTE_CMD=./mock-job.sh
HECSS_INPUT_FILES="INPUT.txt DATA.txt mock-job.sh"
HECSS_EXCLUDE_SYNC=""
EOF

echo ""
echo "Running run-calc-ssh.sh..."
echo ""

# Run the script
if "${SCRIPT_DIR}/run-calc-ssh.sh"; then
    echo ""
    echo "Script completed. Checking results..."
    
    # Verify output file exists
    if [[ -f OUTPUT.txt ]]; then
        echo "✓ OUTPUT.txt created"
        echo "  Contents: $(cat OUTPUT.txt)"
    else
        echo "✗ OUTPUT.txt missing!"
        exit 1
    fi
    
    # Verify job log
    if [[ -f job.log ]]; then
        echo "✓ job.log created"
    else
        echo "✗ job.log missing!"
        exit 1
    fi
    
    echo ""
    echo "=============================================="
    echo "TEST PASSED: All checks successful"
    echo "=============================================="
else
    echo ""
    echo "=============================================="
    echo "TEST FAILED: Script returned non-zero exit"
    echo "=============================================="
    exit 1
fi
