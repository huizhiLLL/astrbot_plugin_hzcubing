from __future__ import annotations

import re
from typing import Any


def _pick_first_numeric(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        text = str(int(value))
        return text if text and text != '0' else None
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return text
        m = re.search(r'(\d{5,})', text)
        if m:
            return m.group(1)
    return None


def _extract_from_segment(segment: Any) -> str | None:
    if segment is None:
        return None

    # dict-like message segment
    if isinstance(segment, dict):
        for key in ('qq', 'user_id', 'userId', 'target', 'target_id'):
            found = _pick_first_numeric(segment.get(key))
            if found:
                return found
        seg_type = str(segment.get('type') or segment.get('msg_type') or '').lower()
        data = segment.get('data') if isinstance(segment.get('data'), dict) else None
        if data:
            for key in ('qq', 'user_id', 'userId'):
                found = _pick_first_numeric(data.get(key))
                if found:
                    return found
        if seg_type in {'at', 'mention'}:
            for source in (segment, data or {}):
                for key in ('qq', 'user_id', 'userId'):
                    found = _pick_first_numeric(source.get(key))
                    if found:
                        return found

    # object-like segment
    for attr in ('qq', 'user_id', 'userId', 'target', 'target_id'):
        found = _pick_first_numeric(getattr(segment, attr, None))
        if found:
            return found

    seg_type = str(getattr(segment, 'type', '') or getattr(segment, 'msg_type', '')).lower()
    data = getattr(segment, 'data', None)
    if isinstance(data, dict):
        for key in ('qq', 'user_id', 'userId'):
            found = _pick_first_numeric(data.get(key))
            if found:
                return found
    if seg_type in {'at', 'mention'} and data:
        for key in ('qq', 'user_id', 'userId'):
            found = _pick_first_numeric(data.get(key) if isinstance(data, dict) else getattr(data, key, None))
            if found:
                return found

    return None


def resolve_target_qq(event: Any) -> str | None:
    candidates = []

    for attr in ('message_obj', 'message_obj_list', 'messages', 'message_chain', 'message'):
        value = getattr(event, attr, None)
        if isinstance(value, (list, tuple)):
            candidates.extend(value)
        elif value is not None:
            candidates.append(value)

    raw_message = getattr(event, 'message_str', None)
    if isinstance(raw_message, str) and ('@' in raw_message or '[CQ:at,' in raw_message):
        m = re.search(r'qq=(\d{5,})', raw_message)
        if m:
            return m.group(1)

    for item in candidates:
        found = _extract_from_segment(item)
        if found:
            return found

    sender_getter = getattr(event, 'get_sender_id', None)
    if callable(sender_getter):
        sender = sender_getter()
        return _pick_first_numeric(sender)

    return None
