import os

from astrbot.api.event import AstrMessageEvent


async def handle(event: AstrMessageEvent):
    image_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "img", "wenjun_cube.png")
    if not os.path.exists(image_path):
        yield event.plain_result(f"图片不存在：{image_path}").use_t2i(False)
        return

    try:
        await event.send(event.image_result(image_path))
    except Exception as e:
        yield event.plain_result(f"图片发送失败：{str(e)}").use_t2i(False)
