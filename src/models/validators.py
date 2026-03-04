"""Shared validation utilities for Pydantic models.

This module provides reusable validation functions to eliminate duplication
across model definitions and ensure consistent validation logic.
"""


def validate_csf_sku(sku: str) -> str:
    """Validate and normalize CSF part SKU format.

    Args:
        sku: Part SKU string to validate

    Returns:
        Normalized SKU (uppercase, stripped whitespace)

    Raises:
        ValueError: If SKU doesn't start with 'CSF-'

    Example:
        >>> validate_csf_sku("csf-3680")
        "CSF-3680"
        >>> validate_csf_sku("  CSF-10881  ")
        "CSF-10881"
        >>> validate_csf_sku("INVALID")
        ValueError: SKU must start with 'CSF-'
    """
    normalized = sku.upper().strip()
    if not normalized.startswith("CSF-"):
        msg = "SKU must start with 'CSF-'"
        raise ValueError(msg)
    return normalized


def normalize_text(text: str) -> str:
    """Normalize text by stripping whitespace and applying title case.

    Args:
        text: Text to normalize

    Returns:
        Normalized text with title case

    Example:
        >>> normalize_text("  honda civic  ")
        "Honda Civic"
        >>> normalize_text("RADIATORS")
        "Radiators"
    """
    return text.strip().title()
