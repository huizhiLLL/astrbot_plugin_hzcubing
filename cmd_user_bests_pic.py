import os
from datetime import datetime

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from astrbot.core.utils.t2i.renderer import HtmlRenderer

from .group_policy import is_group_allowed
from .hzcubing import EVENT_NAME_MAP, OFFICIAL_EVENT_CODES, OFFICIAL_EVENT_ORDER, format_time_seconds


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


def _template() -> str:
    return r"""
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <style>
      * { box-sizing: border-box; }
      body {
        margin: 0;
        background: linear-gradient(135deg, #f8fafc 0%, #eef2ff 45%, #ecfeff 100%);
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
        color: #0f172a;
      }

      .canvas {
        width: 1200px;
        margin: 0 auto;
        padding: 48px;
      }

      .card {
        background: rgba(255, 255, 255, 0.92);
        border: 1px solid rgba(148, 163, 184, 0.28);
        border-radius: 20px;
        box-shadow: 0 22px 60px rgba(15, 23, 42, 0.10);
        overflow: hidden;
      }

      .header {
        padding: 28px 32px 18px;
        border-bottom: 1px solid rgba(148, 163, 184, 0.18);
        background: radial-gradient(1200px 260px at 20% 0%, rgba(99, 102, 241, 0.12), transparent 60%),
                    radial-gradient(900px 240px at 85% 0%, rgba(6, 182, 212, 0.10), transparent 60%);
      }

      .kicker {
        display: flex;
        align-items: center;
        gap: 10px;
        color: rgba(15, 23, 42, 0.65);
        font-size: 14px;
        letter-spacing: 0.4px;
      }

      .dot {
        width: 10px;
        height: 10px;
        border-radius: 999px;
        background: linear-gradient(135deg, #6366f1, #06b6d4);
        box-shadow: 0 8px 16px rgba(99, 102, 241, 0.22);
      }

      .title-row {
        margin-top: 10px;
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 16px;
      }

      .title {
        font-size: 28px;
        font-weight: 800;
        line-height: 1.2;
        letter-spacing: 0.2px;
      }

      .meta {
        margin-top: 10px;
        display: flex;
        gap: 12px;
        flex-wrap: wrap;
        align-items: center;
      }

      .pill {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 8px 12px;
        border-radius: 999px;
        border: 1px solid rgba(148, 163, 184, 0.28);
        background: rgba(255, 255, 255, 0.70);
        font-size: 13px;
        color: rgba(15, 23, 42, 0.75);
      }

      .pill strong {
        font-weight: 700;
        color: rgba(15, 23, 42, 0.92);
      }

      .body {
        padding: 22px 26px 30px;
      }

      .table {
        width: 100%;
        border-collapse: collapse;
        border-spacing: 0;
        overflow: hidden;
      }

      .table thead th {
        text-align: left;
        font-size: 13px;
        letter-spacing: 0.4px;
        font-weight: 700;
        color: rgba(15, 23, 42, 0.60);
        padding: 14px 14px;
        border-bottom: 1px solid rgba(148, 163, 184, 0.22);
        background: rgba(248, 250, 252, 0.65);
      }

      .table thead th.right { text-align: right; }

      .table tbody tr {
        border-bottom: 1px solid rgba(148, 163, 184, 0.12);
      }

      .table tbody tr:nth-child(odd) {
        background: rgba(255, 255, 255, 0.65);
      }

      .table tbody tr:nth-child(even) {
        background: rgba(248, 250, 252, 0.52);
      }

      .table td {
        padding: 14px 14px;
        font-size: 16px;
        color: rgba(15, 23, 42, 0.88);
      }

      .event {
        font-weight: 700;
        color: rgba(15, 23, 42, 0.92);
      }

      .right {
        text-align: right;
        font-variant-numeric: tabular-nums;
      }

      .time {
        font-weight: 800;
        color: rgba(2, 6, 23, 0.92);
      }

      .muted {
        color: rgba(15, 23, 42, 0.55);
        font-weight: 600;
      }

      .footer {
        padding: 14px 26px 18px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        color: rgba(15, 23, 42, 0.45);
        font-size: 12px;
      }

      .brand {
        letter-spacing: 0.4px;
      }
    </style>
  </head>
  <body>
    <div class="canvas">
      <div class="card">
        <div class="header">
          <div class="kicker">
            <span class="dot"></span>
            <span>HZCubing · 个人最佳</span>
          </div>
          <div class="title-row">
            <div class="title">{{ display_name }}</div>
          </div>
          <div class="meta">
            <span class="pill">QQ：<strong>{{ qq_id }}</strong></span>
            <span class="pill">记录数：<strong>{{ record_count }}</strong></span>
            {% if event_code %}
              <span class="pill">仅显示：<strong>{{ event_code }}</strong></span>
            {% endif %}
          </div>
        </div>

        <div class="body">
          <table class="table">
            <thead>
              <tr>
                <th>项目</th>
                <th class="right">单次</th>
                <th class="right">平均</th>
              </tr>
            </thead>
            <tbody>
              {% for row in rows %}
              <tr>
                <td class="event">{{ row.event }}</td>
                <td class="right time">{{ row.single }}</td>
                <td class="right {% if row.avg == '-' %}muted{% else %}time{% endif %}">{{ row.avg }}</td>
              </tr>
              {% endfor %}
            </tbody>
          </table>
        </div>

        <div class="footer">
          <span class="brand">Generated by hzcubing</span>
          <span>{{ generated_at }}</span>
        </div>
      </div>
    </div>
  </body>
</html>
"""


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


async def _render_pic(plugin, event: AstrMessageEvent, nickname: str, user_qq_id: str, event_code: str | None, best_records: list[dict]) -> str:
    cfg = plugin.context.get_config(umo=event.unified_msg_origin)
    endpoint = cfg.get("t2i_endpoint") if isinstance(cfg, dict) else None

    renderer = HtmlRenderer(endpoint_url=endpoint)
    await renderer.initialize()

    return await renderer.render_custom_template(
        _template(),
        _template_data(nickname, user_qq_id, event_code, best_records),
        return_url=False,
        options={
            "full_page": True,
            "type": "jpeg",
            "quality": 100,
            "scale": "device",
            "device_scale_factor_level": "ultra",
        },
    )


async def handle(plugin, event: AstrMessageEvent):
    """查询个人最佳成绩（图片版）- 通过绑定的QQ号获取该选手的个人最佳成绩

    用法:
    /个人记录图 [项目]
    示例: /个人记录图
    示例: /个人记录图 333
    示例: /个人记录图 三阶
    """
    allowed, _ = await is_group_allowed(event)
    if not allowed:
        return

    cmd_tokens = plugin.parse_commands(event.message_str)
    event_input = cmd_tokens.get(1)
    event_code: str | None = None

    if event_input:
        event_code = EVENT_NAME_MAP.get(event_input.strip())
        if not event_code:
            if event_input.strip() in OFFICIAL_EVENT_CODES:
                event_code = event_input.strip()
            else:
                yield event.plain_result(f"找不到这个项目呢：{event_input}").use_t2i(False)
                return

    qq_id = event.get_sender_id()
    if not qq_id:
        yield event.plain_result("哎呀，拿不到你的 QQ 号呢，要在 QQ 里用才行哦~").use_t2i(False)
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

        image_path: str | None = None
        try:
            image_path = await _render_pic(plugin, event, nickname, user_qq_id, event_code, best_records)
            try:
                await event.send(event.image_result(image_path))
            except Exception as send_err:
                logger.error(f"个人记录图 发送超时或失败: {send_err}")
                pic_text = _format_text_response(nickname or "你", str(user_qq_id), event_code, best_records)
                yield event.plain_result("哎呀，图片发送超时啦，先为你展示文字版吧：\n\n" + pic_text).use_t2i(False)
            finally:
                if image_path and os.path.exists(image_path):
                    try:
                        os.remove(image_path)
                    except Exception as e:
                        logger.error(f"清理临时图片失败: {e}")
        except Exception as e:
            logger.error(f"个人记录图 渲染失败: {e}")
            pic_text = _format_text_response(nickname or "你", str(user_qq_id), event_code, best_records)
            yield event.plain_result("渲染图片时出了点小状况呢，先为你展示文字版吧：\n\n" + pic_text).use_t2i(False)
    except Exception as e:
        logger.error(f"个人记录图 命令异常: {e}")
        yield event.plain_result(f"哎呀，出错了呢：{str(e)} 啦！").use_t2i(False)
