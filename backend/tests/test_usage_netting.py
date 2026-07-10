"""Unit tests for billing usage netting and alert comparison."""

from backend.core.usage_tracker import _net_usage_from_entries
from backend.services.alert_engine import _compare
from backend.models.schemas import ModelAnalytics


def test_net_usage_diem_usd_and_bundled_credits():
    totals = _net_usage_from_entries(
        [
            {"currency": "DIEM", "amount": -2.5},
            {"currency": "USD", "amount": -1.0},
            {"currency": "BUNDLED_CREDITS", "amount": -3.0},
            {"currency": "VCU", "amount": -0.5},
            {"currency": "DIEM", "amount": 0.5},  # refund
        ]
    )
    assert totals["diem"] == 2.0
    assert totals["usd"] == 1.0
    assert totals["bundled_credits"] == 3.5


def test_net_usage_empty():
    assert _net_usage_from_entries([]) == {
        "diem": 0.0,
        "usd": 0.0,
        "bundled_credits": 0.0,
    }


def test_alert_compare_gte_lte():
    assert _compare(80, 75, "gte") is True
    assert _compare(70, 75, "gte") is False
    assert _compare(10, 25, "lte") is True
    assert _compare(30, 25, "lte") is False


def test_model_analytics_has_no_success_rate():
    assert "success_rate" not in ModelAnalytics.model_fields
