from __future__ import annotations

import io
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

SCALE = 2
CANVAS_WIDTH = 1200 * SCALE
CARD_MARGIN = 42 * SCALE
CARD_PADDING_X = 34 * SCALE
HEADER_HEIGHT = 150 * SCALE
ROW_HEIGHT = 54 * SCALE
FOOTER_HEIGHT = 54 * SCALE

BG = "#F5F7FB"
CARD_BG = "#FFFFFF"
BORDER = "#E2E8F0"
HEADER_BG = "#F8FAFC"
TITLE = "#0F172A"
TEXT = "#243044"
MUTED = "#64748B"
ACCENT = "#4F46E5"
ACCENT_2 = "#0891B2"
ROW_ALT = "#F8FAFC"
TABLE_HEADER = "#EEF2FF"


class FontBook:
    def __init__(self):
        self.title = _load_font(30 * SCALE)
        self.subtitle = _load_font(17 * SCALE)
        self.body = _load_font(18 * SCALE)
        self.body_small = _load_font(16 * SCALE)
        self.metric = _load_font(20 * SCALE)


def render_user_bests_card(data: dict[str, object]) -> bytes:
    fonts = FontBook()
    rows = list(data.get("rows", []))
    row_count = max(1, len(rows))

    card_width = CANVAS_WIDTH - CARD_MARGIN * 2
    table_top = CARD_MARGIN + HEADER_HEIGHT + 28 * SCALE
    table_header_height = 46 * SCALE
    card_height = HEADER_HEIGHT + 28 * SCALE + table_header_height + row_count * ROW_HEIGHT + FOOTER_HEIGHT
    canvas_height = card_height + CARD_MARGIN * 2

    image = Image.new("RGB", (CANVAS_WIDTH, canvas_height), BG)
    draw = ImageDraw.Draw(image)

    card_box = (CARD_MARGIN, CARD_MARGIN, CARD_MARGIN + card_width, CARD_MARGIN + card_height)
    draw.rounded_rectangle(card_box, radius=20 * SCALE, fill=CARD_BG, outline=BORDER, width=2 * SCALE)
    _draw_header(draw, data, fonts, card_box)

    columns = _columns_from_ratios(
        [
            ("项目", 2.2),
            ("单次", 1),
            ("平均", 1),
        ],
        card_width - CARD_PADDING_X * 2,
    )
    table_left = CARD_MARGIN + CARD_PADDING_X
    _draw_table(draw, rows, fonts, table_left, table_top, columns, table_header_height)
    _draw_footer(draw, data, fonts, card_box)

    output = io.BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def _draw_header(
    draw: ImageDraw.ImageDraw,
    data: dict[str, object],
    fonts: FontBook,
    card_box: tuple[int, int, int, int],
) -> None:
    left, top, right, _ = card_box
    draw.rounded_rectangle(
        (left, top, right, top + HEADER_HEIGHT),
        radius=20 * SCALE,
        fill=HEADER_BG,
    )
    draw.rectangle((left, top + HEADER_HEIGHT - 20 * SCALE, right, top + HEADER_HEIGHT), fill=HEADER_BG)
    draw.line((left, top + HEADER_HEIGHT, right, top + HEADER_HEIGHT), fill=BORDER, width=2 * SCALE)

    content_left = left + CARD_PADDING_X
    kicker_y = top + 26 * SCALE
    dot_box = (content_left, kicker_y + 4 * SCALE, content_left + 12 * SCALE, kicker_y + 16 * SCALE)
    draw.ellipse(dot_box, fill=ACCENT)
    draw.text((content_left + 22 * SCALE, kicker_y), "HZCubing · 个人最佳", font=fonts.body_small, fill=MUTED)

    display_name = str(data.get("display_name", "你"))
    draw.text((content_left, top + 58 * SCALE), display_name, font=fonts.title, fill=TITLE)

    meta_items = [
        f"QQ: {data.get('qq_id', '-')}",
        f"记录数: {data.get('record_count', '-')}",
    ]
    event_code = str(data.get("event_code", "") or "").strip()
    if event_code:
        meta_items.append(f"仅显示: {event_code}")

    pill_x = content_left
    pill_y = top + 110 * SCALE
    for item in meta_items:
        pill_w = _text_width(draw, item, fonts.body_small) + 28 * SCALE
        pill_box = (pill_x, pill_y, pill_x + pill_w, pill_y + 30 * SCALE)
        draw.rounded_rectangle(pill_box, radius=15 * SCALE, fill="#FFFFFF", outline=BORDER, width=1 * SCALE)
        draw.text((pill_x + 14 * SCALE, pill_y + 4 * SCALE), item, font=fonts.body_small, fill=TEXT)
        pill_x += pill_w + 12 * SCALE

    accent_box = (right - 112 * SCALE, top + 34 * SCALE, right - 42 * SCALE, top + 104 * SCALE)
    draw.rounded_rectangle(accent_box, radius=18 * SCALE, fill="#EEF2FF")
    draw.text((right - 93 * SCALE, top + 51 * SCALE), "PB", font=fonts.metric, fill=ACCENT)


def _draw_table(
    draw: ImageDraw.ImageDraw,
    rows: list[object],
    fonts: FontBook,
    left: int,
    top: int,
    columns: list[tuple[str, int]],
    header_height: int,
) -> None:
    table_width = sum(width for _, width in columns)
    draw.rounded_rectangle(
        (left, top, left + table_width, top + header_height),
        radius=10 * SCALE,
        fill=TABLE_HEADER,
    )
    draw.rectangle((left, top + header_height - 10 * SCALE, left + table_width, top + header_height), fill=TABLE_HEADER)

    x = left
    for index, (title, width) in enumerate(columns):
        align = "left" if index == 0 else "center"
        _draw_cell_text(draw, title, (x, top, x + width, top + header_height), fonts.body_small, MUTED, align)
        x += width

    current_top = top + header_height
    if not rows:
        _draw_cell_text(
            draw,
            "暂无有效个人记录",
            (left, current_top, left + table_width, current_top + ROW_HEIGHT),
            fonts.body,
            MUTED,
            "center",
        )
        return

    for row_index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        fill = ROW_ALT if row_index % 2 == 0 else CARD_BG
        draw.rectangle((left, current_top, left + table_width, current_top + ROW_HEIGHT), fill=fill)

        values = [
            (str(row.get("event", "-")), "left", TEXT),
            (str(row.get("single", "-")), "center", TITLE),
            (str(row.get("avg", "-")), "center", MUTED if row.get("avg") == "-" else TITLE),
        ]
        x = left
        for col_index, ((_, width), (text, align, color)) in enumerate(zip(columns, values)):
            font = fonts.body if col_index == 0 else fonts.metric
            _draw_cell_text(draw, text, (x, current_top, x + width, current_top + ROW_HEIGHT), font, color, align)
            x += width
        current_top += ROW_HEIGHT


def _draw_footer(
    draw: ImageDraw.ImageDraw,
    data: dict[str, object],
    fonts: FontBook,
    card_box: tuple[int, int, int, int],
) -> None:
    left, _, right, bottom = card_box
    footer_top = bottom - FOOTER_HEIGHT
    draw.line((left, footer_top, right, footer_top), fill=BORDER, width=1 * SCALE)
    draw.text((left + CARD_PADDING_X, footer_top + 16 * SCALE), "Generated by hzcubing", font=fonts.body_small, fill=MUTED)
    generated_at = str(data.get("generated_at", ""))
    text_w = _text_width(draw, generated_at, fonts.body_small)
    draw.text((right - CARD_PADDING_X - text_w, footer_top + 16 * SCALE), generated_at, font=fonts.body_small, fill=MUTED)


def _columns_from_ratios(ratios: list[tuple[str, float]], target_width: int) -> list[tuple[str, int]]:
    if not ratios:
        return []
    total_ratio = sum(max(0, ratio) for _, ratio in ratios)
    if total_ratio <= 0:
        width, remainder = divmod(target_width, len(ratios))
        return [(title, width + (1 if index < remainder else 0)) for index, (title, _) in enumerate(ratios)]

    widths = [(title, int(target_width * max(0, ratio) / total_ratio)) for title, ratio in ratios]
    remainder = target_width - sum(width for _, width in widths)
    for index in range(remainder):
        title, width = widths[index % len(widths)]
        widths[index % len(widths)] = (title, width + 1)
    return widths


def _draw_cell_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    font: ImageFont.ImageFont,
    fill: str,
    align: str,
    pad_x: int = 16 * SCALE,
) -> None:
    x1, y1, x2, y2 = box
    text = _fit_text(draw, str(text), font, max_width=max(20, x2 - x1 - pad_x * 2))
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    y = y1 + (y2 - y1 - text_h) / 2 - bbox[1]
    if align == "left":
        x = x1 + pad_x
    elif align == "right":
        x = x2 - pad_x - text_w
    else:
        x = x1 + (x2 - x1 - text_w) / 2
    draw.text((x, y), text, font=font, fill=fill)


def _fit_text(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> str:
    if _text_width(draw, text, font) <= max_width:
        return text
    suffix = "..."
    current = text
    while current and _text_width(draw, current + suffix, font) > max_width:
        current = current[:-1]
    return current + suffix if current else suffix


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _font_candidates():
        try:
            return ImageFont.truetype(str(path), size=size)
        except Exception:
            continue
    return ImageFont.load_default()


def _font_candidates() -> list[Path]:
    plugin_root = Path(__file__).resolve().parent.parent
    return [
        plugin_root / "assets" / "fonts" / "NotoSansSC-Regular.ttf",
        Path("C:/Windows/Fonts/msyh.ttc"),
        Path("C:/Windows/Fonts/simhei.ttf"),
        Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
        Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
    ]
