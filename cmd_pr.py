from typing import Any

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from . import wca_utils
from .one_api import EVENT_ID_TO_CODE


async def handle(plugin, event: AstrMessageEvent):
    """PR 查询：合并 WCA 与 one 的最佳成绩（按更好者保留）"""
    cmd_tokens = plugin.parse_commands(event.message_str)
    arg1 = cmd_tokens.get(1)
    arg2 = cmd_tokens.get(2)

    if not arg1:
        yield event.plain_result(
            "哎呀，请提供参数哦~\n"
            "用法：/pr [姓名]\n"
            "如果有同名选手，请用：/pr [WCAID] [oneID] 啦！\n"
            "示例：/pr 2026LIHUA01 1234"
        ).use_t2i(False)
        return

    ok, err_msg = wca_utils.ensure_wca_query(plugin)
    if not ok:
        yield event.plain_result(err_msg or "WCA 服务不可用").use_t2i(False)
        return

    wca_person: dict[str, Any] | None = None
    wca_error: str | None = None
    one_user_id: int | None = None
    one_user_name: str | None = None
    one_error: str | None = None
    search_input = arg1.strip()

    if arg2:
        wca_id_input = search_input
        one_id_input = arg2.strip()

        persons = await plugin.wca_query.search_person(wca_id_input) if plugin.wca_query else []
        if persons:
            match = [
                p for p in persons
                if str(p.get("person", {}).get("wca_id", "")).lower() == wca_id_input.lower()
            ]
            picked = match[0] if match else persons[0]
            wca_person = picked.get("person", {}) if isinstance(picked, dict) else {}
        else:
            wca_error = f"未找到 WCA 选手: {wca_id_input}"

        if one_id_input.isdigit():
            one_user_id = int(one_id_input)
        else:
            one_error = f"oneID 无效: {one_id_input}"
    else:
        persons = await plugin.wca_query.search_person(search_input) if plugin.wca_query else []
        if not persons:
            wca_error = f"未找到匹配的 WCA 选手: {search_input}"
        elif len(persons) > 1:
            lines = ["找到多个匹配的 WCA 选手，请使用 WCAID："]
            for i, p in enumerate(persons[:10], 1):
                person_info = p.get("person", {}) if isinstance(p, dict) else {}
                pid = person_info.get("wca_id", "未知")
                name = person_info.get("name", "未知")
                country = person_info.get("country_iso2", "")
                country_part = f" [{country}]" if country else ""
                lines.append(f"{i}. {name} ({pid}){country_part}")
            if len(persons) > 10:
                lines.append(f"... 还有 {len(persons) - 10} 个结果未显示")
            wca_error = "\n".join(lines)
        else:
            picked = persons[0]
            wca_person = picked.get("person", {}) if isinstance(picked, dict) else {}

        one_user_id, one_user_name, one_error = await plugin.one_handler._resolve_user(search_input)

    if not wca_person or one_user_id is None:
        lines = ["无法唯一确认选手"]
        if wca_error:
            lines.append(wca_error)
        if one_error:
            lines.append(one_error)
        lines.append("请使用: /pr [WCAID] [oneID]")
        yield event.plain_result("\n".join(lines)).use_t2i(False)
        return

    wca_id = wca_person.get("wca_id")
    wca_name = wca_person.get("name", wca_id)

    try:
        wca_records = await plugin.wca_query.get_person_best_records(wca_id) if plugin.wca_query else None
    except Exception as e:
        logger.error(f"WCA PR 查询异常: {e}")
        yield event.plain_result("查询 WCA 成绩时出错，请稍后重试").use_t2i(False)
        return

    if not wca_records:
        yield event.plain_result(f"未找到 {wca_name} ({wca_id}) 的 WCA 成绩记录").use_t2i(False)
        return

    try:
        one_records_resp = await plugin.personal_record_client.get_personal_records(one_user_id)
    except Exception as e:
        logger.error(f"one PR 查询异常: {e}")
        yield event.plain_result("查询 one 成绩时出错，请稍后重试").use_t2i(False)
        return

    if one_records_resp.get("code") != 10000:
        one_error = one_records_resp.get("err", "未知错误")
        yield event.plain_result(f"获取 one 成绩失败\n错误: {one_error}").use_t2i(False)
        return

    one_rank_data = one_records_resp.get("data", {}).get("rank", []) or []
    if not one_user_name and one_rank_data:
        one_user_name = one_rank_data[0].get("u_name")
    one_display_name = one_user_name or str(one_user_id)

    wca_map: dict[str, dict[str, Any]] = {}
    def push_wca(event_code: str, field: str, value: int | None, fmt: str, rank: int):
        if value is None or value <= 0:
            return
        code = wca_utils.normalize_wca_event_id(event_code)
        if not code:
            return
        entry = wca_map.setdefault(code, {"single": None, "average": None, "format": fmt, "rank": rank})
        entry["format"] = entry.get("format") or fmt
        entry["rank"] = min(entry.get("rank", rank), rank)
        current = entry.get(field)
        entry[field] = value if current is None else min(current, value)

    for record in wca_records.get("single_records", []):
        code = wca_utils.normalize_wca_event_id(str(record.get("event_id", "")))
        fmt = record.get("event_format", "time")
        rank = record.get("event_rank", 999)
        best = record.get("best")
        if code in wca_utils.WCA_EVENT_CODES:
            push_wca(code, "single", best if best and best > 0 else None, fmt, rank)

    for record in wca_records.get("average_records", []):
        code = wca_utils.normalize_wca_event_id(str(record.get("event_id", "")))
        fmt = record.get("event_format", "time")
        rank = record.get("event_rank", 999)
        best = record.get("best")
        if code in wca_utils.WCA_EVENT_CODES:
            push_wca(code, "average", best if best and best > 0 else None, fmt, rank)

    one_map: dict[str, dict[str, Any]] = {}
    for record in one_rank_data:
        event_code_raw = EVENT_ID_TO_CODE.get(record.get("e_id"))
        code = wca_utils.normalize_one_event_code(event_code_raw)
        if not code:
            continue
        single_val = wca_utils.one_value_to_number_or_centiseconds(record.get("time_single"), code)
        avg_val = wca_utils.one_value_to_number_or_centiseconds(record.get("time_avg"), code)
        entry = one_map.setdefault(code, {"single": None, "average": None})
        if single_val is not None:
            entry["single"] = single_val if entry["single"] is None else min(entry["single"], single_val)
        if avg_val is not None:
            entry["average"] = avg_val if entry["average"] is None else min(entry["average"], avg_val)

    def better(v1: int | None, v2: int | None, is_number_avg: bool = False) -> int | None:
        """比较两个值，返回更好的（更小的）值
        对于number格式的平均值，需要先统一格式再比较
        """
        if v1 is None:
            return v2
        if v2 is None:
            return v1
        
        if is_number_avg:
            n1 = v1 / 100 if v1 >= 100 else float(v1)
            n2 = v2 / 100 if v2 >= 100 else float(v2)
            if n1 <= n2:
                return v1
            return v2
        
        return v1 if v1 <= v2 else v2

    def format_value(val: int | None, fmt: str, is_average: bool = False) -> str:
        if val is None:
            return "-"
        try:
            if wca_utils.format_wca_cs_time is None:
                return "-"
            if fmt == "number" and is_average:
                if val >= 100:
                    return f"{val / 100:.2f}"
                return f"{val:.2f}"
            return wca_utils.format_wca_cs_time(val, fmt)
        except Exception:
            return "-"

    all_events = set(wca_map.keys()) | set(one_map.keys())
    if not all_events:
        yield event.plain_result("两个平台均无有效成绩").use_t2i(False)
        return

    def sort_key(code: str):
        rank = wca_map.get(code, {}).get("rank", 999)
        return (rank, code)

    sorted_events = sorted(all_events, key=sort_key)
    lines: list[str] = []
    for code in sorted_events:
        if code in wca_utils.NUMBER_FORMAT_EVENTS:
            fmt = "number"
        else:
            fmt = wca_map.get(code, {}).get("format", "time")
        is_number = code in wca_utils.NUMBER_FORMAT_EVENTS
        best_single = better(wca_map.get(code, {}).get("single"), one_map.get(code, {}).get("single"), is_number_avg=False)
        best_avg = better(wca_map.get(code, {}).get("average"), one_map.get(code, {}).get("average"), is_number_avg=is_number)
        single_text = format_value(best_single, fmt, is_average=False)
        avg_text = format_value(best_avg, fmt, is_average=True)
        if single_text == "-" and avg_text == "-":
            continue
        lines.append(f"{code}  {single_text}  ||  {avg_text}")

    header = (
        f"{wca_name}的 PR 成绩如下：\n"
    )
    yield event.plain_result(header + "\n" + "\n".join(lines)).use_t2i(False)
