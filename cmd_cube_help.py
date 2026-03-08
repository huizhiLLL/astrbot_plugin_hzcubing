from astrbot.api.event import AstrMessageEvent


async def handle(event: AstrMessageEvent):
    help_text = """
可用cube命令列表：
1. one平台个人成绩查询
    /one [姓名或ID]
    /one 李华 or /one 1234
2. wca个人成绩查询
    /wca [姓名或ID]
    /wca 李华 or /wca 2026LHUA01
3. wca个人纪录图片查询
    /wcapic [姓名或ID]
    /wcapic 李华
4. wcapk
    /wcapk [姓名或ID] [姓名或ID]
    /wcapk 李华 张伟
5. wca宿敌查询
    /宿敌 [姓名或ID]
    /宿敌 李华
6. 双平台pr查询
    /pr [姓名]
    /pr [WCAID] [oneID] （当姓名重名时使用）
7. 双平台prpk
    /prpk [姓名1] [姓名2]
    /prpk [WCAID1] [oneID1] [WCAID2] [oneID2]（当姓名重名时使用）
8. 近期赛事查询
    /近期比赛
"""
    yield event.plain_result(help_text).use_t2i(False)
