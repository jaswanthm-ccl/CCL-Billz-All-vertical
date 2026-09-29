"""Structured typed models and return objects for Crystal Billz UI and API operations."""

from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PurchaseResult:
    """Represents the structured result of a created Purchase record."""
    reference_no: str
    supplier_name: str
    branch_name: str
    total_amount: Decimal = Decimal("0.00")
    paid_amount: Decimal = Decimal("0.00")
    purchase_type: str = "Credit"
    purchase_id: str | None = None


@dataclass(frozen=True)
class SaleResult:
    """Represents the structured result of a created Sale / Order invoice."""
    invoice_no: str
    customer_name: str
    branch_name: str
    total_amount: Decimal = Decimal("0.00")
    paid_amount: Decimal = Decimal("0.00")
    payment_method: str = "Cash"
    sale_id: str | None = None


@dataclass(frozen=True)
class VoucherResult:
    """Represents the structured result of a created Accounting Voucher."""
    voucher_no: str
    voucher_type: str
    amount: Decimal
    debit_ledger: str
    credit_ledger: str
    branch_name: str | None = None
    voucher_id: str | None = None


@dataclass(frozen=True)
class StockTransferResult:
    """Represents the structured result of an Inter-Branch Stock Transfer."""
    transfer_no: str
    source_branch: str
    destination_branch: str
    quantity: Decimal = Decimal("0")
    remarks: str | None = None
    transfer_id: str | None = None


@dataclass(frozen=True)
class ReturnResult:
    """Represents the structured result of a Purchase Return or Sale Return."""
    return_no: str
    original_reference: str
    return_type: str
    total_amount: Decimal = Decimal("0.00")
    party_name: str | None = None
    return_id: str | None = None
