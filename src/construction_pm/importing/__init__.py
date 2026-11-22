"""Reference-project workbook import, source stage.

This package turns the operator's workbook into a validated, canonical dataset.
It deliberately stops before persistence: writing goes through the same project,
activity, relationship and resource services the product uses, so the workbook
can never become a second source of truth or a parallel calculation path.
"""

from .reference_projects import (
    CONTRACT_VERSION,
    build_report,
    ImportIssue,
    ImportReport,
    ReferenceDataset,
    Sheet,
    load_dataset,
    read_workbook,
    validate_dataset,
)

__all__ = [
    "CONTRACT_VERSION",
    "build_report",
    "ImportIssue",
    "ImportReport",
    "ReferenceDataset",
    "Sheet",
    "load_dataset",
    "read_workbook",
    "validate_dataset",
]
