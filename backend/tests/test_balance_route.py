from backend.api.routes.balance import _balance_amount


def test_balance_amount_reads_documented_lowercase_fields() -> None:
    assert _balance_amount({"diem": 12.5}, "diem", 0.0) == 12.5


def test_balance_amount_falls_back_for_explicit_null() -> None:
    assert _balance_amount({"diem": None}, "diem", 3.0) == 3.0


def test_balance_amount_supports_rate_limit_uppercase_fields() -> None:
    assert _balance_amount({"USD": 7.0}, "usd", 0.0) == 7.0


def test_balance_amount_reads_credit_balance_camel_case() -> None:
    balances = {"bundledCredits": 4.5, "earnedCredits": 2.25}
    assert _balance_amount(balances, "bundledCredits", 0.0) == 4.5
    assert _balance_amount(balances, "earnedCredits", 0.0) == 2.25