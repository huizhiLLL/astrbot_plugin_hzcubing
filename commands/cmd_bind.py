from astrbot.api.event import AstrMessageEvent

from ..utils.group_policy import is_group_allowed


async def handle(plugin, event: AstrMessageEvent):
    """查询 QQ 绑定状态，并提示从站内完成绑定。"""
    allowed, _ = await is_group_allowed(event)
    if not allowed:
        return

    qq_id = event.get_sender_id()
    if not qq_id:
        yield event.plain_result("请在 QQ 中查询绑定状态。").use_t2i(False)
        return

    result = await plugin.hzcubing_service.api_client.find_user(qq_id)
    if result["code"] == 200:
        yield event.plain_result(f"已绑定 {result['data']['nickname']}。").use_t2i(False)
    elif result["code"] == 404:
        yield event.plain_result("请登录 hzcubing.fun，在个人主页绑定 QQ。").use_t2i(False)
    else:
        yield event.plain_result(result["message"]).use_t2i(False)
