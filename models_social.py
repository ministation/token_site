from pydantic import BaseModel
from typing import Optional

class ProfileUpdate(BaseModel):
    bio: Optional[str] = None

class PostCreate(BaseModel):
    content: str

class PostResponse(BaseModel):
    id: int
    author_player_id: str
    author_nickname: str
    content: str
    image_url: Optional[str]
    like_count: int
    comment_count: int
    liked_by_me: bool
    created_at: str

class CommentCreate(BaseModel):
    content: str

class CommentResponse(BaseModel):
    id: int
    post_id: int
    author_player_id: str
    author_nickname: str
    author_avatar: Optional[str]
    content: str
    created_at: str