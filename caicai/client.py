import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any

import aiohttp

try:
    from astrbot.api import logger
except ImportError:  # pragma: no cover
    logger = logging.getLogger(__name__)


CONFIG_PATH = Path(__file__).resolve().parent / "config.json"
REQUEST_TIMEOUT = 20

EVENT_ORDER = [
    "333",
    "222",
    "333oh",
    "444",
    "555",
    "666",
    "777",
    "clock",
    "meg",
    "pyram",
    "skewb",
    "sq1",
    "333bf",
    "444bf",
    "555bf",
    "333mbf",
    "333fm",
    "fto",
    "e333",
    "moyuwcu",
    "smartplayer",
]

EVENT_NAME_MAP = {
    "333": "333",
    "三阶": "333",
    "三速": "333",
    "222": "222",
    "二阶": "222",
    "二速": "222",
    "333oh": "333oh",
    "三单": "333oh",
    "单手": "333oh",
    "444": "444",
    "四阶": "444",
    "555": "555",
    "五阶": "555",
    "clock": "clock",
    "clk": "clock",
    "魔表": "clock",
    "meg": "meg",
    "五魔方": "meg",
    "pyram": "pyram",
    "金字塔": "pyram",
    "skewb": "skewb",
    "斜转": "skewb",
    "e333": "e333",
    "智能三阶": "e333",
    "moyuwcu": "moyuwcu",
    "smartplayer": "smartplayer",
}


def load_config() -> dict[str, Any]:
    with CONFIG_PATH.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def is_tcid(value: str) -> bool:
    return bool(re.match(r"^TC\d{4}[A-Z0-9]+$", value.upper()))


def normalize_event_name(event: str) -> str:
    return EVENT_NAME_MAP.get(event, event)


def format_centiseconds(value: int | None) -> str:
    if value is None:
        return "-"
    if value < 0:
        return "-"
    if value == 999999:
        return "DNF"
    if value == 999998:
        return "DNS"
    minutes = value // 6000
    seconds = (value % 6000) // 100
    centiseconds = value % 100
    if minutes:
        return f"{minutes}:{seconds:02d}.{centiseconds:02d}"
    return f"{seconds}.{centiseconds:02d}"


class CaicaiClient:
    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or load_config()
        self.endpoint = self.config["endpoint"]
        self.env = self.config["env"]
        self.timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        self.session: aiohttp.ClientSession | None = None

    def ensure_not_expired(self):
        expires_at = self.config.get("expires_at")
        if not expires_at:
            return
        expires = datetime.fromisoformat(expires_at)
        if datetime.now(expires.tzinfo) >= expires:
            raise RuntimeError("赛赛平台登录态已过期，请先刷新后再查询哦~")

    async def _ensure_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self.session

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def _post(self, function_name: str, request_data: dict[str, Any]) -> dict[str, Any]:
        self.ensure_not_expired()
        session = await self._ensure_session()
        payload = {
            "action": "functions.invokeFunction",
            "env": self.env,
            "dataVersion": "2019-08-16",
            "function_name": function_name,
            "request_data": json.dumps(request_data, ensure_ascii=False, separators=(",", ":")),
            "access_token": self.config["access_token"],
        }
        try:
            async with session.post(
                self.endpoint,
                params={"env": self.env},
                json=payload,
                headers={"Content-Type": "application/json"},
            ) as response:
                raw = await response.json(content_type=None)
        except Exception as exc:  # noqa: BLE001
            logger.error(f"魔方菜菜请求失败: {exc}")
            raise

        return json.loads(raw["data"]["response_data"])

    async def search_competitors(self, keyword: str, limit: int = 10) -> list[dict[str, Any]]:
        condition = f"/{keyword}/i.test(tcid) || /{keyword}/i.test(name) || /{keyword}/i.test(name_en)"
        request_data = {
            "command": {
                "$db": [
                    {"$method": "collection", "$param": ["c-competitors"]},
                    {"$method": "where", "$param": [condition]},
                    {"$method": "field", "$param": ["_id,name,name_en,tcid"]},
                    {"$method": "limit", "$param": [limit]},
                    {"$method": "get", "$param": []},
                ]
            },
            "clientInfo": self.config["client_info"],
            "uniIdToken": self.config["uni_id_token"],
        }
        result = await self._post("DCloud-clientDB", request_data)
        return result.get("data", []) or []

    async def get_competitor_page(self, tcid: str) -> dict[str, Any]:
        request_data = {
            "action": "competitor/getCompetitorPageInfo",
            "tcid": tcid,
            "apiMiddlewareParams": {"mayVerifyToken": False},
            "params": {"tcid": tcid},
            "clientInfo": self.config["client_info"],
            "uniIdToken": self.config["uni_id_token"],
        }
        result = await self._post("api-common-open", request_data)
        return result.get("data", {}) or {}

    async def query_player(self, query: str) -> dict[str, Any]:
        if is_tcid(query):
            page = await self.get_competitor_page(query.upper())
            return {
                "query": query,
                "match": {"tcid": query.upper()},
                "page_data": page,
                "summary": self.summarize_best_scores(page),
            }

        matches = await self.search_competitors(query)
        if not matches:
            raise RuntimeError(f"No competitor found for query: {query}")

        exact = [item for item in matches if item.get("name") == query or item.get("tcid") == query]
        if not exact:
            return {
                "query": query,
                "matches": matches,
                "match": None,
                "page_data": {},
                "summary": None,
            }

        chosen = exact[0]
        page = await self.get_competitor_page(chosen["tcid"])
        return {
            "query": query,
            "matches": matches,
            "match": chosen,
            "page_data": page,
            "summary": self.summarize_best_scores(page),
        }

    def summarize_best_scores(self, page_data: dict[str, Any]) -> dict[str, Any]:
        ranking = page_data.get("ranking", {}) or {}
        info = page_data.get("info", {}) or {}
        rows = []
        for event_code, result in ranking.items():
            rows.append(
                {
                    "event": normalize_event_name(event_code),
                    "best": format_centiseconds(result.get("best")),
                    "average": format_centiseconds(result.get("average")),
                    "ranking_single_site": result.get("ranking_single_site"),
                    "ranking_average_site": result.get("ranking_average_site"),
                }
            )
        rows.sort(
            key=lambda item: (
                EVENT_ORDER.index(item["event"]) if item["event"] in EVENT_ORDER else len(EVENT_ORDER),
                item["event"],
            )
        )
        return {
            "name": info.get("name"),
            "name_en": info.get("name_en"),
            "tcid": info.get("tcid"),
            "wcaid": info.get("wcaid"),
            "best_scores": rows,
        }
