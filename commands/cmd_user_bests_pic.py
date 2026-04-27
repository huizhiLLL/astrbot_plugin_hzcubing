from datetime import datetime

import astrbot.api.message_components as Comp
from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from ..utils.group_policy import is_group_allowed
from ..services.hzcubing import EVENT_NAME_MAP, OFFICIAL_EVENT_CODES, OFFICIAL_EVENT_ORDER, format_time_seconds
from ..utils.cmd_target_qq import resolve_event_input, resolve_target_qq
from ..utils.pillow_cards import render_user_bests_card


def _sort_best_records(best_records: list[dict]) -> list[dict]:
    return sorted(
        best_records,
        key=lambda x: (
            OFFICIAL_EVENT_ORDER.index(x.get("event", ""))
            if x.get("event", "") in OFFICIAL_EVENT_ORDER
            else len(OFFICIAL_EVENT_ORDER)
        ),
    )


def _format_text_response(nickname: str, user_qq_id: str, event_code: str | None, best_records: list[dict]) -> str:
    if event_code:
        header = f"{nickname}（{user_qq_id}）的 {event_code} 记录在这里哦："
    else:
        header = f"{nickname}（{user_qq_id}）的个人记录在这里哦："

    lines: list[str] = []
    for record in _sort_best_records(best_records):
        event_name = record.get("event", "")
        best_single = record.get("bestSingleSeconds")
        best_average = record.get("bestAverageSeconds")

        single_text = format_time_seconds(best_single) if best_single else "-"
        average_text = format_time_seconds(best_average) if best_average else "-"
        lines.append(f"{event_name}  {single_text} || {average_text}")

    return f"{header}\n" + "\n".join(lines)


def _template_data(nickname: str, user_qq_id: str, event_code: str | None, best_records: list[dict]) -> dict:
    rows: list[dict] = []
    for record in _sort_best_records(best_records):
        event_name = record.get("event", "") or "-"
        best_single = record.get("bestSingleSeconds")
        best_average = record.get("bestAverageSeconds")

        single_text = format_time_seconds(best_single) if best_single else "-"
        average_text = format_time_seconds(best_average) if best_average else "-"

        rows.append({"event": event_name, "single": single_text, "avg": average_text})

    display_name = nickname.strip() if isinstance(nickname, str) and nickname.strip() else "你"
    generated_at = datetime.now().strftime("%Y-%m-%d %H:%M")

    return {
        "display_name": display_name,
        "qq_id": str(user_qq_id),
        "record_count": str(len(rows)),
        "event_code": event_code or "",
        "rows": rows,
        "generated_at": generated_at,
    }


def _render_pic(nickname: str, user_qq_id: str, event_code: str | None, best_records: list[dict]) -> bytes:
    return render_user_bests_card(_template_data(nickname, user_qq_id, event_code, best_records))


async def handle(plugin, event: AstrMessageEvent):
    """查询个人最佳成绩（图片版）- 通过绑定的QQ号获取该选手的个人最佳成绩

    用法:
    /个人记录图 [@某人] [项目]
    示例: /个人记录图
    示例: /个人记录图 333
    示例: /个人记录图 @某人
    示例: /个人记录图 @某人 333
    示例: /个人记录图 三阶
    （优先识别 QQ 消息里的真实艾特）
    """
    allowed, _ = await is_group_allowed(event)
    if not allowed:
        return

    # 支持 /个人记录图[@某人] [项目]，如果有@则优先查询被@的人
    event_input = resolve_event_input(event, "个人记录图")

    event_code: str | None = None

    if event_input:
        event_code = EVENT_NAME_MAP.get(event_input.strip())
        if not event_code:
            if event_input.strip() in OFFICIAL_EVENT_CODES:
                event_code = event_input.strip()
            else:
                yield event.plain_result(f"找不到这个项目呢：{event_input}").use_t2i(False)
                return

    qq_id = resolve_target_qq(event)
    if not qq_id:
        yield event.plain_result("哎呀，拿不到目标 QQ 号呢，要在 QQ 里用才行哦~").use_t2i(False)
        return

    yield event.plain_result("正在为你生成个人记录图，请稍候哦...（查看原图更加清晰~）").use_t2i(False)

    try:
        result = await plugin.hzcubing_service.api_client.get_user_bests(qq_id, event_code)

        if result.get("code") != 200:
            error_msg = result.get("message", "未知错误")
            yield event.plain_result(f"呜呜，没拿到个人记录呢... \n错误：{error_msg} 哦").use_t2i(False)
            return

        data = result.get("data", {})
        nickname = data.get("nickname", "")
        user_qq_id = data.get("qqId", qq_id)
        best_records = data.get("bestRecords", [])

        if not best_records:
            response_text = f"{nickname or '你'}（{user_qq_id}）还没有个人记录呢，快去录入一个吧~"
            yield event.plain_result(response_text).use_t2i(False)
            return

        try:
            image_bytes = _render_pic(nickname, str(user_qq_id), event_code, best_records)
            try:
                await event.send(event.chain_result([Comp.Image.fromBytes(image_bytes)]))
            except Exception as send_err:
                logger.error(f"个人记录图 发送超时或失败: {send_err}")
                pic_text = _format_text_response(nickname or "你", str(user_qq_id), event_code, best_records)
                yield event.plain_result("哎呀，图片发送超时啦，先为你展示文字版吧：\n\n" + pic_text).use_t2i(False)
        except Exception as e:
            logger.error(f"个人记录图 渲染失败: {e}")
            pic_text = _format_text_response(nickname or "你", str(user_qq_id), event_code, best_records)
            yield event.plain_result("渲染图片时出了点小状况呢，先为你展示文字版吧：\n\n" + pic_text).use_t2i(False)
    except Exception as e:
        logger.error(f"个人记录图 命令异常: {e}")
        yield event.plain_result(f"哎呀，出错了呢：{str(e)} 啦！").use_t2i(False)
