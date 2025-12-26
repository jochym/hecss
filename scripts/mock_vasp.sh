#!/bin/bash
# Mock VASP script
# Simulates a successful run by creating dummy output files.

echo "MOCK VASP: Running in $(pwd)"
echo "MOCK VASP: Job Name: $1"

# Simulate some "work"
sleep 1

# Create dummy OUTCAR
cat <<EOF > OUTCAR
  General timing and accounting informations for this job:
  ========================================================
  
  Total CPU time used (sec):        1.000
  User time (sec):                  1.000
  System time (sec):                0.000
  Elapsed time (sec):               1.000
  
  Free energy of the ion-electron system (eV)
  ---------------------------------------------------
  alpha Z        PSCENC =        0.00000000
  EENTRO         =        0.00000000
  -EBGOCC        =        0.00000000
  ---------------------------------------------------
  free  energy   TOTEN  =      -100.12345678 eV

  Energy without entropy=      -100.12345678  energy(sigma->0) =      -100.12345678
EOF

# Create dummy vasprun.xml (minimal valid structure if needed)
# For now, assuming OUTCAR is enough for basic energy parsing. 
# If hecss reads vasprun.xml, we'll need to improve this.
touch vasprun.xml
touch OSZICAR

echo "MOCK VASP: Finished successfully."
exit 0
