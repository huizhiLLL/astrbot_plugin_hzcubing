import sys
import types
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
api = sys.modules.setdefault("astrbot.api", types.ModuleType("astrbot.api"))
api.logger = types.SimpleNamespace(warning=lambda *args: None, error=lambda *args: None)
event_module = sys.modules.setdefault("astrbot.api.event", types.ModuleType("astrbot.api.event"))
event_module.AstrMessageEvent = object

from astrbot_plugin_hzcubing.commands import cmd_submit_record, cmd_leaderboard, cmd_gr, cmd_gr_history
from astrbot_plugin_hzcubing.services.hzcubing import HZCubingService


class Result:
    def __init__(self, text): self.text = text
    def use_t2i(self, _): return self


class Event:
    def __init__(self, text): self.message_str = text
    def plain_result(self, text): return Result(text)
    def get_sender_id(self): return "12345"


class CommandTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.api = types.SimpleNamespace(
            fetch_meme_events=AsyncMock(return_value={"code": 200, "data": [{"id": "汉堡塔", "name": "汉堡塔", "category": "score"}]}),
            submit_record=AsyncMock(return_value={"code": 200, "data": {"event": "汉堡塔", "score": 0, "nickname": "测试", "isScoreGR": True, "previousScoreBest": {"nickname": "旧纪录", "score": -2.5}}}),
            get_leaderboard=AsyncMock(return_value={"code": 200, "data": {"leaderboard": [{"rank": 1, "nickname": "测试", "seconds": 0}]}}),
            best_records=AsyncMock(return_value={"code": 200, "data": {"bestRecords": [{"event": "汉堡塔", "score": {"value": 0, "nickname": "测试"}, "single": None, "average": None}]}}),
            gr_history=AsyncMock(return_value={"code": 200, "data": {"score": [{"score": 0, "nickname": "测试", "timestamp": "2026-01-01T00:00:00+00:00"}], "single": [], "average": []}}),
        )
        service = HZCubingService(self.api)
        self.plugin = types.SimpleNamespace(hzcubing_service=service, parse_commands=lambda text: dict(enumerate(text.split())))

    async def run_command(self, command, text):
        with patch.object(command, "is_group_allowed", AsyncMock(return_value=(True, "test"))):
            return [item.text async for item in command.handle(self.plugin, Event(text))]

    async def test_record_zero_and_reject_time(self):
        messages = await self.run_command(cmd_submit_record, "/录入 汉堡塔 0")
        self.assertIn("成绩: 0", messages[0])
        self.assertIn("旧纪录 -2.5", messages[1])
        kwargs = self.api.submit_record.await_args.kwargs
        self.assertEqual(kwargs["score"], "0")
        self.assertIsNone(kwargs["single_time"])
        self.api.submit_record.reset_mock()
        messages = await self.run_command(cmd_submit_record, "/录入 汉堡塔 1:52.6")
        self.assertIn("积分项目用法", messages[0])
        self.api.submit_record.assert_not_awaited()

    async def test_time_record_keeps_existing_fields(self):
        self.api.submit_record.return_value = {"code": 200, "data": {"event": "333", "nickname": "测试", "singleSeconds": 12.34, "averageSeconds": None}}
        messages = await self.run_command(cmd_submit_record, "/录入 333 12.34 -")
        self.assertIn("单次: 12.34", messages[0])
        kwargs = self.api.submit_record.await_args.kwargs
        self.assertEqual(kwargs["single_time"], "12.34")
        self.assertIsNone(kwargs["score"])

    async def test_score_queries(self):
        board = await self.run_command(cmd_leaderboard, "/排行榜 汉堡塔")
        self.assertIn("测试 0", board[0])
        self.assertEqual(self.api.get_leaderboard.await_args.args[1], "score")
        self.assertIn("测试 0", (await self.run_command(cmd_gr, "/gr 积分"))[0])
        self.assertIn("测试 0", (await self.run_command(cmd_gr_history, "/gr历史 汉堡塔"))[0])
