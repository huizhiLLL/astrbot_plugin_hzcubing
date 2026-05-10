from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from ...integrations.lastcubex import (
    EVENT_MAP,
    SUPPORTED_EVENT_TEXT,
    format_time_millis,
    normalize_event_input,
)


async def handle(plugin, event: AstrMessageEvent):
    """LastCubeX 总榜
    用法:
    /lc总榜 [项目]
    /lc总榜 333
    """
    cmd_tokens = plugin.parse_commands(event.message_str)
    event_input = cmd_tokens.get(1)

    if not event_input:
        yield event.plain_result(
            "要写项目参数哦\n"
            "用法：/lc总榜 [项目]\n"
            f"支持项目：{SUPPORTED_EVENT_TEXT}"
        ).use_t2i(False)
        return

    normalized_event = normalize_event_input(event_input)
    if not normalized_event or normalized_event not in EVENT_MAP:
        yield event.plain_result(
            "暂不支持这个项目哦\n"
            f"支持项目：{SUPPORTED_EVENT_TEXT}"
        ).use_t2i(False)
        return

    try:
        result = await plugin.lastcubex_client.get_all_ranking(normalized_event)
        if result.get("code") != 200:
            error_msg = result.get("message", "未知错误")
            yield event.plain_result(
                f"获取 LastCubeX 总榜失败\n错误：{error_msg}"
            ).use_t2i(False)
            return

        leaderboard = (result.get("data") or {}).get("leaderboard", []) or []
        if not leaderboard:
            yield event.plain_result(
                f"Last cube {normalized_event} 总榜暂时还没有成绩"
            ).use_t2i(False)
            return

        lines = [f"Last cube {normalized_event} 总榜如下："]
        for item in leaderboard:
            rank = item.get("rank", "-")
            nickname = item.get("nickname") or "未知用户"
            avg_text = format_time_millis(item.get("avg"))
            lines.append(f"{rank}. {nickname}  {avg_text}")

        yield event.plain_result("\n".join(lines)).use_t2i(False)
    except Exception as exc:
        logger.error(f"LastCubeX 总榜命令异常: {exc}")
        yield event.plain_result(f"哎呀，出错了呢：{str(exc)} 啦！").use_t2i(False)
