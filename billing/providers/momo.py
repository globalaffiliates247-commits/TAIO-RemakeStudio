"""
MoMo Payment Provider
"""

from typing import Dict, Any


class MoMoPayment:
    @staticmethod
    def create_payment(phone: str, amount: int, order_info: str) -> Dict[str, Any]:
        return {
            "provider": "momo",
            "phone": phone,
            "amount": amount,
            "order_info": order_info,
            "qr_url": f"https://payment.momo.vn/pay?phone={phone}&amount={amount}&note={order_info}"
        }
