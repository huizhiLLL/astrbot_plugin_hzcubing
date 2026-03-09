from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.api import logger

from .one_api import (
    PersonalRecordAPIClient,
    OneRecordHandler,
    format_time_ms,
)
from .hzcubing import HZCubingService, APIClient
from .cmd_cube_help import handle as handle_cube_help
from .cmd_pr import handle as handle_pr
from .cmd_prpk import handle as handle_prpk
from .cmd_gr import handle as handle_gr
from .cmd_one import handle as handle_one
from .cmd_bind import handle as handle_bind
from .cmd_submit_record import handle as handle_submit_record
from .cmd_user_bests import handle as handle_user_bests
from .cmd_user_bests_pic import handle as handle_user_bests_pic
from .cmd_cto import handle as handle_cto
from .wenjun_cube import handle as handle_wenjun_cube


@register("astrbot_plugin_hzcubing", "huizhi", "hzcubing", "1.0.1")
class HZCubingPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        hzcubing_api_client = APIClient()
        self.hzcubing_service = HZCubingService(hzcubing_api_client)
        self.personal_record_client = PersonalRecordAPIClient()
        self.one_handler = OneRecordHandler(
            self.personal_record_client,
            format_time_ms
        )
        self.wca_query = None

    async def initialize(self):
        logger.info("会枝cubing 插件已加载")

    async def terminate(self):
        await self.hzcubing_service.api_client.close()
        await self.personal_record_client.close()
        logger.info("会枝cubing 插件已卸载")

    @filter.command("cube帮助")
    async def help_command(self, event: AstrMessageEvent):
        async for result in handle_cube_help(event, self.context):
            yield result

    @filter.command("pr")
    async def pr_command(self, event: AstrMessageEvent):
        async for result in handle_pr(self, event):
            yield result

    @filter.command("prpk")
    async def pr_pk_command(self, event: AstrMessageEvent):
        async for result in handle_prpk(self, event):
            yield result

    @filter.command("gr", alias={"GR"})
    async def best_records_command(self, event: AstrMessageEvent):
        async for result in handle_gr(self, event):
            yield result

    @filter.command("one", alias={"ONE"})
    async def personal_record_command(self, event: AstrMessageEvent):
        async for result in handle_one(self, event):
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

    @filter.command("cto", alias={"CTO"})
    async def cto_scramble_command(self, event: AstrMessageEvent):
        async for result in handle_cto(event):
            yield result

    @filter.command("俊改")
    async def wenjun_cube_command(self, event: AstrMessageEvent):
        async for result in handle_wenjun_cube(event):
            yield result
