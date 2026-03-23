from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from ..utils.group_policy import is_group_allowed


async def handle(plugin, event: AstrMessageEvent):
    """绑定用户 - 将QQ号与系统中的昵称进行绑定
    用法:
    /绑定 [昵称]
    示例: /绑定 会枝
    """
    allowed, _ = await is_group_allowed(event)
    if not allowed:
        return

    cmd_tokens = plugin.parse_commands(event.message_str)

    nickname = cmd_tokens.get(1)
    if not nickname:
        yield event.plain_result(
            "要提供网站昵称哦~\n用法：/绑定 [昵称]\n比如：/绑定 会枝 啦！"
        ).use_t2i(False)
        return

    qq_id = event.get_sender_id()
    if not qq_id:
        yield event.plain_result(
            "哎呀，拿不到你的 QQ 号呢，要在 QQ 里用才行哦~"
        ).use_t2i(False)
        return

    try:
        result = await plugin.hzcubing_service.api_client.bind_user(qq_id, nickname)

        if result.get("code") == 200:
            data = result.get("data", {})
            user_id = data.get("userId", "")
            bound_nickname = data.get("nickname", nickname)
            response_text = (
                f"绑定成功！\n"
                f"QQ号: {qq_id}\n"
                f"昵称: {bound_nickname}\n"
            )
            yield event.plain_result(response_text).use_t2i(False)
        else:
            error_msg = result.get("message", "未知错误")
            response_text = f"绑定失败\n错误: {error_msg}"
            yield event.plain_result(response_text).use_t2i(False)
    except Exception as e:
        logger.error(f"绑定用户命令异常: {e}")
        yield event.plain_result(f"哎呀，出错了呢：{str(e)} 啦！").use_t2i(False)
