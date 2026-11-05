"""
International Card Payment Provider (Stripe / OnePay)
"""

from typing import Dict, Any


class CardPayment:
    @staticmethod
    def create_checkout_session(amount: int, currency: str = "vnd") -> Dict[str, Any]:
        return {
            "provider": "card",
            "amount": amount,
            "currency": currency,
            "checkout_url": "https://checkout.taio.club/pay"
        }
