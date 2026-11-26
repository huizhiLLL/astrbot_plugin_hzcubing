import asyncio
import os
import re
from datetime import datetime, timezone
import time
from decimal import Decimal, ROUND_DOWN
from typing import Any

import aiohttp
from astrbot.api import logger

# API 配置
API_BASE_URL = "https://hzcubing.fun/api"
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


def parse_score(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]+)?", value):
        return None
    try:
        return value if abs(Decimal(value)) <= Decimal(9007199254740991) else None
    except Exception:
        return None


class APIClient:
    def __init__(self, base_url: str | None = None, timeout: int = REQUEST_TIMEOUT):
        self.base_url = (base_url or os.getenv("HZCUBING_API_URL") or API_BASE_URL).rstrip("/")
        self.token = os.getenv("HZCUBING_BOT_SECRET", "").strip()
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
        headers = {}
        if endpoint.startswith("/bot/"):
            if not self.token:
                return {"code": 503, "message": "成绩服务的机器人凭据尚未配置"}
            headers["Authorization"] = f"Bearer {self.token}"
        session = await self._ensure_session()
        try:
            async with session.request(
                method, f"{self.base_url}{endpoint}", params=params, json=data,
                headers=headers, allow_redirects=False,
            ) as response:
                payload = await response.json(content_type=None)
                if 200 <= response.status < 300:
                    return {"code": 200, "data": payload}
                message = payload.get("message") if isinstance(payload, dict) else None
                return {"code": response.status, "message": message or "成绩服务请求失败"}
        except asyncio.TimeoutError:
            return {"code": 503, "message": "成绩服务请求超时"}
        except (aiohttp.ClientError, ValueError):
            logger.warning("HZCubing API 请求失败")
            return {"code": 503, "message": "暂时无法连接成绩服务"}

    @staticmethod
    def _timestamp(value: int | None) -> str | None:
        return datetime.fromtimestamp(value / 1000, timezone.utc).isoformat() if value is not None else None

    async def best_records(self, event: str | None = None) -> dict[str, Any]:
        result = await self._request("GET", "/records/best", params={"event": event} if event else None)
        if result.get("code") != 200:
            return result

        def holder(item):
            if item is None:
                return None
            return {
                "seconds": item["seconds"], "holderNickname": item["nickname"],
                "userId": item["userNo"], "timestamp": self._timestamp(item["timestamp"]),
            }

        return {"code": 200, "data": {"bestRecords": [
            {"event": row["event"], "single": holder(row["single"]), "average": holder(row["average"]), "score": row.get("score")}
            for row in result["data"]
        ]}}

    async def gr_history(self, event: str) -> dict[str, Any]:
        result = await self._request("GET", "/records/gr", params={"event": event})
        if result["code"] != 200:
            return result
        return {"code": 200, "data": {metric: [
            {"seconds": row[f"{metric}Seconds"], "nickname": row["nickname"], "timestamp": self._timestamp(row["timestamp"])}
            for row in result["data"][metric]
        ] for metric in ("single", "average")} | {"score": [
            {"score": row["score"], "nickname": row["nickname"], "timestamp": self._timestamp(row["timestamp"])}
            for row in result["data"].get("score", [])
        ]}}

    async def find_user(self, qq_id: str) -> dict[str, Any]:
        return await self._request("GET", "/bot/player", params={"qqId": str(qq_id)})

    async def get_user_bests(self, qq_id: str, event: str | None = None) -> dict[str, Any]:
        user_result = await self.find_user(qq_id)
        if user_result.get("code") != 200:
            return user_result

        user = user_result.get("data", {}) or {}
        user_id = user.get("userNo") or user.get("id") or user.get("_id")
        if not user_id:
            return {"code": 500, "message": "User data missing id"}

        best_result = await self._request("GET", f"/players/{user_id}")
        if best_result.get("code") != 200:
            return best_result

        return {
            "code": 200,
            "message": best_result.get("message", "Success"),
            "data": {
                "nickname": user.get("nickname", ""),
                "qqId": user.get("qqId", qq_id),
                "bestRecords": [
                    {"event": row["event"], "bestSingleSeconds": row["singleSeconds"], "bestAverageSeconds": row["averageSeconds"], "score": row.get("score")}
                    for row in best_result["data"]["best"] if not event or row["event"] == event
                ],
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
        score: str | None = None,
    ) -> dict[str, Any]:
        single_seconds = parse_time_to_seconds(single_time)
        average_seconds = parse_time_to_seconds(average_time)

        payload: dict[str, Any] = {
            "qqId": str(qq_id),
            "event": event,
        }
        if score is not None:
            payload["score"] = score
        if single_seconds is not None:
            payload["singleSeconds"] = single_seconds
        if average_seconds is not None:
            payload["averageSeconds"] = average_seconds
        if cube:
            payload["cube"] = cube
        if method:
            payload["method"] = method

        result = await self._request("POST", "/bot/records", data=payload)
        if result["code"] == 200:
            for key, metric in (("previousSingleBest", "single"), ("previousAverageBest", "average")):
                previous = result["data"].get(key)
                if previous is not None:
                    previous["seconds"] = previous.get(f"{metric}Seconds")
        return result

    async def create_meme_event(
        self,
        qq_id: str,
        event_code: str,
        event_name: str,
        description: str = "",
    ) -> dict[str, Any]:
        result = await self._request("POST", "/bot/events", data={
            "qqId": str(qq_id),
            "code": event_code,
            "name": event_name,
            "description": description,
        })
        if result["code"] == 200:
            result["data"]["id"] = result["data"]["code"]
        return result

    async def get_leaderboard(self, event: str, rank_type: str, limit: int = 10) -> dict[str, Any]:
        """获取单项目排行榜

        Args:
            event: 项目代码
            rank_type: 排名类型，"single" 或 "average"
            limit: 返回条数，默认10，最大200
        """
        params = {
            "event": event,
            "type": rank_type,
            "limit": min(limit, 200),  # 接口最大限制200
        }

        result = await self._request("GET", "/records/leaderboard", params=params)
        if result.get("code") != 200:
            return result

        # 接口返回的数据已经是按用户聚合并排序好的
        leaderboard_data = result.get("data", []) or []

        # 转换为统一格式，添加排名
        time_field = "score" if rank_type == "score" else "singleSeconds" if rank_type == "single" else "averageSeconds"
        leaderboard = [
            {
                "rank": item["rank"],
                "nickname": item.get("nickname") or "无名高手",
                "seconds": item.get(time_field),
                "userId": item["userNo"],
            }
            for item in leaderboard_data
        ]

        return {
            "code": 200,
            "message": result.get("message", "Success"),
            "data": {
                "event": event,
                "type": rank_type,
                "leaderboard": leaderboard,
            }
        }

    async def fetch_meme_events(self) -> dict[str, Any]:
        result = await self._request("GET", "/events")
        if result["code"] == 200:
            result["data"] = [
                {"id": row["code"], "name": row["name"], "category": row["category"]}
                for row in result["data"] if row["category"] in ("meme", "score") and row["active"]
            ]
        return result

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()


class HZCubingService:
    def __init__(self, api_client: APIClient):
        self.api_client = api_client
        self.meme_events_cache: dict[str, str] = {}
        self.score_event_codes: set[str] = set()
        self.meme_events_last_fetch = 0
        self.MEME_CACHE_DURATION = 300

    async def _ensure_meme_events(self):
        now = time.time()
        if self.meme_events_cache and (now - self.meme_events_last_fetch < self.MEME_CACHE_DURATION):
            return

        result = await self.api_client.fetch_meme_events()
        next_cache: dict[str, str] = {}
        next_scores: set[str] = set()

        if result.get("code") == 200:
            for item in result.get("data", []) or []:
                event_code = str(item.get("id") or "").strip()
                event_name = str(item.get("name") or "").strip()
                if not event_code:
                    continue
                if item.get("category") == "score":
                    next_scores.add(event_code)
                next_cache[event_code] = event_code
                if event_name:
                    next_cache[event_name] = event_code

        self.score_event_codes = next_scores
        self.meme_events_cache = next_cache
        self.meme_events_last_fetch = now
