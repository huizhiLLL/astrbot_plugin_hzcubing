from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from .group_policy import is_group_allowed
from .hzcubing import (
    EVENT_NAME_MAP,
    EXTRA_EVENT_NAMES,
    OFFICIAL_EVENT_CODES,
    format_time_seconds,
)


RANK_TYPE_MAP = {
    "单次": "single",
    "single": "single",
    "Single": "single",
    "平均": "average",
    "avg": "average",
    "AVG": "average",
    "average": "average",
    "Average": "average",
}


async def handle(plugin, event: AstrMessageEvent):
    """排行榜
    用法:
    /排行榜 [项目] [单次/平均]
    示例:
    /排行榜 333 单次
    /排行榜 三阶 平均
    """
    allowed, _ = await is_group_allowed(event)
    if not allowed:
        return

    cmd_tokens = plugin.parse_commands(event.message_str)
    event_input = cmd_tokens.get(1)
    rank_type_input = cmd_tokens.get(2)

    if not event_input or not rank_type_input:
        yield event.plain_result(
            "参数还没写完整哦~\n"
            "用法：/排行榜 [项目] [单次/平均]\n"
            "比如：/排行榜 333 单次"
        ).use_t2i(False)
        return

    event_input_stripped = event_input.strip()
    event_code = EVENT_NAME_MAP.get(event_input_stripped)

    if not event_code:
        if event_input_stripped in OFFICIAL_EVENT_CODES:
            event_code = event_input_stripped
        elif event_input_stripped in EXTRA_EVENT_NAMES:
            event_code = event_input_stripped
        else:
            await plugin.hzcubing_service._ensure_meme_events()
            if event_input_stripped in plugin.hzcubing_service.meme_events_cache:
                event_code = plugin.hzcubing_service.meme_events_cache[event_input_stripped]

    if not event_code:
        yield event.plain_result(
            f"找不到这个项目呢：{event_input}"
        ).use_t2i(False)
        return

    rank_type = RANK_TYPE_MAP.get(rank_type_input.strip())
    if not rank_type:
        yield event.plain_result(
            "第二个参数要写 单次 或 平均 哦~\n"
            "比如：/排行榜 333 单次"
        ).use_t2i(False)
        return

    try:
        result = await plugin.hzcubing_service.api_client.get_leaderboard(event_code, rank_type)

        if result.get("code") != 200:
            error_msg = result.get("message", "未知错误")
            yield event.plain_result(
                f"呜，排行榜没拿到呢...\n错误：{error_msg}"
            ).use_t2i(False)
            return

        data = result.get("data", {}) or {}
        leaderboard = data.get("leaderboard", []) or []
        display_type = "单次" if rank_type == "single" else "平均"

        if not leaderboard:
            yield event.plain_result(
                f"{event_code} {display_type} 暂时还没有成绩喵~"
            ).use_t2i(False)
            return

        lines = [f"{event_code} {display_type} 排行榜："]
        for item in leaderboard:
            rank = item.get("rank", "-")
            nickname = item.get("nickname") or "无名高手"
            seconds = item.get("seconds")
            time_text = format_time_seconds(seconds)
            lines.append(f"{rank}. {nickname} {time_text}")

        yield event.plain_result("\n".join(lines)).use_t2i(False)
    except Exception as e:
        logger.error(f"排行榜命令异常: {e}")
        yield event.plain_result(f"哎呀，出错了呢：{str(e)} 啦！").use_t2i(False)
