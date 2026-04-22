from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProfileUpdate(BaseModel):
    bio: Optional[str] = None

class PostCreate(BaseModel):
    content: str

class CommentCreate(BaseModel):
    content: str

class PrivateMessageRequest(BaseModel):
    receiver_player_id: str
    message: str

class SocialUserProfile(BaseModel):
    player_id: str
    game_nickname: str
    discord_username: str
    discord_avatar: Optional[str]
    bio: str
    following_count: int
    followers_count: int
    is_following: bool = False
    created_at: Optional[datetime]