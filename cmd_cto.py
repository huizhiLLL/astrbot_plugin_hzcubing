from astrbot.api.event import AstrMessageEvent

from .cto_scramble import generate_cto_scramble


async def handle(event: AstrMessageEvent):
    scramble = generate_cto_scramble()
    yield event.plain_result(scramble).use_t2i(False)
