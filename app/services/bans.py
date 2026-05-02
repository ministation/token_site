from app.db.database import get_pg_pool

ROLE_TRANSLATIONS = {
    'Paramedic': 'Парамедик', 'ChiefMedicalOfficer': 'Главный врач', 'Psychologist': 'Психолог',
    'MedicalDoctor': 'Врач', 'Chemist': 'Химик', 'MedicalIntern': 'Медицинский интерн',
    'Surgeon': 'Хирург', 'Virologist': 'Вирусолог',
    'ChiefEngineer': 'Старший инженер', 'StationEngineer': 'Инженер станции',
    'TechnicalAssistant': 'Технический ассистент', 'AtmosphericTechnician': 'Атмосферный техник',
    'HeadOfSecurity': 'Глава службы безопасности', 'Pilot': 'Пилот',
    'Detective': 'Детектив', 'Brigmedic': 'Бригмедик', 'SecurityOfficer': 'Офицер безопасности',
    'SecurityCadet': 'Кадет безопасности', 'Warden': 'Смотритель', 'CBURN': 'РХБЗЗ',
    'Captain': 'Капитан', 'BlueshieldOfficer': 'ОСЩ', 'CommandMaid': 'Командная горничная',
    'CentralCommandOfficial': 'Представитель ЦентКома', 'NanotrasenRepresentative': 'Представитель НаноТрейзен',
    'DeathSquad': 'Эскадрон смерти', 'ERTLeader': 'Лидер ОБР', 'ERTEngineer': 'Инженер ОБР',
    'ERTMedical': 'Медик ОБР', 'ERTChaplain': 'Священник ОБР', 'ERTSecurity': 'Офицер безопасности ОБР',
    'ERTJanitor': 'Уборщик ОБР', 'HecuOperative': 'Оперативник ХЕКУ',
    'Quartermaster': 'Квартирмейстер', 'HeadOfPersonnel': 'Глава персонала',
    'ResearchDirector': 'Директор исследований', 'Scientist': 'Ученый',
    'ResearchAssistant': 'Лаборант', 'Roboticist': 'Робототехник',
    'Botanist': 'Ботаник', 'Bartender': 'Бармен', 'Clown': 'Клоун',
    'Chef': 'Шеф-повар', 'Janitor': 'Уборщик', 'Lawyer': 'Юрист',
    'Librarian': 'Библиотекарь', 'Visitor': 'Посетитель', 'ServiceWorker': 'Работник сервиса',
    'Zookeeper': 'Смотритель зоопарка', 'Musician': 'Музыкант', 'Chaplain': 'Священник',
    'Mime': 'Мим', 'Passenger': 'Пассажир', 'CargoTechnician': 'Карго-техник',
    'Reporter': 'Репортер', 'SalvageSpecialist': 'Спасатель',
    'Boxer': 'Боксер', 'RadioHost': 'Радиоведущий', 'Diplomat': 'Дипломат',
    'GovernmentMan': 'Правительственный агент', 'SpecialOperationsOfficer': 'Офицер спецопераций',
    'NavyOfficerUndercover': 'Офицер флота под прикрытием', 'NavyCaptain': 'Капитан флота',
    'NavyOfficer': 'Офицер флота', 'NanotrasenCareerTrainer': 'Инструктор НаноТрейзен',
    'PartyMaker': 'Организатор вечеринок', 'SecurityClown': 'Клоун безопасности',
}


def translate_role(role: str) -> str:
    if role.startswith("Job:"):
        role = role[4:]
    return ROLE_TRANSLATIONS.get(role, role)


async def get_all_bans(limit: int = 50, offset: int = 0):
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                b.ban_id, b.type, b.ban_time, b.expiration_time, b.reason,
                b.banning_admin,
                p_admin.last_seen_user_name as admin_name,
                COALESCE(bp_agg.players, ARRAY[]::text[]) as player_ids,
                COALESCE(br_agg.roles, ARRAY[]::text[]) as roles,
                COALESCE(brnd_agg.rounds, ARRAY[]::integer[]) as rounds
            FROM ban b
            LEFT JOIN player p_admin ON b.banning_admin = p_admin.user_id
            LEFT JOIN LATERAL (
                SELECT ARRAY_AGG(bp.user_id::text) as players
                FROM ban_player bp WHERE bp.ban_id = b.ban_id
            ) bp_agg ON true
            LEFT JOIN LATERAL (
                SELECT ARRAY_AGG(br.role_id) as roles
                FROM ban_role br WHERE br.ban_id = b.ban_id
            ) br_agg ON true
            LEFT JOIN LATERAL (
                SELECT ARRAY_AGG(brn.round_id) as rounds
                FROM ban_round brn WHERE brn.ban_id = b.ban_id
            ) brnd_agg ON true
            ORDER BY b.ban_time DESC
            LIMIT $1 OFFSET $2
        """, limit, offset)
        
        bans = []
        for row in rows:
            # Получаем имена игроков
            player_names = []
            for pid in (row["player_ids"] or []):
                p = await conn.fetchrow(
                    "SELECT last_seen_user_name FROM player WHERE user_id::text = $1", pid
                )
                player_names.append(p["last_seen_user_name"] if p else pid[:8]+"...")
            
            bans.append({
                "ban_id": row["ban_id"],
                "type": row["type"],
                "ban_time": row["ban_time"].isoformat() if row["ban_time"] else None,
                "expiration_time": row["expiration_time"].isoformat() if row["expiration_time"] else None,
                "reason": row["reason"] or "Не указана",
                "admin_name": row["admin_name"] or "Неизвестный",
                "player_names": player_names,
                "roles": [translate_role(r) for r in (row["roles"] or [])],
                "rounds": row["rounds"] or []
            })
        return bans


async def get_player_bans(player_uuid: str, limit: int = 50):
    pg = await get_pg_pool()
    async with pg.acquire() as conn:
        rows = await conn.fetch("""
            SELECT 
                b.ban_id, b.type, b.ban_time, b.expiration_time, b.reason,
                p_admin.last_seen_user_name as admin_name
            FROM ban b
            JOIN ban_player bp ON b.ban_id = bp.ban_id
            LEFT JOIN player p_admin ON b.banning_admin = p_admin.user_id
            WHERE bp.user_id::text = $1
            ORDER BY b.ban_time DESC
            LIMIT $2
        """, str(player_uuid), int(limit))
        
        return [{
            "ban_id": row["ban_id"],
            "type": row["type"],
            "ban_time": row["ban_time"].isoformat() if row["ban_time"] else None,
            "expiration_time": row["expiration_time"].isoformat() if row["expiration_time"] else None,
            "reason": row["reason"] or "Не указана",
            "admin_name": row["admin_name"] or "Неизвестный",
        } for row in rows]