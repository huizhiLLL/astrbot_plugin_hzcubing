import os

from astrbot.api import logger
from astrbot.api.event import AstrMessageEvent
from astrbot.api.star import Context
from astrbot.core.utils.t2i.renderer import HtmlRenderer


async def handle(event: AstrMessageEvent, context: Context):
    """生成精美的 cube 命令帮助图片"""
    yield event.plain_result("正在为您生成命令帮助图，请稍候哦...（查看原图更加清晰~）").use_t2i(False)

    # 准备命令数据
    commands_data = _prepare_commands_data()

    try:
        # 获取 t2i 配置
        cfg = context.get_config(umo=event.unified_msg_origin)
        endpoint = cfg.get("t2i_endpoint") if isinstance(cfg, dict) else None

        renderer = HtmlRenderer(endpoint_url=endpoint)
        await renderer.initialize()

        tmpl_str = _help_card_template()
        tmpl_data = _help_card_template_data(commands_data)

        image_path = await renderer.render_custom_template(
            tmpl_str,
            tmpl_data,
            return_url=False,
            options={
                "full_page": True,
                "type": "jpeg",
                "quality": 100,
                "scale": "device",
                "device_scale_factor_level": "ultra",
            },
        )

        try:
            await event.send(event.image_result(image_path))
        except Exception as send_err:
            logger.error(f"cube帮助 图片发送超时或失败: {send_err}")
            # 回退到文字版
            help_text = _format_help_text(commands_data)
            yield event.plain_result("哎呀，图片发送超时啦，先为您展示文字版吧：\n\n" + help_text).use_t2i(False)
        finally:
            if image_path and os.path.exists(image_path):
                try:
                    os.remove(image_path)
                    logger.debug(f"已清理 cube帮助 临时图片: {image_path}")
                except Exception as e:
                    logger.error(f"清理临时图片失败: {e}")

    except Exception as e:
        logger.error(f"cube帮助 图片渲染失败: {e}")
        help_text = _format_help_text(commands_data)
        yield event.plain_result("渲染图片时出了点小状况呢，先为您展示文字版吧：\n\n" + help_text).use_t2i(False)


def _prepare_commands_data() -> dict:
    """准备命令数据"""
    return {
        "title": "Cube 命令帮助",
        "subtitle": "魔方相关命令一览",
        "commands": [
            {
                "name": "/one",
                "desc": "查询 one 平台个人成绩",
                "example": "/one 李华 或 /one 1234"
            },
            {
                "name": "/wca",
                "desc": "查询 WCA 个人成绩",
                "example": "/wca 李华 或 /wca 2026LHUA01"
            },
            {
                "name": "/wcapic",
                "desc": "生成 WCA 个人纪录图片",
                "example": "/wcapic 李华"
            },
            {
                "name": "/wcapk",
                "desc": "WCA 成绩 PK 对比",
                "example": "/wcapk 李华 张伟"
            },
            {
                "name": "/宿敌",
                "desc": "查询 WCA 宿敌",
                "example": "/宿敌 李华"
            },
            {
                "name": "/pr",
                "desc": "双平台 PR 查询",
                "example": "/pr 李华 或 /pr [WCAID] [oneID]"
            },
            {
                "name": "/prpk",
                "desc": "双平台 PR PK 对比",
                "example": "/prpk 李华1 李华2"
            },
            {
                "name": "/近期比赛",
                "desc": "查询近期赛事",
                "example": "/近期比赛"
            },
        ]
    }


def _help_card_template() -> str:
    """HTML 模板 - 卡片式布局"""
    return r"""
<!DOCTYPE html>
<html lang="zh-CN">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

      * {
        box-sizing: border-box;
        margin: 0;
        padding: 0;
      }

      body {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        min-height: 100vh;
        color: #333;
      }

      .wrap {
        width: 100%;
        max-width: 800px;
        margin: 0 auto;
        padding: 32px 24px;
        background: linear-gradient(180deg, #f8faff 0%, #fffcf8 100%);
        min-height: 100vh;
      }

      /* 标题区域 */
      .header {
        text-align: center;
        margin-bottom: 32px;
      }

      .title {
        font-size: 28px;
        font-weight: 700;
        color: #002864;
        margin-bottom: 8px;
      }

      .subtitle {
        font-size: 14px;
        color: #505050;
      }

      /* 卡片网格 */
      .cards-grid {
        display: grid;
        grid-template-columns: repeat(2, 1fr);
        gap: 16px;
      }

      /* 卡片样式 */
      .card {
        background: #ffffff;
        border: 1px solid #dce1eb;
        border-radius: 10px;
        padding: 16px;
        transition: box-shadow 0.2s ease;
      }

      .card:hover {
        box-shadow: 0 4px 12px rgba(0, 90, 180, 0.1);
      }

      .card-command {
        font-size: 18px;
        font-weight: 700;
        color: #0a468c;
        margin-bottom: 6px;
      }

      .card-desc {
        font-size: 13px;
        color: #464646;
        margin-bottom: 8px;
        line-height: 1.4;
      }

      .card-example {
        font-size: 11px;
        color: #646464;
        font-family: monospace;
        background: #f0f2f8;
        padding: 4px 8px;
        border-radius: 4px;
        display: inline-block;
      }

      /* 底部提示 */
      .footer {
        text-align: center;
        margin-top: 24px;
        padding-top: 16px;
        border-top: 1px solid #e8eaef;
      }

      .footer-text {
        font-size: 12px;
        color: #646464;
      }
    </style>
  </head>
  <body>
    <div class="wrap">
      <div class="header">
        <div class="title">{{ title }}</div>
        <div class="subtitle">{{ subtitle }}</div>
      </div>

      <div class="cards-grid">
        {% for cmd in commands %}
        <div class="card">
          <div class="card-command">{{ cmd.name }}</div>
          <div class="card-desc">{{ cmd.desc }}</div>
          <div class="card-example">{{ cmd.example }}</div>
        </div>
        {% endfor %}
      </div>

      <div class="footer">
        <div class="footer-text">发送命令即可使用，如 /one 李华</div>
      </div>
    </div>
  </body>
</html>
"""


def _help_card_template_data(data: dict) -> dict:
    """模板数据"""
    return {
        "title": data.get("title", "命令帮助"),
        "subtitle": data.get("subtitle", ""),
        "commands": data.get("commands", []),
    }


def _format_help_text(data: dict) -> str:
    """格式化纯文本版本（备用）"""
    lines = [data.get("title", "命令帮助"), data.get("subtitle", ""), ""]
    for cmd in data.get("commands", []):
        lines.append(f"{cmd['name']} - {cmd['desc']}")
        lines.append(f"  例: {cmd['example']}")
        lines.append("")
    return "\n".join(lines)