"""Financial primitives; the only bespoke calculations ERPNext lacks for worker-day contracting."""
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

PRECISION = Decimal("0.01")


def as_decimal(value):
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError("Amount must be numeric") from None
    if not number.is_finite():
        raise ValueError("Amount must be finite")
    return number


def money(value):
    return as_decimal(value).quantize(PRECISION, rounding=ROUND_HALF_UP)


def day_units(value):
    units = as_decimal(value)
    if units not in {Decimal("0"), Decimal("0.5"), Decimal("1")}:
        raise ValueError("Units must be 0, 0.5 or 1")
    return units


def daily_amounts(wage_rate, client_rate, units):
    """Returns wage earned and separately client-billable value for one worker-day."""
    units = day_units(units)
    wage = as_decimal(wage_rate)
    bill = as_decimal(client_rate)
    if wage < 0 or bill < 0:
        raise ValueError("Rates must be nonnegative")
    return money(wage * units), money(bill * units)


def project_gross_contribution(model, work_entries, milestone_amounts=()):
    """Operational figure before other project costs/taxes, NOT accounting net profit."""
    if model not in {"Daily", "Fixed"}:
        raise ValueError("Unknown billing model")
    labour = sum((money(row[0]) for row in work_entries), Decimal("0.00"))
    if model == "Daily":
        earned = sum((money(row[1]) for row in work_entries), Decimal("0.00"))
    else:
        earned = sum((money(m) for m in milestone_amounts), Decimal("0.00"))
    return {"earned_revenue":money(earned), "labour_cost":money(labour), "gross_contribution_before_other_costs":money(earned-labour)}
