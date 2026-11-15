"""Shared display formatting for readability metric values.

Builder's readability metrics panel formats values in the browser with
``Intl.NumberFormat(undefined, {maximumFractionDigits: 2})``. That rounds the
number's shortest decimal form (what JavaScript prints, so 13.495 stays
13.495) half away from zero, keeps thousands separators, and drops trailing
zeros. Server-rendered views use this helper so the Readability
Checker and saved snapshots show the same digits as the panel.
"""

from decimal import ROUND_HALF_UP, Decimal

_HUNDREDTH = Decimal("0.01")


def format_metric_number(value):
    """Format a finite number like the panel: up to 2 decimal places."""

    # repr() gives the same shortest round-trip digits JavaScript uses, so
    # ties such as 13.495 or 2.675 round up exactly as the panel does.
    rounded = Decimal(repr(float(value))).quantize(_HUNDREDTH, rounding=ROUND_HALF_UP)
    text = f"{rounded:,.2f}"
    return text.rstrip("0").rstrip(".")
