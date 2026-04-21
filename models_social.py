from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

# ---------- Соцсеть ----------
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

class PostCreate(BaseModel):
    content: str
    image_url: Optional[str] = None

class PostResponse(BaseModel):
    id: int
    author_player_id: str
    author_nickname: str
    author_discord_username: str
    author_avatar: Optional[str]
    content: str
    image_url: Optional[str]
    like_count: int
    comment_count: int
    liked_by_me: bool
    created_at: datetime

class CommentCreate(BaseModel):
    content: str

class CommentResponse(BaseModel):
    id: int
    post_id: int
    author_player_id: str
    author_nickname: str
    author_avatar: Optional[str]
    content: str
    created_at: datetime

class FollowResponse(BaseModel):
    following: bool

class ProfileUpdate(BaseModel):
    bio: Optional[str] = None