from pydantic import BaseModel
from typing import Optional


class TransferRequest(BaseModel):
    receiver_nick: str
    amount: int


class DepositRequest(BaseModel):
    amount: int


class LoanRequest(BaseModel):
    amount: int


class WithdrawRequest(BaseModel):
    deposit_id: int


class RepayRequest(BaseModel):
    loan_id: int
    amount: Optional[int] = None


class AdminGiveRequest(BaseModel):
    target_nick: str
    amount: int