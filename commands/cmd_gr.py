from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from ..utils.group_policy import is_group_allowed
from ..services.hzcubing import (
    EXTRA_EVENT_NAMES,
    OFFICIAL_EVENT_CODES,
    OFFICIAL_EVENT_ORDER,
    format_time_seconds,
)


CATEGORY_ALIASES = {
    None: "official",
    "": "official",
    "官方": "official",
    "官方项目": "official",
    "趣味": "fun",
    "趣味项目": "fun",
    "整活": "meme",
    "整活项目": "meme",
}


async def handle(plugin, event: AstrMessageEvent):
    """GR记录
    用法:
    /gr
    /gr 官方
    /gr 趣味
    /gr 整活
    """
    allowed, _ = await is_group_allowed(event)
    if not allowed:
        return

    cmd_tokens = plugin.parse_commands(event.message_str)
    category_input = (cmd_tokens.get(1) or "").strip()
    category = CATEGORY_ALIASES.get(category_input)

    if category is None:
        yield event.plain_result(
            "GR 只支持这三种看法哦~\n"
            "用法：/gr 官方\n"
            "      /gr 趣味\n"
            "      /gr 整活"
        ).use_t2i(False)
        return

    try:
        await plugin.hzcubing_service._ensure_meme_events()
        result = await plugin.hzcubing_service.api_client.best_records()

        if result.get("code") != 200:
            error_msg = result.get("message", "未知错误")
            response_text = f"获取GR记录失败\n错误: {error_msg}"
            yield event.plain_result(response_text).use_t2i(False)
            return

        data = result.get("data", {})
        best_records = data.get("bestRecords", [])
        if not best_records:
            yield event.plain_result("GR记录\n暂无记录").use_t2i(False)
            return

        meme_event_codes = {
            code.strip()
            for code in plugin.hzcubing_service.meme_events_cache.values()
            if isinstance(code, str) and code.strip()
        }

        def _match_category(event_name: str) -> bool:
            if category == "official":
                return event_name in OFFICIAL_EVENT_CODES
            if category == "fun":
                return event_name in EXTRA_EVENT_NAMES
            return event_name in meme_event_codes

        def _sort_key(event_name: str):
            if category == "official":
                if event_name in OFFICIAL_EVENT_ORDER:
                    return (0, OFFICIAL_EVENT_ORDER.index(event_name), event_name)
                return (1, 0, event_name)
            return (0, event_name)

        filtered_records = []
        for record in best_records:
            event_name = str(record.get("event", "")).strip()
            if event_name and _match_category(event_name):
                filtered_records.append(record)

        filtered_records.sort(key=lambda record: _sort_key(str(record.get("event", "")).strip()))

        lines = []
        for record in filtered_records:
            event_name = str(record.get("event", "")).strip()
            single = record.get("single")
            average = record.get("average")

            single_text = "-"
            single_nickname = ""
            if single:
                single_seconds = single.get("seconds")
                single_nickname = single.get("holderNickname") or "无名高手"
                if single_seconds is not None:
                    try:
                        single_text = format_time_seconds(float(single_seconds))
                    except (ValueError, TypeError):
                        single_text = "-"

            average_text = "-"
            average_nickname = ""
            if average:
                average_seconds = average.get("seconds")
                average_nickname = average.get("holderNickname") or "无名高手"
                if average_seconds is not None:
                    try:
                        average_text = format_time_seconds(float(average_seconds))
                    except (ValueError, TypeError):
                        average_text = "-"

            if single_text != "-" and average_text != "-":
                lines.append(f" {event_name}  {single_nickname} {single_text} || {average_text} {average_nickname}")
            elif single_text != "-":
                lines.append(f" {event_name}  {single_nickname} {single_text} || -")
            elif average_text != "-":
                lines.append(f" {event_name}  - || {average_text} {average_nickname}")

        category_title = {
            "official": "官方项目",
            "fun": "趣味项目",
            "meme": "整活项目",
        }[category]

        if not lines:
            response_text = f"{category_title}GR记录\n暂无有效记录"
        else:
            response_text = f"{category_title}GR记录如下：\n\n" + "\n".join(lines)
        yield event.plain_result(response_text).use_t2i(False)
    except Exception as e:
        logger.error(f"GR记录命令异常: {e}")
        yield event.plain_result(f"哎呀，出错了呢：{str(e)} 啦！").use_t2i(False)
