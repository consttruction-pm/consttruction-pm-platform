from decimal import Decimal, ROUND_HALF_UP


CENT = Decimal("0.01")


def money(value):
    return Decimal(value).quantize(CENT, rounding=ROUND_HALF_UP)


def test_revised_contract_value_excludes_pending_changes():
    original = Decimal("100000.00")
    approved_changes = [Decimal("1250.25"), Decimal("-300.00")]
    pending_changes = [Decimal("9000.00")]
    revised = money(original + sum(approved_changes, Decimal("0")))
    pending_exposure = money(sum(pending_changes, Decimal("0")))
    assert revised == Decimal("100950.25")
    assert pending_exposure == Decimal("9000.00")
    assert revised != money(revised + pending_exposure)


def test_current_net_certified_amount_uses_explicit_deductions():
    gross = Decimal("25000.00")
    retention = Decimal("1250.00")
    advance_recovery = Decimal("500.00")
    deductions = Decimal("125.00")
    tax = Decimal("0.00")
    assert money(gross - retention - advance_recovery - deductions + tax) == Decimal("23125.00")


def test_certified_not_paid_and_retention_outstanding():
    assert money(Decimal("45000.00") - Decimal("32000.00")) == Decimal("13000.00")
    assert money(Decimal("6000.00") - Decimal("1500.00")) == Decimal("4500.00")


def test_remaining_sov_and_forecast_are_distinct_from_approved_value():
    remaining_sov = money(Decimal("80000.00") - Decimal("32500.00"))
    forecast_final = money(Decimal("100000.00") + Decimal("7500.00"))
    assert remaining_sov == Decimal("47500.00")
    assert forecast_final == Decimal("107500.00")
