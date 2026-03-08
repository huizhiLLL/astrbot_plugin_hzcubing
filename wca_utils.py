import sys
from importlib import import_module
from pathlib import Path

from astrbot.api import logger

WCAQuery = None
format_wca_cs_time = None
WCA_EVENT_CODES: set[str] = set()

ONE_EVENT_TO_WCA: dict[str, str] = {
    "333": "333",
    "222": "222",
    "444": "444",
    "555": "555",
    "666": "666",
    "777": "777",
    "333oh": "333oh",
    "333bf": "333bf",
    "444bf": "444bf",
    "555bf": "555bf",
    "333mbf": "333mbf",
    "333mbld": "333mbf",
    "333fm": "333fm",
    "py": "py",
    "pyram": "py",
    "sk": "sk",
    "skewb": "sk",
    "sq1": "sq1",
    "clock": "clock",
    "minx": "minx",
    "meg": "minx",
}

NUMBER_FORMAT_EVENTS: set[str] = {"333fm"}


def one_time_to_centiseconds(time_value: int | None) -> int | None:
    """将 one 平台的 mmsscc 编码转为厘秒，用于比较"""
    if not time_value or time_value == 999999:
        return None
    try:
        value_str = str(int(time_value)).zfill(6)
        minutes = int(value_str[:2])
        seconds = int(value_str[2:4])
        centi = int(value_str[4:6])
        total_centis = (minutes * 60 + seconds) * 100 + centi
        return total_centis if total_centis > 0 else None
    except (ValueError, TypeError):
        return None


def one_value_to_number_or_centiseconds(time_value: int | None, event_code: str) -> int | None:
    """将 one 平台的值转换为数字（步数）或厘秒（时间）
    
    对于步数格式的项目（如333fm），one平台以mmsscc格式存储（如2300表示00:23.00，即23.00步），
    需要转换为实际步数（23）。
    对于时间格式的项目，转换为厘秒。
    """
    if not time_value or time_value == 999999:
        return None
    
    if event_code in NUMBER_FORMAT_EVENTS:
        try:
            value_int = int(time_value)
            if value_int < 100:
                return value_int if value_int > 0 else None
            
            value_str = str(value_int).zfill(6)
            minutes = int(value_str[:2])
            seconds = int(value_str[2:4])
            if minutes == 0:
                return seconds if seconds > 0 else None
            return None
        except (ValueError, TypeError):
            return None
    return one_time_to_centiseconds(time_value)


def normalize_one_event_code(event_code: str | None) -> str | None:
    """规范化 one 项目代码到 WCA 代码并过滤非 WCA 项目"""
    if not event_code:
        return None
    mapped = ONE_EVENT_TO_WCA.get(event_code.lower())
    if not mapped:
        return None
    mapped_lower = mapped.lower()
    if mapped_lower in WCA_EVENT_CODES:
        return mapped_lower
    return None


def normalize_wca_event_id(event_id: str | None) -> str | None:
    """将 WCA 数据库中的 eventId 规范化为统一代码（例如 pyram -> py, skewb -> sk）"""
    if not event_id:
        return None
    e = event_id.lower()
    if e == "pyram":
        return "py"
    if e == "skewb":
        return "sk"
    return e


def ensure_wca_query(plugin) -> tuple[bool, str | None]:
    global WCAQuery, format_wca_cs_time, WCA_EVENT_CODES

    if WCAQuery is None or format_wca_cs_time is None or not WCA_EVENT_CODES:
        try:
            mod = import_module("astrbot_plugin_wca.wca_query")
        except ImportError:
            try:
                wca_dir = str((Path(__file__).resolve().parent.parent / "astrbot_plugin_wca").resolve())
                if wca_dir not in sys.path:
                    sys.path.insert(0, wca_dir)
                mod = import_module("wca_query")
            except Exception as e:
                logger.error(f"导入 WCA 模块失败: {e}")
                return False, "未找到 WCA 插件，请先安装/启用 astrbot_plugin_wca"

        try:
            WCAQuery = getattr(mod, "WCAQuery", None)
            format_wca_cs_time = getattr(mod, "format_wca_time", None)
            event_id_map = getattr(mod, "EVENT_ID_MAP", {})
            WCA_EVENT_CODES = {
                normalize_wca_event_id(str(k)) or str(k)
                for k in event_id_map.keys()
            }
        except Exception as e:
            logger.error(f"WCA 模块属性获取失败: {e}")
            return False, "WCA 插件接口不完整，无法进行 PR 查询"

    if plugin.wca_query:
        return True, None
    try:
        if WCAQuery is None:
            return False, "WCA 查询类未加载"
        plugin.wca_query = WCAQuery()
        return True, None
    except Exception as e:
        logger.error(f"WCA 查询器初始化失败: {e}")
        return False, "初始化 WCA 查询失败，请稍后重试"
