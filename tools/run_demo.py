import sys
from pathlib import Path

# Add project root to sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from tools.run_evaluation import run_reproducible_evaluation, run_reproducible_demo, main

if __name__ == "__main__":
    main()

