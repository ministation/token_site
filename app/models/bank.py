from pydantic import BaseModel


class TransferRequest(BaseModel):
    receiver_nick: str
    amount: int


class AdminGiveRequest(BaseModel):
    target_nick: str
    amount: int
