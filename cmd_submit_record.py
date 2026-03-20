from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from .group_policy import is_group_allowed
from .hzcubing import (
    EVENT_NAME_MAP,
    EXTRA_EVENT_NAMES,
    OFFICIAL_EVENT_CODES,
    format_time_seconds,
    normalize_meme_event_input,
)


async def handle(plugin, event: AstrMessageEvent):
    """录入成绩 - 通过已绑定的QQ号提交成绩
    用法:
    /录入 [项目] <单次成绩> <平均成绩>
    示例: /录入 333 2.22 3.32
    示例: /录入 三阶 1:23.45 -
    示例: /录入 333 2.22 -
    说明: 单次和平均至少存在一个，不录入的字段使用-代替
    """
    allowed, _ = await is_group_allowed(event)
    if not allowed:
        return

    cmd_tokens = plugin.parse_commands(event.message_str)

    event_input = cmd_tokens.get(1)
    single_time = cmd_tokens.get(2)
    average_time = cmd_tokens.get(3)
    cube = cmd_tokens.get(4)
    method = cmd_tokens.get(5)

    if not event_input:
        yield event.plain_result(
            "还没说是什么项目呢~\n"
            "用法：/录入 [项目] [单次成绩] [平均成绩]\n"
            "比如：/录入 333 2.22 3.32 哦！"
        ).use_t2i(False)
        return

    if (not single_time or single_time == "-") and (not average_time or average_time == "-"):
        yield event.plain_result(
            "单次成绩和平均成绩至少要给一个哦~\n"
            "用法: /录入 [项目] [单次成绩] [平均成绩] [魔方] [方法]"
        ).use_t2i(False)
        return

    event_input_stripped = event_input.strip()
    normalized_event_input = normalize_meme_event_input(event_input_stripped)
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
            elif normalized_event_input in plugin.hzcubing_service.meme_events_cache:
                event_code = plugin.hzcubing_service.meme_events_cache[normalized_event_input]

    if not event_code:
        yield event.plain_result(
            f"找不到这个项目呢：{event_input}，目前只支持官方项目和已收录的整活项目哦~"
        ).use_t2i(False)
        return

    qq_id = event.get_sender_id()
    if not qq_id:
        yield event.plain_result(
            "哎呀，拿不到你的 QQ 号呢，要在 QQ 里用才行哦~"
        ).use_t2i(False)
        return

    try:
        result = await plugin.hzcubing_service.api_client.submit_record(
            qq_id=qq_id,
            event=event_code,
            single_time=single_time if single_time and single_time != "-" else None,
            average_time=average_time if average_time and average_time != "-" else None,
            cube=cube if cube and cube != "-" else None,
            method=method if method and method != "-" else None,
        )

        if result.get("code") == 200:
            data = result.get("data", {})
            event_name = data.get("event", event_code)
            single_seconds = data.get("singleSeconds")
            average_seconds = data.get("averageSeconds")
            cube_name = data.get("cube", "")
            method_name = data.get("method", "")
            nickname = data.get("nickname", "")

            is_single_gr = data.get("isSingleGR", False)
            is_average_gr = data.get("isAverageGR", False)
            prev_single_best = data.get("previousSingleBest")
            prev_average_best = data.get("previousAverageBest")

            single_text = (
                format_time_seconds(single_seconds) if single_seconds is not None else "-"
            )
            average_text = (
                format_time_seconds(average_seconds) if average_seconds is not None else "-"
            )

            response_lines = [
                f"好耶！成绩录入成功啦！✨",
                f"项目: {event_name}",
                f"单次: {single_text}",
                f"平均: {average_text}",
            ]

            if cube_name:
                response_lines.append(f"魔方: {cube_name}")
            if method_name:
                response_lines.append(f"方法: {method_name}")
            if nickname:
                response_lines.append(f"用户: {nickname}")

            base_text = "\n".join(response_lines)
            yield event.plain_result(base_text).use_t2i(False)

            gr_lines: list[str] = []

            if is_single_gr:
                if prev_single_best and isinstance(prev_single_best, dict):
                    prev_seconds = prev_single_best.get("seconds")
                    prev_nickname = (
                        prev_single_best.get("nickname")
                        or prev_single_best.get("nickName")
                        or prev_single_best.get("name")
                        or prev_single_best.get("holderNickname")
                        or "未知用户"
                    )
                    prev_time_text = (
                        format_time_seconds(prev_seconds)
                        if prev_seconds is not None
                        else "-"
                    )
                    gr_lines.append(
                        f"记录快讯！🎉恭喜 {nickname} 刷新{event_name} 单次 GR！\n"
                        f"原纪录：{prev_nickname} {prev_time_text}"
                    )
                else:
                    gr_lines.append(
                        f"记录快讯！🎉恭喜 {nickname} 拿下{event_name} 首个单次 GR！"
                    )

            if is_average_gr:
                if prev_average_best and isinstance(prev_average_best, dict):
                    prev_seconds = prev_average_best.get("seconds")
                    prev_nickname = (
                        prev_average_best.get("nickname")
                        or prev_average_best.get("nickName")
                        or prev_average_best.get("name")
                        or prev_average_best.get("holderNickname")
                        or "未知用户"
                    )
                    prev_time_text = (
                        format_time_seconds(prev_seconds)
                        if prev_seconds is not None
                        else "-"
                    )
                    gr_lines.append(
                        f"记录快讯！🎉恭喜 {nickname} 刷新{event_name} 平均 GR！\n"
                        f"原纪录：{prev_nickname} {prev_time_text}"
                    )
                else:
                    gr_lines.append(
                        f"记录快讯！🎉恭喜 {nickname} 拿下{event_name} 首个平均 GR！"
                    )

            if gr_lines:
                gr_text = "\n".join(gr_lines)
                yield event.plain_result(gr_text).use_t2i(False)
        else:
            error_msg = result.get("message", "未知错误")
            response_text = f"呜呜，成绩录入失败了呢... \n错误：{error_msg} 哦"
            yield event.plain_result(response_text).use_t2i(False)
    except Exception as e:
        logger.error(f"录入成绩命令异常: {e}")
        yield event.plain_result(f"哎呀，出错了呢：{str(e)} 啦！").use_t2i(False)
