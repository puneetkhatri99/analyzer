def quantile(sorted_values: list[float], q: float) -> float | None:
    """Linear-interpolated quantile of an already sorted list; None when it is empty."""
    if not sorted_values:
        return None
    pos = (len(sorted_values) - 1) * q
    lo = int(pos)
    hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)
