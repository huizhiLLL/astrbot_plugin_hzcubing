from __future__ import annotations

import re
from typing import Any

try:
    from astrbot.core.message.components import At
except Exception:  # pragma: no cover
    At = None


def _pick_first_numeric(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        text = str(int(value))
        return text if text and text != "0" else None
    if isinstance(value, str):
        text = value.strip()
        if text.isdigit():
            return text
        m = re.search(r"(\d{5,})", text)
        if m:
            return m.group(1)
    return None


def _extract_from_segment(segment: Any) -> str | None:
    if segment is None:
        return None

    if At is not None and isinstance(segment, At):
        return _pick_first_numeric(getattr(segment, "qq", None))

    if isinstance(segment, dict):
        for key in ("qq", "user_id", "userId", "target", "target_id"):
            found = _pick_first_numeric(segment.get(key))
            if found:
                return found
        seg_type = str(segment.get("type") or segment.get("msg_type") or "").lower()
        data = segment.get("data") if isinstance(segment.get("data"), dict) else None
        if data:
            for key in ("qq", "user_id", "userId"):
                found = _pick_first_numeric(data.get(key))
                if found:
                    return found
        if seg_type in {"at", "mention"}:
            for source in (segment, data or {}):
                for key in ("qq", "user_id", "userId"):
                    found = _pick_first_numeric(source.get(key))
                    if found:
                        return found

    for attr in ("qq", "user_id", "userId", "target", "target_id"):
        found = _pick_first_numeric(getattr(segment, attr, None))
        if found:
            return found

    seg_type = str(getattr(segment, "type", "") or getattr(segment, "msg_type", "")).lower()
    data = getattr(segment, "data", None)
    if isinstance(data, dict):
        for key in ("qq", "user_id", "userId"):
            found = _pick_first_numeric(data.get(key))
            if found:
                return found
    if seg_type in {"at", "mention"} and data:
        for key in ("qq", "user_id", "userId"):
            found = _pick_first_numeric(data.get(key) if isinstance(data, dict) else getattr(data, key, None))
            if found:
                return found

    return None


def _extract_from_get_messages(event: Any) -> str | None:
    getter = getattr(event, "get_messages", None)
    if not callable(getter):
        return None

    try:
        messages = getter() or []
    except Exception:
        return None

    for segment in list(messages)[1:]:
        found = _extract_from_segment(segment)
        if found:
            return found

    return None


def resolve_target_qq(event: Any) -> str | None:
    target = _extract_from_get_messages(event)
    if target:
        return target

    raw_message = getattr(event, "message_str", None)
    if isinstance(raw_message, str):
        for arg in raw_message.split():
            if arg.startswith("@") and arg[1:].isdigit():
                return arg[1:]
        m = re.search(r"qq=(\d{5,})", raw_message)
        if m:
            return m.group(1)

    candidates = []
    for attr in ("message_obj", "message_obj_list", "messages", "message_chain", "message"):
        value = getattr(event, attr, None)
        if isinstance(value, (list, tuple)):
            candidates.extend(value)
        elif value is not None:
            candidates.append(value)

    for item in candidates:
        found = _extract_from_segment(item)
        if found:
            return found

    sender_getter = getattr(event, "get_sender_id", None)
    if callable(sender_getter):
        sender = sender_getter()
        return _pick_first_numeric(sender)

    return None
