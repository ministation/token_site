from pydantic import BaseModel
from typing import Optional

class ProfileUpdate(BaseModel):
    bio: Optional[str] = None

class PostCreate(BaseModel):
    content: str

class CommentCreate(BaseModel):
    content: str

class PrivateMessageRequest(BaseModel):
    receiver_player_id: str
    message: str