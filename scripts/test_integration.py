import os
import shutil
import subprocess
from hecss.cli import hecss_sampler
from click.testing import CliRunner

def test_integration():
    """
    Runs a partial hecss_sampler workflow using mock_vasp.sh.
    """
    runner = CliRunner()
    
    # Setup test directory
    test_dir = "integration_test_workdir"
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir)
    os.makedirs(test_dir)
    
    # We need a dummy POSCAR and POTCAR
    with open(os.path.join(test_dir, "POSCAR"), "w") as f:
        f.write("Mock POSCAR\n1.0\n10 0 0\n0 10 0\n0 0 10\nSi\n1\nCartesian\n0 0 0\n")
    with open(os.path.join(test_dir, "POTCAR"), "w") as f:
        f.write("Mock POTCAR")
    with open(os.path.join(test_dir, "INCAR"), "w") as f:
        f.write("Mock INCAR")
    with open(os.path.join(test_dir, "KPOINTS"), "w") as f:
        f.write("Mock KPOINTS")

    mock_script = os.path.abspath("mock_vasp.sh")
    
    # Argument list for hecss_sampler
    # --calc VASP (default)
    # --command "bash mock_vasp.sh"
    # --nsamples 1 (just one to test loop)
    # --nwork 1 (serial)
    # --nodfset (skip alamode dependency for this test if possible, or create dummy force constants?)
    # Wait, hecss_sampler generation usually needs alamode for displacement generation if T > 0?
    # Or force constants. 
    # Let's try to run it. If it fails on missing FC2, we'll need to mock that too.
    
    # Create WORK directory which is default expected by strict Click type check if not passed, 
    # or pass explicit existing directory.
    work_dir = os.path.join(test_dir, "WORK")
    os.makedirs(work_dir)

    print(f"Running integration test in {test_dir} with command {mock_script}")
    
    # We execute inside the test_dir so hecss finds POSCAR
    current_dir = os.getcwd()
    os.chdir(test_dir)
    
    try:
        # We invoke the command line interface programmatically
        # We need to supply input directory (context of POSCAR) as argument ".". 
        # And we point --workdir to our created WORK dir.
        
        result = runner.invoke(hecss_sampler, [
            ".", 
            "--workdir", "WORK",
            "--command", f"bash {mock_script}",
            "--nsamples", "1",
            "--nwork", "1",
            "--nodfset" # We skip ALAMODE DFSET generation, but hecss should still run the calc loop
        ])
        
        print("Exit Code:", result.exit_code)
        
        if result.exit_code != 0:
            print("Output:", result.output)
            print("Integration test FAILED (Non-zero exit).")
            # Print traceback
            if result.exc_info:
                import traceback
                traceback.print_exception(*result.exc_info)
        else:
            # Verify if it actually ran something
            # Check for sample directory in WORK/T_300.0K/sample_00000
            expected_sample_dir = os.path.join("WORK", "T_300.0K", "sample_00000")
            if os.path.exists(expected_sample_dir):
                print(f"SUCCESS: Sample directory created at {expected_sample_dir}")
                # Check for OUTCAR (proof that mock ran)
                if os.path.exists(os.path.join(expected_sample_dir, "OUTCAR")):
                     print("SUCCESS: Mock code executed (OUTCAR found).")
                     print("Integration test PASSED.")
                else:
                     print("FAILURE: OUTCAR not found in sample directory.")
            else:
                print(f"FAILURE: Sample directory {expected_sample_dir} not found.")
                print(f"Directory listing of WORK/T_300.0K: ")
                if os.path.exists(os.path.join("WORK", "T_300.0K")):
                    print(os.listdir(os.path.join("WORK", "T_300.0K")))
                else:
                    print("Structure T_300.0K not found.")
                print("Output:", result.output)
            
    finally:
        os.chdir(current_dir)

if __name__ == "__main__":
    test_integration()
