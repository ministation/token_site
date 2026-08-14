"""Клиент API «Мой налог» (ЛКНПД) для выдачи чеков самозанятого.

Сейчас НЕ используется сайтом — авто-отправка в Мой налог отключена
(см. app/services/donation_receipts.py). Файл оставлен, чтобы быстро включить обратно.

Неофициальный REST API lknpd.nalog.ru — используйте на свой страх и риск,
всегда сверяйте чеки в кабинете https://lknpd.nalog.ru
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import aiohttp

from app.config import (
    NALOG_DEVICE_ID,
    NALOG_INN,
    NALOG_PASSWORD,
    NALOG_SESSION_FILE,
)

logger = logging.getLogger(__name__)

API_BASE = "https://lknpd.nalog.ru/api/v1"
MSK = timezone(timedelta(hours=3))


class MoyNalogError(Exception):
    def __init__(self, message: str, *, code: str | None = None, response: Any = None):
        super().__init__(message)
        self.message = message
        self.code = code
        self.response = response


def nalog_configured() -> bool:
    return bool((NALOG_INN or "").strip() and (NALOG_PASSWORD or "").strip())


def _device_id() -> str:
    raw = (NALOG_DEVICE_ID or "").strip()
    if raw:
        return raw
    # стабильный id на машине
    path = Path(NALOG_SESSION_FILE)
    sid_path = path.with_name("nalog_device_id.txt")
    try:
        if sid_path.is_file():
            val = sid_path.read_text(encoding="utf-8").strip()
            if val:
                return val
        val = uuid.uuid4().hex
        sid_path.parent.mkdir(parents=True, exist_ok=True)
        sid_path.write_text(val, encoding="utf-8")
        return val
    except Exception:
        return uuid.uuid4().hex


def _device_info() -> dict:
    return {
        "sourceDeviceId": _device_id(),
        "sourceType": "WEB",
        "appVersion": "1.0.0",
        "metaDetails": {
            "userAgent": "Mozilla/5.0 (compatible; MiniStation/1.0; +https://ministation.ru)",
        },
    }


def _msk_now_iso() -> str:
    return datetime.now(MSK).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+03:00"


def _load_session() -> dict:
    path = Path(NALOG_SESSION_FILE)
    if not path.is_file():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_session(data: dict) -> None:
    path = Path(NALOG_SESSION_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        os.chmod(path, 0o600)
    except Exception:
        pass


def receipt_print_url(inn: str, receipt_uuid: str) -> str:
    return f"{API_BASE}/receipt/{inn}/{receipt_uuid}/print"


def receipt_json_url(inn: str, receipt_uuid: str) -> str:
    return f"{API_BASE}/receipt/{inn}/{receipt_uuid}/json"


class MoyNalogClient:
    def __init__(self) -> None:
        self._session = _load_session()

    @property
    def inn(self) -> str:
        return str(self._session.get("inn") or NALOG_INN or "").strip()

    @property
    def access_token(self) -> str:
        return str(self._session.get("access_token") or "").strip()

    def is_token_fresh(self) -> bool:
        exp = self._session.get("expires_at")
        if not self.access_token or not exp:
            return False
        try:
            expires = datetime.fromisoformat(str(exp))
        except Exception:
            return False
        return datetime.now(timezone.utc) < expires - timedelta(minutes=2)

    async def ensure_auth(self) -> None:
        if self.is_token_fresh():
            return
        if self._session.get("refresh_token"):
            try:
                await self.refresh_token()
                if self.is_token_fresh():
                    return
            except Exception:
                logger.warning("Nalog refresh failed, re-login", exc_info=True)
        await self.login()

    async def login(self) -> dict:
        if not nalog_configured():
            raise MoyNalogError("NALOG_INN / NALOG_PASSWORD не заданы")
        payload = {
            "username": (NALOG_INN or "").strip(),
            "password": NALOG_PASSWORD,
            "deviceInfo": _device_info(),
        }
        last_err: Exception | None = None
        for path in ("/auth/lkfl", "/auth/lkfl/login"):
            try:
                data = await self._request(
                    "POST",
                    path,
                    json_body=payload,
                    auth=False,
                )
                return self._apply_auth_response(data)
            except MoyNalogError as e:
                last_err = e
                if e.code not in ("404", "405"):
                    raise
        if last_err:
            raise last_err
        raise MoyNalogError("Не удалось войти в Мой налог")

    async def refresh_token(self) -> dict:
        refresh = self._session.get("refresh_token")
        if not refresh:
            raise MoyNalogError("Нет refresh_token")
        data = await self._request(
            "POST",
            "/auth/token",
            json_body={"refreshToken": refresh, "deviceInfo": _device_info()},
            auth=False,
        )
        return self._apply_auth_response(data)

    def _apply_auth_response(self, data: dict) -> dict:
        if not isinstance(data, dict):
            raise MoyNalogError("Некорректный ответ авторизации", response=data)
        token = data.get("token") or data.get("accessToken")
        refresh = data.get("refreshToken")
        if not token:
            msg = (
                (data.get("message") if isinstance(data.get("message"), str) else None)
                or "Не удалось войти в Мой налог"
            )
            raise MoyNalogError(msg, response=data)
        expire_in = int(data.get("tokenExpireIn") or data.get("expireIn") or 3600)
        profile = data.get("profile") or {}
        inn = str(profile.get("inn") or NALOG_INN or "").strip()
        self._session = {
            "access_token": token,
            "refresh_token": refresh or self._session.get("refresh_token"),
            "inn": inn,
            "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=expire_in)).isoformat(),
            "display_name": profile.get("displayName") or profile.get("fio") or "",
        }
        _save_session(self._session)
        return self._session

    async def create_income(
        self,
        *,
        name: str,
        amount_rub: float,
        operation_time: datetime | None = None,
    ) -> dict:
        await self.ensure_auth()
        amount = round(float(amount_rub), 2)
        if amount <= 0:
            raise MoyNalogError("Сумма чека должна быть > 0")
        op = operation_time.astimezone(MSK) if operation_time else datetime.now(MSK)
        op_iso = op.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+03:00"
        req_iso = _msk_now_iso()
        body = {
            "operationTime": op_iso,
            "requestTime": req_iso,
            "services": [
                {
                    "name": (name or "Услуга")[:256],
                    "amount": amount,
                    "quantity": 1,
                }
            ],
            "totalAmount": f"{amount:.2f}",
            "client": {
                "contactPhone": None,
                "displayName": None,
                "inn": None,
                "incomeType": "FROM_INDIVIDUAL",
            },
            "paymentType": "CASH",
            "ignoreMaxTotalIncomeRestriction": False,
        }
        data = await self._request("POST", "/income", json_body=body, auth=True)
        receipt_uuid = ""
        if isinstance(data, dict):
            receipt_uuid = str(
                data.get("approvedReceiptUuid")
                or data.get("receiptUuid")
                or data.get("uuid")
                or ""
            ).strip()
        if not receipt_uuid:
            raise MoyNalogError(
                "Мой налог не вернул UUID чека",
                response=data,
            )
        inn = self.inn
        return {
            "uuid": receipt_uuid,
            "inn": inn,
            "amount": amount,
            "print_url": receipt_print_url(inn, receipt_uuid),
            "json_url": receipt_json_url(inn, receipt_uuid),
            "raw": data,
        }

    async def download_receipt_print(self, receipt_uuid: str) -> tuple[bytes, str]:
        """Скачивает печатную форму чека. Возвращает (bytes, content_type)."""
        await self.ensure_auth()
        inn = self.inn
        if not inn or not receipt_uuid:
            raise MoyNalogError("Нет ИНН или UUID чека для скачивания")
        url = receipt_print_url(inn, receipt_uuid)
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Accept": "*/*",
            "User-Agent": "Mozilla/5.0 (compatible; MiniStation/1.0)",
        }
        timeout = aiohttp.ClientTimeout(total=45)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, headers=headers) as resp:
                raw = await resp.read()
                ctype = (resp.headers.get("Content-Type") or "application/octet-stream").split(";")[0].strip()
                if resp.status >= 400 or not raw:
                    raise MoyNalogError(
                        f"Не удалось скачать чек ({resp.status})",
                        code=str(resp.status),
                    )
                return raw, ctype

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict | None = None,
        auth: bool = True,
    ) -> Any:
        url = f"{API_BASE}{path}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (compatible; MiniStation/1.0)",
        }
        if auth:
            if not self.access_token:
                raise MoyNalogError("Нет access token")
            headers["Authorization"] = f"Bearer {self.access_token}"

        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.request(method, url, json=json_body, headers=headers) as resp:
                text = await resp.text()
                try:
                    data = json.loads(text) if text else {}
                except Exception:
                    data = {"raw": text[:500]}
                if resp.status >= 400:
                    msg = None
                    if isinstance(data, dict):
                        msg = data.get("message") or data.get("error")
                        if isinstance(msg, dict):
                            msg = msg.get("message") or str(msg)
                    raise MoyNalogError(
                        str(msg or f"HTTP {resp.status}"),
                        code=str(resp.status),
                        response=data,
                    )
                return data
