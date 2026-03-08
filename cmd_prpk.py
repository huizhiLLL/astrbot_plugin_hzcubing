from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent

from . import wca_utils
from .hzcubing import OFFICIAL_EVENT_ORDER
from .one_api import EVENT_ID_TO_CODE


async def handle(plugin, event: AstrMessageEvent):
    """PR PK：两位选手跨平台最佳成绩对比"""
    cmd_tokens = plugin.parse_commands(event.message_str)
    a1 = cmd_tokens.get(1)
    a2 = cmd_tokens.get(2)
    a3 = cmd_tokens.get(3)
    a4 = cmd_tokens.get(4)

    if not a1 or not a2:
        yield event.plain_result(
            "参数不够呢，请提供两个选手哦~\n"
            "用法：/prpk [选手1] [选手2]\n"
            "同名请用：/prpk [WCAID1] [oneID1] [WCAID2] [oneID2] 啦！"
        ).use_t2i(False)
        return

    ok, err_msg = wca_utils.ensure_wca_query(plugin)
    if not ok:
        yield event.plain_result(err_msg or "WCA 服务不可用").use_t2i(False)
        return

    yield event.plain_result("麦麦收到！正在进行pk中......").use_t2i(False)

    async def resolve_player(kw: str, forced_wca: str | None = None, forced_one: str | None = None):
        wca_person = None
        one_uid = None
        one_name = None
        wca_err = None
        one_err = None

        if forced_wca:
            persons = await plugin.wca_query.search_person(forced_wca) if plugin.wca_query else []
            if persons:
                match = [
                    p for p in persons
                    if str(p.get("person", {}).get("wca_id", "")).lower() == forced_wca.lower()
                ]
                picked = match[0] if match else persons[0]
                wca_person = picked.get("person", {}) if isinstance(picked, dict) else {}
            else:
                wca_err = f"未找到 WCA 选手: {forced_wca}"
        else:
            persons = await plugin.wca_query.search_person(kw) if plugin.wca_query else []
            if not persons:
                wca_err = f"未找到匹配的 WCA 选手: {kw}"
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
                lines.append("请使用 WCAID：/prpk <WCAID1> <oneID1> <WCAID2> <oneID2>")
                wca_err = "\n".join(lines)
            else:
                picked = persons[0]
                wca_person = picked.get("person", {}) if isinstance(picked, dict) else {}

        if forced_one:
            if forced_one.isdigit():
                one_uid = int(forced_one)
            else:
                one_err = f"oneID 无效: {forced_one}"
        else:
            one_uid, one_name, one_err = await plugin.one_handler._resolve_user(kw)

        return wca_person, one_uid, one_name, wca_err, one_err

    if a3 and a4:
        p1_kw, p2_kw = a1.strip(), a3.strip()
        w1, o1, n1, e1_w, e1_o = await resolve_player(p1_kw, forced_wca=p1_kw, forced_one=a2.strip())
        w2, o2, n2, e2_w, e2_o = await resolve_player(p2_kw, forced_wca=p2_kw, forced_one=a4.strip())
    else:
        w1, o1, n1, e1_w, e1_o = await resolve_player(a1.strip())
        w2, o2, n2, e2_w, e2_o = await resolve_player(a2.strip())

    if not w1 or not w2 or o1 is None or o2 is None:
        lines = ["无法唯一确认选手"]
        for e in (e1_w, e1_o, e2_w, e2_o):
            if e:
                lines.append(e)
        lines.append("请使用: /prpk [WCAID1] [oneID1] [WCAID2] [oneID2]")
        yield event.plain_result("\n".join(lines)).use_t2i(False)
        return

    async def fetch_one(u_id: int):
        try:
            return await plugin.personal_record_client.get_personal_records(u_id)
        except Exception as e:
            logger.error(f"PRPK one 查询异常: {e}")
            return None

    w1_id = w1.get("wca_id", "") if w1 else ""
    w2_id = w2.get("wca_id", "") if w2 else ""
    w1_name = w1.get("name", w1_id) if w1 else w1_id
    w2_name = w2.get("name", w2_id) if w2 else w2_id

    try:
        w1_records = await plugin.wca_query.get_person_best_records(w1_id) if plugin.wca_query else None
        w2_records = await plugin.wca_query.get_person_best_records(w2_id) if plugin.wca_query else None
    except Exception as e:
        logger.error(f"PRPK WCA 查询异常: {e}")
        yield event.plain_result("查询 WCA 成绩时出错，请稍后重试").use_t2i(False)
        return

    one1_resp = await fetch_one(o1)
    one2_resp = await fetch_one(o2)

    if not w1_records and not one1_resp:
        yield event.plain_result(f"{w1_name} 无成绩记录").use_t2i(False)
        return
    if not w2_records and not one2_resp:
        yield event.plain_result(f"{w2_name} 无成绩记录").use_t2i(False)
        return

    def to_one_map(resp):
        data = resp.get("data", {}).get("rank", []) if resp and resp.get("code") == 10000 else []
        one_map_s: dict[str, int | None] = {}
        one_map_a: dict[str, int | None] = {}
        for record in data:
            event_code_raw = EVENT_ID_TO_CODE.get(record.get("e_id"))
            code = wca_utils.normalize_one_event_code(event_code_raw)
            if not code:
                continue
            single_val = wca_utils.one_value_to_number_or_centiseconds(record.get("time_single"), code)
            avg_val = wca_utils.one_value_to_number_or_centiseconds(record.get("time_avg"), code)
            if single_val is not None:
                prev = one_map_s.get(code)
                one_map_s[code] = single_val if prev is None else min(prev, single_val)
            if avg_val is not None:
                prev = one_map_a.get(code)
                one_map_a[code] = avg_val if prev is None else min(prev, avg_val)
        return one_map_s, one_map_a

    def to_wca_map(records):
        single_map = {}
        avg_map = {}
        fmt_map = {}
        if not records:
            return single_map, avg_map, fmt_map
        for r in records.get("single_records", []):
            code = wca_utils.normalize_wca_event_id(str(r.get("event_id", "")))
            if code in wca_utils.WCA_EVENT_CODES:
                v = r.get("best")
                if v and v > 0:
                    single_map[code] = min(single_map.get(code, v), v) if code in single_map else v
                    fmt_map[code] = r.get("event_format", "time")
        for r in records.get("average_records", []):
            code = wca_utils.normalize_wca_event_id(str(r.get("event_id", "")))
            if code in wca_utils.WCA_EVENT_CODES:
                v = r.get("best")
                if v and v > 0:
                    avg_map[code] = min(avg_map.get(code, v), v) if code in avg_map else v
                    fmt_map.setdefault(code, r.get("event_format", "time"))
        return single_map, avg_map, fmt_map

    w1_s, w1_a, w1_fmt = to_wca_map(w1_records)
    w2_s, w2_a, w2_fmt = to_wca_map(w2_records)
    o1_s, o1_a = to_one_map(one1_resp)
    o2_s, o2_a = to_one_map(one2_resp)

    def better(v1, v2, is_number_avg=False):
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

    def build_best(single_map, avg_map, fmt_map, one_s, one_a):
        best_s = {}
        best_a = {}
        best_fmt = {}
        for code in set(single_map) | set(avg_map) | set(one_s) | set(one_a):
            is_number = code in wca_utils.NUMBER_FORMAT_EVENTS
            best_s[code] = better(single_map.get(code), one_s.get(code), is_number_avg=False)
            best_a[code] = better(avg_map.get(code), one_a.get(code), is_number_avg=is_number)
            if is_number:
                best_fmt[code] = "number"
            else:
                best_fmt[code] = fmt_map.get(code, "time")
        return best_s, best_a, best_fmt

    a_s, a_a, a_fmt = build_best(w1_s, w1_a, w1_fmt, o1_s, o1_a)
    b_s, b_a, b_fmt = build_best(w2_s, w2_a, w2_fmt, o2_s, o2_a)

    all_events = set(a_s.keys()) | set(a_a.keys()) | set(b_s.keys()) | set(b_a.keys())
    if not all_events:
        yield event.plain_result("两位选手均无有效成绩").use_t2i(False)
        return

    def cmp(v1, v2, fmt="time", is_average=False):
        def normalize_value(v):
            """统一格式：对于number格式的平均值，转换为实际步数"""
            if v is None:
                return None
            if fmt == "number" and is_average:
                if v >= 100:
                    return v / 100
                return float(v)
            return v
        
        def fmt_val(v):
            if wca_utils.format_wca_cs_time is None:
                return "-"
            if v is None:
                return "-"
            if fmt == "number" and is_average:
                if v >= 100:
                    return f"{v / 100:.2f}"
                return f"{v:.2f}"
            return wca_utils.format_wca_cs_time(v, fmt)
        
        n1 = normalize_value(v1)
        n2 = normalize_value(v2)
        
        if n1 is None and n2 is None:
            return fmt_val(v1), fmt_val(v2), 0, 0
        if n1 is not None and n2 is None:
            return fmt_val(v1), fmt_val(v2), 1, 0
        if n2 is not None and n1 is None:
            return fmt_val(v1), fmt_val(v2), 0, 1
        if n1 < n2:
            return fmt_val(v1), fmt_val(v2), 1, 0
        if n2 < n1:
            return fmt_val(v1), fmt_val(v2), 0, 1
        return fmt_val(v1), fmt_val(v2), 0, 0

    score_a = 0
    score_b = 0
    lines = [f"PR PK 结果：\n{w1_name} VS {w2_name}\n"]

    def order_key(code: str):
        if code in OFFICIAL_EVENT_ORDER:
            return (0, OFFICIAL_EVENT_ORDER.index(code))
        return (1, code)

    for code in sorted(all_events, key=order_key):
        fmt = a_fmt.get(code) or b_fmt.get(code) or "time"
        s1, s2, p1, p2 = cmp(a_s.get(code), b_s.get(code), fmt, is_average=False)
        score_a += p1
        score_b += p2
        star1 = " (☆)" if p1 > p2 else ""
        star2 = " (★)" if p2 > p1 else ""

        avg1, avg2, ap1, ap2 = cmp(a_a.get(code), b_a.get(code), fmt, is_average=True)
        score_a += ap1
        score_b += ap2
        star1_avg = " (☆)" if ap1 > ap2 else ""
        star2_avg = " (★)" if ap2 > ap1 else ""

        if (p1 or p2 or ap1 or ap2 or s1 != "-" or s2 != "-" or avg1 != "-" or avg2 != "-"):
            lines.append(f"{code}  {s1}{star1} || {s2}{star2}")
            lines.append(f"    {avg1}{star1_avg} || {avg2}{star2_avg}")

    if score_a > score_b:
        lines.append(f" 胜利(⭐) {score_a} : {score_b} 失败")
    elif score_b > score_a:
        lines.append(f"   失败 {score_a} : {score_b}(⭐) 胜利")
    else:
        lines.append(f"   {score_a} : {score_b} 平局")
    yield event.plain_result("\n".join(lines)).use_t2i(False)
