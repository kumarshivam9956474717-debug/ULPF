import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.utils.performance_benchmark import run_final_benchmark

if __name__ == "__main__":
    run_final_benchmark()

