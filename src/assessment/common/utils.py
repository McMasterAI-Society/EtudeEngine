"""Small shared helpers."""
import math
import statistics


def number(value):
    """Parse a CSV cell to a finite float, or None."""
    if value is None or value == '':
        return None
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def median(values):
    """Median, or None for an empty list."""
    return statistics.median(values) if values else None
