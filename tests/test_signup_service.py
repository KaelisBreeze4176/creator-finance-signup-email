import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))

from src.signup_service import PaymentEvent, action_for_payment


def test_large_first_payment_requires_review():
    event = PaymentEvent("evt_9", "user_9", 100_000)
    assert action_for_payment(event) == "manual_review"


def test_small_payment_can_continue():
    event = PaymentEvent("evt_10", "user_10", 9_900)
    assert action_for_payment(event) == "allow"
