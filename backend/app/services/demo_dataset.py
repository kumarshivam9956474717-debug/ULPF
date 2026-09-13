"""
Backward compatibility alias for evaluation_dataset.py.
"""
from app.services.evaluation_dataset import (
    DemoDatasetGenerator,
    EvaluationDatasetGenerator,
)

__all__ = ["DemoDatasetGenerator", "EvaluationDatasetGenerator"]
