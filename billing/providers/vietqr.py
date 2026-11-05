"""
VietQR Payment Integration
Tạo mã QR thanh toán ngân hàng NAPAS 24/7 tự động xác nhận theo số phút.
"""

from typing import Dict, Any


class VietQRPayment:
    @staticmethod
    def create_payment_qr(bank_id: str, account_no: str, account_name: str, amount: int, order_info: str) -> Dict[str, Any]:
        # Tạo URL VietQR chuẩn
        qr_url = f"https://img.vietqr.io/image/{bank_id}-{account_no}-compact2.png?amount={amount}&addInfo={order_info}&accountName={account_name}"
        return {
            "provider": "vietqr",
            "qr_image_url": qr_url,
            "amount": amount,
            "order_info": order_info,
            "bank_id": bank_id,
            "account_no": account_no,
            "account_name": account_name
        }
