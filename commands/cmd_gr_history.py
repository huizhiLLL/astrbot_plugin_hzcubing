from datetime import datetime

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from ..utils.group_policy import is_group_allowed
from ..services.hzcubing import (
    EVENT_NAME_MAP,
    EXTRA_EVENT_NAMES,
    OFFICIAL_EVENT_CODES,
    format_time_seconds,
    normalize_meme_event_input,
)


def _format_date(value) -> str:
    if not value:
        return "-"
    try:
        if isinstance(value, str):
            normalized = value.replace("Z", "+00:00")
            dt = datetime.fromisoformat(normalized)
        else:
            dt = value
        return f"{dt.year}.{dt.month}.{dt.day}"
    except Exception:
        return str(value).split("T", 1)[0].replace("-", ".")


def _format_history_section(title: str, items: list[dict]) -> list[str]:
    lines = [title]
    if not items:
        lines.append("暂无")
        return lines

    for item in items:
        nickname = item.get("nickname") or "无名高手"
        time_text = format_time_seconds(item.get("seconds"))
        date_text = _format_date(item.get("timestamp"))
        lines.append(f"{nickname} {time_text} {date_text}")
    return lines


async def _resolve_event_code(plugin, event_input: str) -> str | None:
    event_input_stripped = event_input.strip()
    normalized_event_input = normalize_meme_event_input(event_input_stripped)
    event_code = EVENT_NAME_MAP.get(event_input_stripped)

    if event_code:
        return event_code
    if event_input_stripped in OFFICIAL_EVENT_CODES:
        return event_input_stripped
    if event_input_stripped in EXTRA_EVENT_NAMES:
        return event_input_stripped

    await plugin.hzcubing_service._ensure_meme_events()
    if event_input_stripped in plugin.hzcubing_service.meme_events_cache:
        return plugin.hzcubing_service.meme_events_cache[event_input_stripped]
    if normalized_event_input in plugin.hzcubing_service.meme_events_cache:
        return plugin.hzcubing_service.meme_events_cache[normalized_event_input]

    return None


async def handle(plugin, event: AstrMessageEvent):
    """GR历史
    用法:
    /gr历史 [项目]
    /gr历史 333
    /gr历史 三阶
    """
    allowed, _ = await is_group_allowed(event)
    if not allowed:
        return

    cmd_tokens = plugin.parse_commands(event.message_str)
    event_input = cmd_tokens.get(1)

    if not event_input:
        yield event.plain_result(
            "要告诉小枝查哪个项目哦~\n"
            "用法：/gr历史 [项目]\n"
            "比如：/gr历史 333"
        ).use_t2i(False)
        return

    event_code = await _resolve_event_code(plugin, event_input)
    if not event_code:
        yield event.plain_result(f"找不到这个项目呢：{event_input}").use_t2i(False)
        return

    try:
        result = await plugin.hzcubing_service.api_client.gr_history(event_code)

        if result.get("code") != 200:
            error_msg = result.get("message", "未知错误")
            yield event.plain_result(
                f"获取GR历史失败\n错误：{error_msg}"
            ).use_t2i(False)
            return

        data = result.get("data", {}) or {}
        single_history = data.get("single", []) or []
        average_history = data.get("average", []) or []

        if not single_history and not average_history:
            yield event.plain_result(f"{event_code} 暂时还没有GR历史").use_t2i(False)
            return

        lines = [f"{event_code} 的GR历史如下："]
        lines.extend(_format_history_section("单次", single_history))
        lines.extend(_format_history_section("平均", average_history))

        yield event.plain_result("\n".join(lines)).use_t2i(False)
    except Exception as e:
        logger.error(f"GR历史命令异常: {e}")
        yield event.plain_result(f"哎呀，出错了呢：{str(e)} 啦！").use_t2i(False)
