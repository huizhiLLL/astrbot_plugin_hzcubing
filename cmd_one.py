from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from .one_api import EVENT_ID_TO_CODE


async def handle(plugin, event: AstrMessageEvent):
    """查询one平台个人记录
    用法:
    /one [姓名或oneID]
    示例: /one 李华
    示例: /one 1234
    """
    cmd_tokens = plugin.parse_commands(event.message_str)
    search_input = cmd_tokens.get(1)
    if not search_input:
        yield event.plain_result(
            "请提供姓名或 ID 哦~\n用法：/one [姓名或ID]\n比如：/one 李华 啦！"
        ).use_t2i(False)
        return

    try:
        u_id, user_name, error_msg = await plugin.one_handler._resolve_user(search_input)
        if error_msg:
            yield event.plain_result(error_msg).use_t2i(False)
            return

        if u_id is None:
            yield event.plain_result("哎呀，没拿到用户 ID 呢").use_t2i(False)
            return

        records_result = await plugin.personal_record_client.get_personal_records(u_id)

        if records_result.get("code") != 10000:
            error_msg = records_result.get("err", "未知错误")
            yield event.plain_result(f"呜呜，没拿到成绩记录呢... \n错误：{error_msg} 哦").use_t2i(False)
            return

        rank_data = records_result.get("data", {}).get("rank", [])
        if not rank_data:
            yield event.plain_result(f"{user_name or '你'} 还没有个人记录呢，快去录一个吧~").use_t2i(False)
            return

        if not user_name and rank_data:
            user_name = rank_data[0].get("u_name", "未知用户")

        if not u_id and rank_data:
            u_id = rank_data[0].get("u_id")

        header = f"{user_name}（{u_id}）在 one 平台的成绩为：\n"
        lines = []

        sorted_records = sorted(rank_data, key=lambda x: x.get("e_id", 0))

        for record in sorted_records:
            e_id = record.get("e_id")

            event_code = EVENT_ID_TO_CODE.get(e_id)
            if not event_code:
                event_code = f"项目{e_id}"

            time_single_ms = record.get("time_single")
            time_avg_ms = record.get("time_avg")

            single_time = "-"
            if time_single_ms and time_single_ms != 999999:
                single_time = plugin.one_handler.format_time_ms(time_single_ms)

            avg_time = "-"
            if time_avg_ms and time_avg_ms != 999999:
                avg_time = plugin.one_handler.format_time_ms(time_avg_ms)

            if single_time == "-" and avg_time == "-":
                continue

            lines.append(f"{event_code}  {single_time} || {avg_time}")

        if not lines:
            response_text = f"{user_name} 还没有有效个人记录呢，快去录一个吧~"
            yield event.plain_result(response_text).use_t2i(False)
        else:
            response_text = f"{header}\n" + "\n".join(lines)
            yield event.plain_result(response_text).use_t2i(False)

    except Exception as e:
        logger.error(f"个人记录查询异常: {e}")
        yield event.plain_result(f"哎呀，出错了呢：{str(e)} 啦！").use_t2i(False)
