from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

from .commands.cmd_bind import handle as handle_bind
from .commands.cmd_cto import handle as handle_cto
from .commands.cmd_gr import handle as handle_gr
from .commands.cmd_leaderboard import handle as handle_leaderboard
from .commands.cmd_submit_record import handle as handle_submit_record
from .commands.cmd_user_bests import handle as handle_user_bests
from .commands.cmd_user_bests_pic import handle as handle_user_bests_pic
from .commands.wenjun_cube import handle as handle_wenjun_cube
from .integrations.caicai import CaicaiClient
from .integrations.caicai.command import handle as handle_caicai
from .services.hzcubing import HZCubingService, APIClient


@register("astrbot_plugin_hzcubing", "huizhi", "hzcubing", "1.0.3")
class HZCubingPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        hzcubing_api_client = APIClient()
        self.hzcubing_service = HZCubingService(hzcubing_api_client)
        self.caicai_client = CaicaiClient()

    async def initialize(self):
        logger.info("会枝cubing 插件已加载")

    async def terminate(self):
        await self.hzcubing_service.api_client.close()
        await self.caicai_client.close()
        logger.info("会枝cubing 插件已卸载")

    @filter.command("gr", alias={"GR"})
    async def best_records_command(self, event: AstrMessageEvent):
        async for result in handle_gr(self, event):
            yield result

    @filter.command("绑定")
    async def bind_user_command(self, event: AstrMessageEvent):
        async for result in handle_bind(self, event):
            yield result

    @filter.command("录入")
    async def submit_record_command(self, event: AstrMessageEvent):
        async for result in handle_submit_record(self, event):
            yield result

    @filter.command("个人记录")
    async def get_user_bests_command(self, event: AstrMessageEvent):
        async for result in handle_user_bests(self, event):
            yield result

    @filter.command("个人记录图")
    async def get_user_bests_pic_command(self, event: AstrMessageEvent):
        async for result in handle_user_bests_pic(self, event):
            yield result

    @filter.command("排行榜")
    async def leaderboard_command(self, event: AstrMessageEvent):
        async for result in handle_leaderboard(self, event):
            yield result

    @filter.command("cto", alias={"CTO"})
    async def cto_scramble_command(self, event: AstrMessageEvent):
        async for result in handle_cto(event):
            yield result

    @filter.command("俊改")
    async def wenjun_cube_command(self, event: AstrMessageEvent):
        async for result in handle_wenjun_cube(event):
            yield result

    @filter.command("赛赛")
    async def caicai_command(self, event: AstrMessageEvent):
        async for result in handle_caicai(self, event):
            yield result
