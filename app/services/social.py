import database_social as social_db
from typing import Optional


def get_or_create_social_user(player_id: int, user_uuid: str, discord_id: str,
                              discord_username: str, discord_avatar: Optional[str],
                              game_nickname: str):
    """Создать или обновить пользователя соцсети."""
    return social_db.get_or_create_social_user(
        player_id=player_id,
        user_uuid=user_uuid,
        discord_id=discord_id,
        discord_username=discord_username,
        discord_avatar=discord_avatar,
        game_nickname=game_nickname
    )


def get_social_user_by_player_id(player_id: str):
    return social_db.get_social_user_by_player_id(player_id)


def update_social_user(player_id: str, bio: Optional[str] = None):
    return social_db.update_social_user(player_id, bio=bio)


def create_post(author_player_id: str, content: str, image_url: Optional[str] = None):
    return social_db.create_post(author_player_id, content, image_url)


def delete_post(post_id: int, player_id: str):
    return social_db.delete_post(post_id, player_id)


def toggle_like(post_id: int, player_id: str):
    return social_db.toggle_like(post_id, player_id)


def get_like_count(post_id: int):
    return social_db.get_like_count(post_id)


def add_comment(post_id: int, author_player_id: str, content: str):
    return social_db.add_comment(post_id, author_player_id, content)


def get_comments(post_id: int):
    return social_db.get_comments(post_id)


def delete_comment(comment_id: int, player_id: str):
    return social_db.delete_comment(comment_id, player_id)


def follow_user(follower_id: str, target_id: str):
    return social_db.follow_user(follower_id, target_id)


def unfollow_user(follower_id: str, target_id: str):
    return social_db.unfollow_user(follower_id, target_id)


def is_following(follower_id: str, target_id: str):
    return social_db.is_following(follower_id, target_id)


def get_follow_counts(player_id: str):
    return social_db.get_follow_counts(player_id)


def get_followers(player_id: str, limit: int = 20):
    return social_db.get_followers(player_id, limit)


def get_following(player_id: str, limit: int = 20):
    return social_db.get_following(player_id, limit)


def get_feed_posts(player_id: str, limit: int = 20, offset: int = 0):
    return social_db.get_feed_posts(player_id, limit, offset)


def get_user_posts(player_id: str, limit: int = 20, offset: int = 0):
    return social_db.get_user_posts(player_id, limit, offset)


def search_social_users(query: str, limit: int = 20):
    return social_db.search_social_users(query, limit)