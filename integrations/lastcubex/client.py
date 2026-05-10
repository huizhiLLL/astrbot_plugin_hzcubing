import asyncio
from typing import Any

import aiohttp
from astrbot.api import logger


BASE_URL = "https://lc.huizhi.ink"
REQUEST_TIMEOUT = 15
HEADERS = {
    "Accept": "application/json",
    "User-Agent": "AstrBot-HZCubing/1.0",
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
        self.timeout = aiohttp.ClientTimeout(total=timeout, connect=10, sock_read=timeout)
        self.session: aiohttp.ClientSession | None = None

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout, headers=HEADERS)
        return self.session

    async def _request_json(
        self,
        method: str,
        endpoint: str,
        *,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
    ) -> Any:
        session = await self._ensure_session()
        url = f"{self.base_url}{endpoint}"
        try:
            if method.upper() == "GET":
                async with session.get(url, params=params) as response:
                    if response.status >= 400:
                        return {
                            "code": response.status,
                            "message": f"中转接口返回 HTTP {response.status}",
                            "error": await response.text(),
                        }
                    return await response.json(content_type=None)
            async with session.post(url, json=payload or {}) as response:
                if response.status >= 400:
                    return {
                        "code": response.status,
                        "message": f"中转接口返回 HTTP {response.status}",
                        "error": await response.text(),
                    }
                return await response.json(content_type=None)
        except asyncio.TimeoutError as exc:
            logger.warning(f"LastCubeX 中转请求超时: endpoint={endpoint}, error={type(exc).__name__}")
            return {"code": 500, "message": "中转请求超时", "error": type(exc).__name__}
        except Exception as exc:
            logger.error(f"LastCubeX 中转请求异常: endpoint={endpoint}, error={type(exc).__name__}: {exc!r}")
            return {"code": 500, "message": "中转请求异常", "error": f"{type(exc).__name__}: {exc!r}"}

    async def get_all_ranking(self, event_input: str, limit: int = 10) -> dict[str, Any]:
        normalized_event = normalize_event_input(event_input)
        if not normalized_event:
            return {"code": 400, "message": "不支持的 LastCubeX 项目"}

        result = await self._request_json(
            "GET",
            "/api/lastcubex/all-ranking",
            params={"event": normalized_event, "limit": limit},
        )
        return result

    async def get_current_ranking(self, event_input: str, limit: int = 15) -> dict[str, Any]:
        normalized_event = normalize_event_input(event_input)
        if not normalized_event:
            return {"code": 400, "message": "不支持的 LastCubeX 项目"}

        result = await self._request_json(
            "GET",
            "/api/lastcubex/current-ranking",
            params={"event": normalized_event, "limit": limit},
        )
        return result

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
