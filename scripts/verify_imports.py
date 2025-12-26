import sys
import os

try:
    print("Importing hecss.core...")
    import hecss.core
    print("Importing hecss.cli...")
    import hecss.cli
    print("Importing hecss.util...")
    import hecss.util
    print("Importing hecss.optimize...")
    import hecss.optimize
    print("Importing hecss.monitor...")
    import hecss.monitor
    print("Importing hecss.planner...")
    import hecss.planner
    print("\nSUCCESS: All modules imported without error.")
except ImportError as e:
    print(f"\nFAILURE: ImportError: {e}")
    sys.exit(1)
except Exception as e:
    print(f"\nFAILURE: Unexpected error: {e}")
    sys.exit(1)
