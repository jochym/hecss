#!/bin/bash
# =============================================================================
# test-mock.sh - Pure local mock test (no SSH required)
# =============================================================================
# Tests the script logic by mocking ssh and rsync commands.
# This test does NOT require any network or SSH configuration.
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TEST_DIR=$(mktemp -d)
MOCK_REMOTE=$(mktemp -d)

echo "=============================================="
echo "Pure Mock Test for run-calc-ssh.sh"
echo "=============================================="
echo "Test directory:  ${TEST_DIR}"
echo "Mock remote dir: ${MOCK_REMOTE}"
echo "=============================================="

# Cleanup on exit
cleanup() {
    rm -rf "$TEST_DIR" "$MOCK_REMOTE"
    echo "Cleaned up test directories"
}
trap cleanup EXIT

# Create mock bin directory and add to PATH
MOCK_BIN="${TEST_DIR}/mock_bin"
mkdir -p "$MOCK_BIN"

# Create mock ssh command
cat > "${MOCK_BIN}/ssh" << 'EOFMOCK'
#!/bin/bash
# Mock SSH - executes commands locally
shift  # skip host argument
if [[ $# -gt 0 ]]; then
    # Execute the command locally
    eval "$@"
fi
EOFMOCK
chmod +x "${MOCK_BIN}/ssh"

# Create mock rsync command
cat > "${MOCK_BIN}/rsync" << EOFRSYNC
#!/bin/bash
# Mock rsync - use real rsync but locally
# Parse arguments to find source and dest
args=()
for arg in "\$@"; do
    # Remove any localhost: prefix
    arg=\${arg/localhost:/}
    args+=("\$arg")
done
/usr/bin/rsync "\${args[@]}"
EOFRSYNC
chmod +x "${MOCK_BIN}/rsync"

# Set up test environment
cd "$TEST_DIR"

# Create test input files
echo "test input content from POSCAR" > POSCAR
echo "INCAR settings" > INCAR
echo "POTCAR data" > POTCAR
echo "KPOINTS mesh" > KPOINTS

# Create mock job script (simulates VASP output)
cat > run-vasp-script << 'EOF'
#!/bin/bash
# Mock VASP execution
echo "Mock VASP started at $(date)" > OUTCAR
echo "Energy: -123.456 eV" >> OUTCAR
echo "Forces converged" >> OUTCAR
echo "Mock VASP completed" >> OUTCAR

# Create fake output files
cp POSCAR CONTCAR
echo "CHG data" > CHG
EOF
chmod +x run-vasp-script

# Create local config for test
cat > run-calc.conf << EOF
HECSS_REMOTE_HOST=localhost
HECSS_REMOTE_BASE=${MOCK_REMOTE}
HECSS_USE_SLURM=false
HECSS_REMOTE_CMD=./run-vasp-script
HECSS_INPUT_FILES="POSCAR INCAR POTCAR KPOINTS run-vasp-script"
HECSS_EXCLUDE_SYNC="WAVECAR CHGCAR"
EOF

echo ""
echo "Running run-calc-ssh.sh with mocked ssh/rsync..."
echo ""

# Run with mock commands in PATH
export PATH="${MOCK_BIN}:${PATH}"

if "${SCRIPT_DIR}/run-calc-ssh.sh"; then
    echo ""
    echo "Script completed. Checking results..."
    
    PASSED=0
    FAILED=0
    
    # Check expected output files
    for file in OUTCAR CONTCAR CHG; do
        if [[ -f "$file" ]]; then
            echo "✓ $file synced back"
            PASSED=$((PASSED + 1))
        else
            echo "✗ $file missing!"
            FAILED=$((FAILED + 1))
        fi
    done
    
    # Show OUTCAR contents
    if [[ -f OUTCAR ]]; then
        echo ""
        echo "--- OUTCAR contents ---"
        cat OUTCAR
        echo "--- end of OUTCAR ---"
    fi
    
    echo ""
    echo "=============================================="
    if [[ $FAILED -eq 0 ]]; then
        echo "TEST PASSED: All $PASSED checks successful"
    else
        echo "TEST FAILED: $FAILED checks failed, $PASSED passed"
        exit 1
    fi
    echo "=============================================="
else
    echo ""
    echo "=============================================="
    echo "TEST FAILED: Script returned non-zero exit"
    echo "=============================================="
    exit 1
fi
