import io
import unittest

from PIL import Image

from astrbot_plugin_hzcubing.utils.pillow_cards import (
    CANVAS_WIDTH,
    _columns_from_ratios,
    render_user_bests_card,
)


class PillowCardsTest(unittest.TestCase):
    def test_render_user_bests_card_returns_valid_png(self):
        image_bytes = render_user_bests_card(
            {
                "display_name": "会枝",
                "qq_id": "3169164181",
                "record_count": "3",
                "event_code": "",
                "generated_at": "2026-04-27 12:00",
                "rows": [
                    {"event": "333", "single": "7.89", "avg": "9.87"},
                    {"event": "222", "single": "1.23", "avg": "-"},
                    {"event": "333oh", "single": "13.21", "avg": "16.09"},
                ],
            }
        )

        self.assertGreater(len(image_bytes), 8000)
        with Image.open(io.BytesIO(image_bytes)) as image:
            self.assertEqual(image.format, "PNG")
            self.assertEqual(image.size[0], CANVAS_WIDTH)
            self.assertGreaterEqual(image.size[1], 500)

    def test_columns_from_ratios_fill_target_width(self):
        columns = _columns_from_ratios([("项目", 2.2), ("单次", 1), ("平均", 1)], 1000)

        self.assertEqual(sum(width for _, width in columns), 1000)
        self.assertGreater(columns[0][1], columns[1][1])
        self.assertLessEqual(abs(columns[1][1] - columns[2][1]), 1)


if __name__ == "__main__":
    unittest.main()
