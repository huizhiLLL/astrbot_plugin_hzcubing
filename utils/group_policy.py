from astrbot.api.event import AstrMessageEvent

ALLOWED_GROUP_ID = "460507071"


async def is_group_allowed(event: AstrMessageEvent) -> tuple[bool, str | None]:
    """检查群聊是否在允许列表中
    
    Returns:
        tuple[bool, str | None]: (是否允许, 群聊ID)
        - 如果是私聊，返回 (False, None) - 不响应
        - 如果是允许的群聊，返回 (True, group_id)
        - 如果是不允许的群聊，返回 (False, group_id) - 不响应
    """
    if event.is_private_chat():
        return False, None
    
    group_id = event.message_obj.group_id if hasattr(event.message_obj, "group_id") else None
    if not group_id and hasattr(event.message_obj, "group") and event.message_obj.group:
        group_id = event.message_obj.group.group_id
    
    if not group_id:
        return False, None
    
    if group_id == ALLOWED_GROUP_ID:
        return True, group_id
    return False, group_id
