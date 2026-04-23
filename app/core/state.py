# Глобальные переменные, которые не относятся к сессиям
from collections import defaultdict
import datetime

# transfer_cooldowns: user_uuid -> datetime последнего перевода
transfer_cooldowns: dict[str, datetime.datetime] = {}