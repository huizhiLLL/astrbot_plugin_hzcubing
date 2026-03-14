from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent


async def handle(plugin, event: AstrMessageEvent):
    cmd_tokens = plugin.parse_commands(event.message_str)
    search_input = cmd_tokens.get(1)

    if not search_input:
        yield event.plain_result(
            "请提供姓名或 TCID 哦~\n用法：/赛赛 [姓名或TCID]\n比如：/赛赛 胡泽亮"
        ).use_t2i(False)
        return

    try:
        result = await plugin.caicai_client.query_player(search_input.strip())
        if not result.get("match"):
            matches = result.get("matches", [])
            if matches:
                lines = [f"没找到完全匹配的选手「{search_input}」呢~", "你是不是想找下面这些："]
                for idx, item in enumerate(matches[:10], 1):
                    name = item.get("name", "未知")
                    tcid = item.get("tcid", "未知TCID")
                    name_en = item.get("name_en", "")
                    extra = f" / {name_en}" if name_en else ""
                    lines.append(f"{idx}. {name}（{tcid}{extra}）")
                lines.append("可以直接用：/赛赛 TCID")
                yield event.plain_result("\n".join(lines)).use_t2i(False)
                return

        summary = result.get("summary", {})
        name = summary.get("name") or result.get("match", {}).get("name") or search_input
        tcid = summary.get("tcid") or result.get("match", {}).get("tcid") or "未知TCID"
        best_scores = summary.get("best_scores", [])

        if not best_scores:
            yield event.plain_result(f"{name}（{tcid}）在赛赛平台还没有有效成绩呢~").use_t2i(False)
            return

        lines = [f"{item['event']}  {item['best']} || {item['average']}" for item in best_scores]
        response_text = f"{name}（{tcid}）在 魔方赛赛 平台的成绩为：\n\n" + "\n".join(lines)
        yield event.plain_result(response_text).use_t2i(False)
    except RuntimeError as exc:
        message = str(exc)
        if "登录态已过期" in message:
            yield event.plain_result(message).use_t2i(False)
            return
        yield event.plain_result(f"找不到这个选手呢：{search_input}\n{message}").use_t2i(False)
    except Exception as exc:  # noqa: BLE001
        logger.error(f"赛赛查询异常: {exc}")
        yield event.plain_result(f"哎呀，出错了呢：{str(exc)} 啦！").use_t2i(False)
