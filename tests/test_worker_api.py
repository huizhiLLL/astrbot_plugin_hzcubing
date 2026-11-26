import os
import sys
import types
import unittest
from unittest.mock import patch

import aiohttp
from aiohttp import web

if "astrbot.api" not in sys.modules:
    astrbot_api = types.ModuleType("astrbot.api")
    astrbot_api.logger = types.SimpleNamespace(warning=lambda *args: None)
    sys.modules["astrbot.api"] = astrbot_api

from services.hzcubing import APIClient, HZCubingService, parse_score


class WorkerAPITest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.authorization = None
        self.payload = None
        app = web.Application()
        app.router.add_get("/api/events", self.events)
        app.router.add_get("/api/records/best", self.current_best)
        app.router.add_get("/api/records/gr", self.history)
        app.router.add_get("/api/records/leaderboard", self.leaderboard)
        app.router.add_post("/api/bot/records", self.submit)
        self.runner = web.AppRunner(app)
        await self.runner.setup()
        site = web.TCPSite(self.runner, "127.0.0.1", 0)
        await site.start()
        port = self.runner.addresses[0][1]
        with patch.dict(os.environ, {"HZCUBING_BOT_SECRET": "test-token"}):
            self.client = APIClient(f"http://127.0.0.1:{port}/api")
        self.addAsyncCleanup(self.runner.cleanup)
        self.addAsyncCleanup(self.client.close)

    async def events(self, request):
        return web.json_response([{"code": "汉堡塔", "name": "汉堡塔", "category": "score", "active": True}, {"code": "meme", "name": "整活", "category": "meme", "active": True}])

    async def current_best(self, request):
        self.authorization = request.headers.get("Authorization")
        return web.json_response([{
            "event": "333", "single": {"seconds": 7.12, "nickname": "选手", "userNo": 1, "timestamp": 0}, "average": None,
        }, {"event": "汉堡塔", "single": None, "average": None, "score": {"value": 0, "nickname": "选手", "userNo": 1, "timestamp": 0}}])

    async def history(self, request):
        return web.json_response({"single": [{"singleSeconds": 7.12, "nickname": "选手", "timestamp": 0}], "average": [], "score": [{"score": 0, "nickname": "选手", "timestamp": 0}]})

    async def leaderboard(self, request):
        return web.json_response([{"rank": 1, "nickname": "选手", "score": 0, "userNo": 1}])

    async def submit(self, request):
        self.authorization = request.headers.get("Authorization")
        self.payload = await request.json()
        if "score" in self.payload:
            return web.json_response({"event": self.payload["event"], "score": float(self.payload["score"]), "isScoreGR": True, "previousScoreBest": {"score": 9.5}}, status=201)
        return web.json_response({"isSingleGR": True, "previousSingleBest": {"singleSeconds": 7.12}}, status=201)

    async def test_public_gr_matches_command_contract(self):
        best = await self.client.best_records("333")
        holder = best["data"]["bestRecords"][0]["single"]
        self.assertEqual(holder["holderNickname"], "选手")
        self.assertEqual(holder["timestamp"], "1970-01-01T00:00:00+00:00")
        self.assertIsNone(self.authorization)
        history = await self.client.gr_history("333")
        self.assertEqual(history["data"]["single"][0]["seconds"], 7.12)
        self.assertEqual(history["data"]["score"][0]["score"], 0)
        self.assertEqual(best["data"]["bestRecords"][1]["score"]["value"], 0)
        board = await self.client.get_leaderboard("汉堡塔", "score")
        self.assertEqual(board["data"]["leaderboard"][0]["seconds"], 0)

    async def test_score_catalog_submission_and_validation(self):
        service = HZCubingService(self.client)
        await service._ensure_meme_events()
        self.assertEqual(service.meme_events_cache["汉堡塔"], "汉堡塔")
        self.assertEqual(service.score_event_codes, {"汉堡塔"})
        for score in ("0", "-2.5", "9.567", "112.6"):
            self.assertEqual(parse_score(score), score)
            result = await self.client.submit_record("10000", "汉堡塔", score=score)
            self.assertEqual(self.payload, {"qqId": "10000", "event": "汉堡塔", "score": score})
            self.assertEqual(result["data"]["score"], float(score))
        for value in ("", "1:52.6", "DNF", "1e2", "12分", "9007199254740992"):
            self.assertIsNone(parse_score(value))

    async def test_authenticated_record_submission(self):
        result = await self.client.submit_record("10000", "333", "6.99")
        self.assertEqual(self.authorization, "Bearer test-token")
        self.assertEqual(self.payload["singleSeconds"], 6.99)
        self.assertEqual(result["code"], 200)
        self.assertEqual(result["data"]["previousSingleBest"]["seconds"], 7.12)
        self.client.token = ""
        self.assertEqual((await self.client.submit_record("10000", "333", "6.98"))["code"], 503)
