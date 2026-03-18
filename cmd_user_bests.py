from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from .group_policy import is_group_allowed
from .hzcubing import EVENT_NAME_MAP, OFFICIAL_EVENT_CODES, OFFICIAL_EVENT_ORDER, format_time_seconds
from .cmd_target_qq import resolve_event_input, resolve_target_qq


async def handle(plugin, event: AstrMessageEvent):
    """查询个人最佳成绩 - 通过绑定的QQ号获取该选手的个人最佳成绩
    
    用法:
    /个人记录 [@某人] [项目]
    示例: /个人记录
    示例: /个人记录 333
    示例: /个人记录 @某人
    示例: /个人记录 @某人 333
    （优先识别 QQ 消息里的真实艾特）
    示例: /个人记录 三阶
    """
    allowed, _ = await is_group_allowed(event)
    if not allowed:
        return

    event_input = resolve_event_input(event, "个人记录")

    event_code = None

    if event_input:
        event_code = EVENT_NAME_MAP.get(event_input.strip())
        if not event_code:
            if event_input.strip() in OFFICIAL_EVENT_CODES:
                event_code = event_input.strip()
            else:
                yield event.plain_result(
                    f"找不到这个项目呢：{event_input}"
                ).use_t2i(False)
                return

    qq_id = resolve_target_qq(event)
    if not qq_id:
        yield event.plain_result(
            "哎呀，拿不到目标 QQ 号呢，要在 QQ 里用才行哦~"
        ).use_t2i(False)
        return

    try:
        result = await plugin.hzcubing_service.api_client.get_user_bests(qq_id, event_code)

        if result.get("code") == 200:
            data = result.get("data", {})
            nickname = data.get("nickname", "")
            user_qq_id = data.get("qqId", qq_id)
            best_records = data.get("bestRecords", [])

            if not best_records:
                response_text = f"{nickname or '你'}（{user_qq_id}）还没有个人记录呢，快去录入一个吧~"
                yield event.plain_result(response_text).use_t2i(False)
                return

            if event_code:
                header = f"{nickname}（{user_qq_id}）的 {event_code} 记录在这里哦："
            else:
                header = f"{nickname}（{user_qq_id}）的个人记录在这里哦："

            lines = []
            sorted_records = sorted(
                best_records,
                key=lambda x: (
                    OFFICIAL_EVENT_ORDER.index(x.get("event", ""))
                    if x.get("event", "") in OFFICIAL_EVENT_ORDER
                    else len(OFFICIAL_EVENT_ORDER)
                )
            )

            for record in sorted_records:
                event_name = record.get("event", "")
                best_single = record.get("bestSingleSeconds")
                best_average = record.get("bestAverageSeconds")

                single_text = format_time_seconds(best_single) if best_single else "-"
                average_text = format_time_seconds(best_average) if best_average else "-"

                lines.append(f"{event_name}  {single_text} || {average_text}")

            response_text = f"{header}\n" + "\n".join(lines)
            yield event.plain_result(response_text).use_t2i(False)
        else:
            error_msg = result.get("message", "未知错误")
            response_text = f"呜呜，没拿到个人记录呢... \n错误：{error_msg} 哦"
            yield event.plain_result(response_text).use_t2i(False)
    except Exception as e:
        logger.error(f"查询个人记录命令异常: {e}")
        yield event.plain_result(f"哎呀，出错了呢：{str(e)} 啦！").use_t2i(False)
