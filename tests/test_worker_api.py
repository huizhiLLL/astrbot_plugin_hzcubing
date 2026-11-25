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

from services.hzcubing import APIClient


class WorkerAPITest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.authorization = None
        self.payload = None
        app = web.Application()
        app.router.add_get("/api/records/best", self.current_best)
        app.router.add_get("/api/records/gr", self.history)
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

    async def current_best(self, request):
        self.authorization = request.headers.get("Authorization")
        return web.json_response([{
            "event": "333", "single": {"seconds": 7.12, "nickname": "选手", "userNo": 1, "timestamp": 0}, "average": None,
        }])

    async def history(self, request):
        return web.json_response({"single": [{"singleSeconds": 7.12, "nickname": "选手", "timestamp": 0}], "average": []})

    async def submit(self, request):
        self.authorization = request.headers.get("Authorization")
        self.payload = await request.json()
        return web.json_response({"isSingleGR": True, "previousSingleBest": {"singleSeconds": 7.12}}, status=201)

    async def test_public_gr_matches_command_contract(self):
        best = await self.client.best_records("333")
        holder = best["data"]["bestRecords"][0]["single"]
        self.assertEqual(holder["holderNickname"], "选手")
        self.assertEqual(holder["timestamp"], "1970-01-01T00:00:00+00:00")
        self.assertIsNone(self.authorization)
        history = await self.client.gr_history("333")
        self.assertEqual(history["data"]["single"][0]["seconds"], 7.12)

    async def test_authenticated_record_submission(self):
        result = await self.client.submit_record("10000", "333", "6.99")
        self.assertEqual(self.authorization, "Bearer test-token")
        self.assertEqual(self.payload["singleSeconds"], 6.99)
        self.assertEqual(result["code"], 200)
        self.assertEqual(result["data"]["previousSingleBest"]["seconds"], 7.12)
        self.client.token = ""
        self.assertEqual((await self.client.submit_record("10000", "333", "6.98"))["code"], 503)
