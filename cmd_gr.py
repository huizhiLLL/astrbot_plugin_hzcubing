from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from .group_policy import is_group_allowed
from .hzcubing import (
    EXTRA_EVENT_NAMES,
    OFFICIAL_EVENT_CODES,
    OFFICIAL_EVENT_ORDER,
    format_time_seconds,
    normalize_event_code,
)


async def handle(plugin, event: AstrMessageEvent):
    """GR记录
    用法:
    /gr
    /gr [项目]
    """
    allowed, _ = await is_group_allowed(event)
    if not allowed:
        return

    cmd_tokens = plugin.parse_commands(event.message_str)
    event_code_str = cmd_tokens.get(1)
    event_code = None
    if event_code_str:
        event_code = normalize_event_code(event_code_str)
        if not event_code:
            event_input_stripped = event_code_str.strip()
            if event_input_stripped in EXTRA_EVENT_NAMES:
                event_code = event_input_stripped
            else:
                await plugin.hzcubing_service._ensure_meme_events()
                if event_input_stripped in plugin.hzcubing_service.meme_events_cache:
                    event_code = plugin.hzcubing_service.meme_events_cache[event_input_stripped]

        if not event_code:
            yield event.plain_result(f"找不到这个项目呢：{event_code_str} 啦！").use_t2i(False)
            return

    try:
        result = await plugin.hzcubing_service.api_client.best_records(event=event_code)

        if result.get("code") == 200:
            data = result.get("data", {})
            best_records = data.get("bestRecords", [])

            if not best_records:
                response_text = "GR记录\n暂无记录"
                yield event.plain_result(response_text).use_t2i(False)
            else:
                lines = []
                event_to_record = {}
                for record in best_records:
                    event_name = record.get("event", "")
                    if event_name in OFFICIAL_EVENT_CODES:
                        event_to_record[event_name] = record

                sorted_events = sorted(
                    event_to_record.keys(),
                    key=lambda x: OFFICIAL_EVENT_ORDER.index(x) if x in OFFICIAL_EVENT_ORDER else len(OFFICIAL_EVENT_ORDER)
                )

                for event_name in sorted_events:
                    record = event_to_record[event_name]
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

                    if single_text != "-" or average_text != "-":
                        if event_code:
                            lines.append(f" {event_name }  {single_text} || {average_text}")
                        else:
                            if single_text != "-" and average_text != "-":
                                lines.append(f" {event_name}  {single_nickname} {single_text} || {average_text} {average_nickname}")
                            elif single_text != "-":
                                lines.append(f" {event_name}  {single_nickname} {single_text} || -")
                            else:
                                lines.append(f" {event_name}  - || {average_text} {average_nickname}")

                if not lines:
                    response_text = "GR记录\n暂无有效记录"
                else:
                    response_text = "GR记录如下：\n\n" + "\n".join(lines)
                yield event.plain_result(response_text).use_t2i(False)
        else:
            error_msg = result.get("message", "未知错误")
            response_text = f"获取GR记录失败\n错误: {error_msg}"
            yield event.plain_result(response_text).use_t2i(False)
    except Exception as e:
        logger.error(f"GR记录命令异常: {e}")
        yield event.plain_result(f"哎呀，出错了呢：{str(e)} 啦！").use_t2i(False)
