from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from ..utils.group_policy import is_group_allowed


async def handle(plugin, event: AstrMessageEvent):
    """创建整活项目 - 通过已绑定的QQ号创建整活项目
    用法:
    /创建 [项目名]
    示例: /创建 三阶镜面
    """
    allowed, _ = await is_group_allowed(event)
    if not allowed:
        return

    cmd_tokens = plugin.parse_commands(event.message_str)
    event_name = cmd_tokens.get(1)

    if not event_name:
        yield event.plain_result(
            "还没说要创建什么项目呢~\n"
            "用法：/创建 [项目名]\n"
            "比如：/创建 三阶镜面"
        ).use_t2i(False)
        return

    event_name = event_name.strip()
    if not event_name:
        yield event.plain_result("项目名要有内容哦~").use_t2i(False)
        return

    qq_id = event.get_sender_id()
    if not qq_id:
        yield event.plain_result(
            "哎呀，拿不到你的 QQ 号呢，要在 QQ 里用才行哦~"
        ).use_t2i(False)
        return

    try:
        result = await plugin.hzcubing_service.api_client.create_meme_event(
            qq_id=qq_id,
            event_code=event_name,
            event_name=event_name,
            description="",
        )

        if result.get("code") == 200:
            data = result.get("data", {})
            response_lines = [
                "整活项目创建成功啦！",
                f"项目名: {data.get('name', event_name)}",
                f"项目代码: {data.get('id', event_name)}",
            ]

            created_by_name = data.get("createdByName")
            if created_by_name:
                response_lines.append(f"创建者: {created_by_name}")

            yield event.plain_result("\n".join(response_lines)).use_t2i(False)
            return

        error_msg = result.get("message", "未知错误")
        if result.get("code") == 404 and "bind" in str(error_msg).lower():
            error_msg = "还没绑定站内账号哦，先用 /绑定 [昵称] 再来创建吧~"
        response_text = f"创建失败\n错误: {error_msg}"
        yield event.plain_result(response_text).use_t2i(False)
    except Exception as e:
        logger.error(f"创建整活项目命令异常: {e}")
        yield event.plain_result(f"哎呀，出错了呢：{str(e)} 啦！").use_t2i(False)
