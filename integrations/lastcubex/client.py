import asyncio
from typing import Any

import aiohttp
from astrbot.api import logger


BASE_URL = "https://api.kdcubeapp.com"
REQUEST_TIMEOUT = 10
MAX_RETRIES = 2
HEADERS = {
    "User-Agent": "Dalvik/2.1.0 (Linux; U; Android 14; 23127PN0CC Build/UKQ1.230804.001)",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8",
    "Content-Type": "application/json; charset=UTF-8",
    "Connection": "keep-alive",
}

EVENT_MAP = {
    "222": "cube2",
    "333": "cube3",
    "444": "cube4",
    "555": "cube5",
    "666": "cube6",
    "777": "cube7",
    "333oh": "oh3",
    "clock": "clock",
    "py": "pyraminx",
    "sk": "skewb",
    "minx": "megaminx",
    "sq1": "sq1",
    "333bf": "bf3",
    "fto": "fto",
}

SUPPORTED_EVENT_TEXT = "222 333 444 555 666 777 333oh clock py sk minx sq1 333bf fto"


def normalize_event_input(event: str | None) -> str | None:
    if not event:
        return None
    normalized = "".join(str(event).strip().split()).lower()
    if not normalized:
        return None
    return normalized if normalized in EVENT_MAP else None


def format_time_millis(time_millis: int | float | None) -> str:
    if time_millis is None:
        return "-"
    try:
        millis = int(time_millis)
        if millis <= 0:
            return "-"

        minutes = millis // 60000
        seconds = (millis % 60000) // 1000
        millis_remainder = millis % 1000
        if minutes > 0:
            return f"{minutes}:{seconds:02d}.{millis_remainder:03d}"
        return f"{seconds}.{millis_remainder:03d}"
    except Exception:
        return "-"


class LastCubeXClient:
    def __init__(self, base_url: str = BASE_URL, timeout: int = REQUEST_TIMEOUT):
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout
        self.timeout = aiohttp.ClientTimeout(total=timeout, connect=5, sock_read=timeout)
        self.session: aiohttp.ClientSession | None = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout, headers=HEADERS)
        return self.session

    async def _reset_session(self):
        if self.session and not self.session.closed:
            await self.session.close()
        self.session = None

    async def _post_json(self, endpoint: str, payload: dict[str, Any]) -> Any:
        url = f"{self.base_url}{endpoint}"
        last_error: dict[str, Any] | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            session = await self._ensure_session()
            try:
                async with session.post(url, json=payload) as response:
                    if response.status >= 400:
                        response_text = await response.text()
                        logger.warning(
                            f"LastCubeX 请求失败: endpoint={endpoint}, status={response.status}, "
                            f"attempt={attempt}/{MAX_RETRIES}, body={response_text[:200]}"
                        )
                        last_error = {
                            "code": response.status,
                            "message": f"上游接口返回 HTTP {response.status}",
                            "error": response_text[:200],
                        }
                        if response.status >= 500 and attempt < MAX_RETRIES:
                            await self._reset_session()
                            await asyncio.sleep(0.4 * attempt)
                            continue
                        return last_error
                    return await response.json(content_type=None)
            except asyncio.TimeoutError as exc:
                logger.warning(
                    f"LastCubeX 请求超时: endpoint={endpoint}, timeout={self.timeout_seconds}s, "
                    f"attempt={attempt}/{MAX_RETRIES}, error={type(exc).__name__}"
                )
                last_error = {
                    "code": 500,
                    "message": "请求超时",
                    "error": f"{type(exc).__name__}: timeout={self.timeout_seconds}s",
                }
            except (
                aiohttp.ClientConnectionError,
                aiohttp.ClientPayloadError,
                aiohttp.ServerDisconnectedError,
            ) as exc:
                logger.warning(
                    f"LastCubeX 连接异常: endpoint={endpoint}, attempt={attempt}/{MAX_RETRIES}, "
                    f"error={type(exc).__name__}: {exc!r}"
                )
                last_error = {
                    "code": 500,
                    "message": "连接上游接口失败",
                    "error": f"{type(exc).__name__}: {exc!r}",
                }
            except Exception as exc:
                logger.error(
                    f"LastCubeX 请求异常: endpoint={endpoint}, attempt={attempt}/{MAX_RETRIES}, "
                    f"error={type(exc).__name__}: {exc!r}"
                )
                return {
                    "code": 500,
                    "message": "请求异常",
                    "error": f"{type(exc).__name__}: {exc!r}",
                }

            if attempt < MAX_RETRIES:
                await self._reset_session()
                await asyncio.sleep(0.4 * attempt)

        return last_error or {"code": 500, "message": "请求异常", "error": "unknown error"}

    async def get_all_ranking(self, event_input: str, limit: int = 10) -> dict[str, Any]:
        normalized_event = normalize_event_input(event_input)
        if not normalized_event:
            return {"code": 400, "message": "不支持的 LastCubeX 项目"}

        ranking_result = await self._post_json(
            "/v2/competition/all/ranking",
            {
                "item": EVENT_MAP[normalized_event],
                "avg": 0,
                "best_time": 0,
                "limit": limit,
            },
        )
        if isinstance(ranking_result, dict) and ranking_result.get("code"):
            return ranking_result
        if not isinstance(ranking_result, list):
            return {"code": 500, "message": "LastCubeX 总榜响应格式异常"}

        user_ids: list[str] = []
        for record in ranking_result:
            user_id = str(record.get("user_id") or "").strip()
            if user_id and user_id not in user_ids:
                user_ids.append(user_id)

        nickname_map: dict[str, str] = {}
        if user_ids:
            users_result = await self._post_json("/v2/user/list", {"users": user_ids})
            if isinstance(users_result, list):
                nickname_map = {
                    str(user.get("id") or "").strip(): str(user.get("username") or "").strip()
                    for user in users_result
                    if str(user.get("id") or "").strip()
                }
            elif isinstance(users_result, dict) and users_result.get("code"):
                return users_result
            else:
                return {"code": 500, "message": "LastCubeX 用户资料响应格式异常"}

        leaderboard = []
        for index, record in enumerate(ranking_result, start=1):
            user_id = str(record.get("user_id") or "").strip()
            leaderboard.append(
                {
                    "rank": index,
                    "nickname": nickname_map.get(user_id) or "未知用户",
                    "avg": record.get("avg"),
                }
            )

        return {
            "code": 200,
            "message": "Success",
            "data": {
                "event": normalized_event,
                "leaderboard": leaderboard,
            },
        }

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
