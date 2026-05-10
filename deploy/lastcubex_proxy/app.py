import asyncio
import time
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


UPSTREAM_BASE_URL = "https://api.kdcubeapp.com"
REQUEST_TIMEOUT = 15
CONNECT_TIMEOUT = 8
MAX_RETRIES = 2
CACHE_TTL_SECONDS = 180
UPSTREAM_HEADERS = {
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


class AllRankingBody(BaseModel):
    event: str = Field(..., description="项目代码，如 333")
    limit: int = Field(10, ge=1, le=50)


class UsersResolveBody(BaseModel):
    users: list[str]


def normalize_event_input(event: str | None) -> str | None:
    if not event:
        return None
    normalized = "".join(str(event).strip().split()).lower()
    if not normalized:
        return None
    return normalized if normalized in EVENT_MAP else None


class LastCubeXProxyService:
    def __init__(self):
        self.client = httpx.AsyncClient(
            base_url=UPSTREAM_BASE_URL,
            headers=UPSTREAM_HEADERS,
            timeout=httpx.Timeout(REQUEST_TIMEOUT, connect=CONNECT_TIMEOUT),
        )
        self.all_ranking_cache: dict[tuple[str, int], tuple[float, dict[str, Any]]] = {}

    async def close(self):
        await self.client.aclose()

    async def _post_json(self, endpoint: str, payload: dict[str, Any]) -> Any:
        last_error: HTTPException | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                response = await self.client.post(endpoint, json=payload)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                detail = exc.response.text[:200]
                last_error = HTTPException(
                    status_code=exc.response.status_code,
                    detail=f"上游接口返回 HTTP {exc.response.status_code}: {detail}",
                )
                if exc.response.status_code >= 500 and attempt < MAX_RETRIES:
                    await asyncio.sleep(0.4 * attempt)
                    continue
                raise last_error
            except (httpx.ConnectTimeout, httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as exc:
                last_error = HTTPException(status_code=504, detail=f"上游请求超时: {type(exc).__name__}")
            except httpx.HTTPError as exc:
                last_error = HTTPException(status_code=502, detail=f"上游连接异常: {type(exc).__name__}")

            if attempt < MAX_RETRIES:
                await asyncio.sleep(0.4 * attempt)

        if last_error is None:
            raise HTTPException(status_code=500, detail="未知上游错误")
        raise last_error

    def _get_cached_all_ranking(self, event: str, limit: int) -> dict[str, Any] | None:
        cached = self.all_ranking_cache.get((event, limit))
        if not cached:
            return None
        cached_at, payload = cached
        if time.time() - cached_at > CACHE_TTL_SECONDS:
            self.all_ranking_cache.pop((event, limit), None)
            return None
        return payload

    def _set_cached_all_ranking(self, event: str, limit: int, payload: dict[str, Any]):
        self.all_ranking_cache[(event, limit)] = (time.time(), payload)

    async def get_current_competition(self) -> dict[str, Any]:
        data = await self._post_json("/v2/competition/processing", {})
        if not isinstance(data, list):
            raise HTTPException(status_code=502, detail="周赛接口响应格式异常")
        return {"code": 200, "message": "Success", "data": data}

    async def resolve_users(self, users: list[str]) -> dict[str, Any]:
        filtered = [str(user).strip() for user in users if str(user).strip()]
        data = await self._post_json("/v2/user/list", {"users": filtered})
        if not isinstance(data, list):
            raise HTTPException(status_code=502, detail="用户资料接口响应格式异常")
        return {"code": 200, "message": "Success", "data": data}

    async def get_all_ranking(self, event: str, limit: int) -> dict[str, Any]:
        normalized_event = normalize_event_input(event)
        if not normalized_event:
            raise HTTPException(status_code=400, detail="不支持的 LastCubeX 项目")

        cached = self._get_cached_all_ranking(normalized_event, limit)
        if cached is not None:
            return cached

        ranking_result = await self._post_json(
            "/v2/competition/all/ranking",
            {"item": EVENT_MAP[normalized_event], "avg": 0, "best_time": 0, "limit": limit},
        )
        if not isinstance(ranking_result, list):
            raise HTTPException(status_code=502, detail="总榜接口响应格式异常")

        user_ids: list[str] = []
        for record in ranking_result:
            user_id = str(record.get("user_id") or "").strip()
            if user_id and user_id not in user_ids:
                user_ids.append(user_id)

        nickname_map: dict[str, str] = {}
        if user_ids:
            users_result = await self._post_json("/v2/user/list", {"users": user_ids})
            if not isinstance(users_result, list):
                raise HTTPException(status_code=502, detail="用户资料接口响应格式异常")
            nickname_map = {
                str(user.get("id") or "").strip(): str(user.get("username") or "").strip()
                for user in users_result
                if str(user.get("id") or "").strip()
            }

        payload = {
            "code": 200,
            "message": "Success",
            "data": {
                "event": normalized_event,
                "leaderboard": [
                    {
                        "rank": index,
                        "nickname": nickname_map.get(str(record.get("user_id") or "").strip()) or "未知用户",
                        "avg": record.get("avg"),
                        "user_id": str(record.get("user_id") or "").strip(),
                    }
                    for index, record in enumerate(ranking_result, start=1)
                ],
            },
        }
        self._set_cached_all_ranking(normalized_event, limit, payload)
        return payload


app = FastAPI(title="LastCubeX Proxy", version="1.0.0")
service = LastCubeXProxyService()


@app.on_event("shutdown")
async def shutdown_event():
    await service.close()


@app.get("/health")
async def health():
    return {"ok": True}


@app.get("/api/lastcubex/current-competition")
async def current_competition():
    return await service.get_current_competition()


@app.post("/api/lastcubex/users/resolve")
async def resolve_users(body: UsersResolveBody):
    return await service.resolve_users(body.users)


@app.get("/api/lastcubex/all-ranking")
async def get_all_ranking(event: str, limit: int = 10):
    return await service.get_all_ranking(event, limit)


@app.post("/api/lastcubex/all-ranking")
async def post_all_ranking(body: AllRankingBody):
    return await service.get_all_ranking(body.event, body.limit)
