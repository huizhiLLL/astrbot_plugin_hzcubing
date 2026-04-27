import asyncio
import time
from decimal import Decimal, ROUND_DOWN
from typing import Any

import aiohttp
from astrbot.api import logger

# API 配置
API_BASE_URL = "https://api.hzcubing.club/api"
REQUEST_TIMEOUT = 10

# 官方项目顺序列表（用于排序）
OFFICIAL_EVENT_ORDER = [
    "333", "222", "333oh", "444", "555", "666", "777",
    "py", "sk", "sq1", "clock", "meg", "333bf", "444bf",
    "555bf", "333mbf", "333fm", "fto",
]

OFFICIAL_EVENT_CODES = set(OFFICIAL_EVENT_ORDER)

EVENT_NAME_MAP = {
    "三阶速拧": "333", "三阶": "333", "333": "333", "三速": "333",
    "二阶速拧": "222", "二阶": "222", "222": "222", "二速": "222",
    "三阶单手": "333oh", "单手": "333oh", "333oh": "333oh", "三单": "333oh",
    "四阶速拧": "444", "四阶": "444", "444": "444", "四速": "444",
    "五阶速拧": "555", "五阶": "555", "555": "555", "五速": "555",
    "六阶速拧": "666", "六阶": "666", "666": "666", "六速": "666",
    "七阶速拧": "777", "七阶": "777", "777": "777", "七速": "777",
    "五魔方": "meg", "meg": "meg", "五魔": "meg",
    "三阶盲拧": "333bf", "333bf": "333bf", "三盲": "333bf",
    "四阶盲拧": "444bf", "444bf": "444bf", "四盲": "444bf",
    "五阶盲拧": "555bf", "555bf": "555bf", "五盲": "555bf",
    "最少步": "333fm", "333fm": "333fm",
    "金字塔": "py", "py": "py", "塔": "py",
    "斜转": "sk", "sk": "sk", "斜": "sk",
    "SQ1": "sq1", "sq1": "sq1",
    "魔表": "clock", "clock": "clock", "表": "clock",
    "多盲": "333mbf", "333mbf": "333mbf",
    "FTO": "fto", "fto": "fto",
}

# 保留少量静态额外项目名，同时支持从后端动态拉取整活项目
EXTRA_EVENT_NAMES = {
    "二阶镜面", "三阶镜面", "四阶镜面", "五阶镜面", "二阶FTO", "齿轮",
    "四阶华容道", "正阶连拧(2-7)", "异形连拧(5个)", "全项目连拧(12个)",
    "枫叶", "CTO", "REDI", "二重奏", "八阶速拧", "九阶速拧", "十阶速拧", "十一阶速拧",
}


def format_time_seconds(time_seconds: float | int | None) -> str:
    if time_seconds is None:
        return "-"
    try:
        d = Decimal(str(time_seconds))
        if d <= 0:
            return "-"
        d = d.quantize(Decimal("0.00"), rounding=ROUND_DOWN)
        centis = int((d * 100).to_integral_exact(rounding=ROUND_DOWN))
        if centis <= 0:
            return "-"
        minutes = centis // 6000
        rem_centis = centis - minutes * 6000
        seconds_int = rem_centis // 100
        centi = rem_centis % 100
        if minutes > 0:
            return f"{minutes}:{seconds_int:02d}.{centi:02d}"
        return f"{seconds_int}.{centi:02d}"
    except Exception:
        return "-"


def normalize_event_code(event: str) -> str | None:
    event = event.strip()
    if not event:
        return None
    if event in OFFICIAL_EVENT_CODES:
        return event
    return None


def normalize_meme_event_input(event: str | None) -> str:
    if not event:
        return ""
    return "".join(str(event).strip().split())


def parse_time_to_seconds(value: str | float | int | None) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if value >= 0 else None

    raw = str(value).strip()
    if not raw or raw == "-":
        return None
    upper = raw.upper()
    if upper in {"DNF", "DNS"}:
        return None

    try:
        parts = upper.split(":")
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        return float(upper)
    except Exception:
        return None


class APIClient:
    def __init__(self, base_url: str = API_BASE_URL, timeout: int = REQUEST_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: aiohttp.ClientSession | None = None

    async def _ensure_session(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self.session

    async def _request(
        self,
        method: str,
        endpoint: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        session = await self._ensure_session()
        url = f"{self.base_url}{endpoint}"
        try:
            if method.upper() == "GET":
                async with session.get(url, params=params or {}) as response:
                    return await response.json(content_type=None)
            if method.upper() == "POST":
                async with session.post(url, json=data or {}) as response:
                    return await response.json(content_type=None)
            return {"code": 500, "message": "Unsupported HTTP method"}
        except asyncio.TimeoutError:
            return {
                "code": 500,
                "message": "请求超时",
                "error": f"请求超时（{self.timeout.total}秒）",
            }
        except Exception as e:
            logger.error(f"API 请求异常: {e}")
            return {
                "code": 500,
                "message": "请求异常",
                "error": str(e),
            }

    async def best_records(self, event: str | None = None) -> dict[str, Any]:
        result = await self._request("GET", "/records/best", params={"event": event} if event else None)
        if result.get("code") != 200:
            return result

        raw_records = result.get("data", []) or []
        best_records = []
        for item in raw_records:
            best_records.append({
                "event": item.get("event"),
                "single": {
                    "seconds": item.get("bestSingleSeconds"),
                    "holderNickname": item.get("bestSingleNickname"),
                    "userId": item.get("bestSingleUserNo") or item.get("bestSingleUserId"),
                    "timestamp": item.get("bestSingleTimestamp"),
                } if item.get("bestSingleSeconds") is not None else None,
                "average": {
                    "seconds": item.get("bestAverageSeconds"),
                    "holderNickname": item.get("bestAverageNickname"),
                    "userId": item.get("bestAverageUserNo") or item.get("bestAverageUserId"),
                    "timestamp": item.get("bestAverageTimestamp"),
                } if item.get("bestAverageSeconds") is not None else None,
            })

        return {
            "code": 200,
            "message": result.get("message", "Success"),
            "data": {
                "bestRecords": best_records
            }
        }

    async def bind_user(self, qq_id: str, nickname: str) -> dict[str, Any]:
        return await self._request("POST", "/auth/bind-user-by-nickname", data={
            "qqId": str(qq_id),
            "nickname": nickname,
        })

    async def get_user_bests(self, qq_id: str, event: str | None = None) -> dict[str, Any]:
        user_result = await self._request("GET", "/auth/find-user-by-qq", params={"qqId": str(qq_id)})
        if user_result.get("code") != 200:
            return user_result

        user = user_result.get("data", {}) or {}
        user_id = user.get("userNo") or user.get("id") or user.get("_id")
        if not user_id:
            return {"code": 500, "message": "User data missing id"}

        params = {"event": event} if event else None
        best_result = await self._request("GET", f"/records/user/{user_id}/best", params=params)
        if best_result.get("code") != 200:
            return best_result

        return {
            "code": 200,
            "message": best_result.get("message", "Success"),
            "data": {
                "nickname": user.get("nickname", ""),
                "qqId": user.get("qqId", qq_id),
                "bestRecords": best_result.get("data", []) or [],
            }
        }

    async def submit_record(
        self,
        qq_id: str,
        event: str,
        single_time: str | None = None,
        average_time: str | None = None,
        cube: str | None = None,
        method: str | None = None,
    ) -> dict[str, Any]:
        single_seconds = parse_time_to_seconds(single_time)
        average_seconds = parse_time_to_seconds(average_time)

        payload: dict[str, Any] = {
            "qqId": str(qq_id),
            "event": event,
        }
        if single_seconds is not None:
            payload["singleSeconds"] = single_seconds
        if average_seconds is not None:
            payload["averageSeconds"] = average_seconds
        if cube:
            payload["cube"] = cube
        if method:
            payload["method"] = method

        return await self._request("POST", "/auth/submit-record-by-qq", data=payload)

    async def create_meme_event(
        self,
        qq_id: str,
        event_code: str,
        event_name: str,
        description: str = "",
    ) -> dict[str, Any]:
        return await self._request("POST", "/auth/create-meme-event", data={
            "qqId": str(qq_id),
            "eventCode": event_code,
            "eventName": event_name,
            "description": description,
        })

    async def get_leaderboard(self, event: str, rank_type: str, limit: int = 10) -> dict[str, Any]:
        records_result = await self._request(
            "GET",
            "/records",
            params={"event": event, "pageSize": 2000}
        )
        if records_result.get("code") != 200:
            return records_result

        records = records_result.get("data", []) or []
        time_field = "singleSeconds" if rank_type == "single" else "averageSeconds"
        user_best_map: dict[str, dict[str, Any]] = {}

        for record in records:
            time_value = record.get(time_field)
            if time_value is None:
                continue

            user_id = str(record.get("profileUserNo") or record.get("userId") or "")
            if not user_id:
                continue

            existing = user_best_map.get(user_id)
            if existing is None or time_value < existing.get(time_field):
                user_best_map[user_id] = record

        sorted_records = sorted(
            user_best_map.values(),
            key=lambda item: item.get(time_field, float("inf"))
        )[:limit]

        leaderboard = [
            {
                "rank": index + 1,
                "nickname": item.get("nickname") or "无名高手",
                "seconds": item.get(time_field),
                "userId": item.get("profileUserNo") or item.get("userId"),
            }
            for index, item in enumerate(sorted_records)
        ]

        return {
            "code": 200,
            "message": "Success",
            "data": {
                "event": event,
                "type": rank_type,
                "leaderboard": leaderboard,
            }
        }

    async def fetch_meme_events(self) -> dict[str, Any]:
        return await self._request("GET", "/meme-events")

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()


class HZCubingService:
    def __init__(self, api_client: APIClient):
        self.api_client = api_client
        self.meme_events_cache: dict[str, str] = {}
        self.meme_events_last_fetch = 0
        self.MEME_CACHE_DURATION = 300

    async def _ensure_meme_events(self):
        now = time.time()
        if self.meme_events_cache and (now - self.meme_events_last_fetch < self.MEME_CACHE_DURATION):
            return

        result = await self.api_client.fetch_meme_events()
        next_cache: dict[str, str] = {}

        if result.get("code") == 200:
            for item in result.get("data", []) or []:
                event_code = str(item.get("id") or "").strip()
                event_name = str(item.get("name") or "").strip()
                if not event_code:
                    continue
                next_cache[event_code] = event_code
                if event_name:
                    next_cache[event_name] = event_code

        self.meme_events_cache = next_cache
        self.meme_events_last_fetch = now
