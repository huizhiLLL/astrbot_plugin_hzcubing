import asyncio
import time
from typing import Any
import aiohttp
from astrbot.api import logger

# API 配置
API_BASE_URL = "https://backend.hzcubing.club/astrobot-hzcubing"
REQUEST_TIMEOUT = 10  # 请求超时时间（秒）

# 官方项目顺序列表（用于排序）
OFFICIAL_EVENT_ORDER = [
    "333",     # 三阶速拧
    "222",     # 二阶速拧
    "333oh",   # 三阶单手
    "444",     # 四阶速拧
    "555",     # 五阶速拧
    "666",     # 六阶速拧
    "777",     # 七阶速拧
    "py",      # 金字塔
    "sk",      # 斜转
    "sq1",     # SQ1
    "clock",   # 魔表
    "meg",     # 五魔方
    "333bf",   # 三阶盲拧
    "444bf",   # 四阶盲拧
    "555bf",   # 五阶盲拧
    "333mbf",  # 多盲
    "333fm",   # 最少步
    "fto",     # FTO
]

# 官方项目代码集合（用于验证和过滤）
OFFICIAL_EVENT_CODES = set(OFFICIAL_EVENT_ORDER)

# 项目名称映射表（中文 -> 项目代码）
EVENT_NAME_MAP = {
    # 三阶速拧
    "三阶速拧": "333",
    "三阶": "333",
    "333": "333",
    "三速": "333",
    # 二阶速拧
    "二阶速拧": "222",
    "二阶": "222",
    "222": "222",
    "二速": "222",
    # 三阶单手
    "三阶单手": "333oh",
    "单手": "333oh",
    "333oh": "333oh",
    "三单": "333oh",
    # 四阶速拧
    "四阶速拧": "444",
    "四阶": "444",
    "444": "444",
    "四速": "444",
    # 五阶速拧
    "五阶速拧": "555",
    "五阶": "555",
    "555": "555",
    "五速": "555",
    # 六阶速拧
    "六阶速拧": "666",
    "六阶": "666",
    "666": "666",
    "六速": "666",
    # 七阶速拧
    "七阶速拧": "777",
    "七阶": "777",
    "777": "777",
    "七速": "777",
    # 五魔方
    "五魔方": "meg",
    "meg": "meg",
    "五魔": "meg",
    # 三阶盲拧
    "三阶盲拧": "333bf",
    "333bf": "333bf",
    "三盲": "333bf",
    # 四阶盲拧
    "四阶盲拧": "444bf",
    "444bf": "444bf",
    "四盲": "444bf",
    # 五阶盲拧
    "五阶盲拧": "555bf",
    "555bf": "555bf",
    "五盲": "555bf",
    # 最少步
    "最少步": "333fm",
    "333fm": "333fm",
    # 金字塔
    "金字塔": "py",
    "py": "py",
    "塔": "py",
    # 斜转
    "斜转": "sk",
    "sk": "sk",
    "斜": "sk",
    # SQ1
    "SQ1": "sq1",
    "sq1": "sq1",
    # 魔表
    "魔表": "clock",
    "clock": "clock",
    "表": "clock",
    # 多盲
    "多盲": "333mbf",
    "333mbf": "333mbf",
    # FTO
    "FTO": "fto",
    "fto": "fto",
}

# 额外支持的自定义项目名称（直接作为后端的 event 传递）
EXTRA_EVENT_NAMES = {
    "二阶镜面",
    "三阶镜面",
    "四阶镜面",
    "五阶镜面",
    "二阶FTO",
    "齿轮",
    "四阶华容道",
    "正阶连拧(2-7)",
    "异形连拧(5个)",
    "全项目连拧(12个)",
    "枫叶",
    "CTO",
    "REDI",
    "二重奏",
    "八阶速拧",
    "九阶速拧",
    "十阶速拧",
    "十一阶速拧",
}

from decimal import Decimal, ROUND_DOWN


def format_time_seconds(time_seconds: float | int | None) -> str:
    """格式化时间（秒数格式转换为分:秒.毫秒格式）
    
    例如：62.01 -> 1:02.01
         45.23 -> 45.23
         120.50 -> 2:00.50
         69.00 -> 1:09.00
         6.00 -> 6.00
         6.60 -> 6.60
    
    注意：
    1. 使用向下取整（舍弃第三位小数），而非四舍五入
    2. 始终保留2位小数（如果存在小数部分），不删除末尾的0
    """
    if time_seconds is None:
        return "-"
    
    try:
        # 使用 Decimal 避免浮点误差，确保向下取整时不会出现 5.52 -> 5.51 的问题
        d = Decimal(str(time_seconds))
        if d <= 0:
            return "-"

        # 向下取整到 2 位小数（舍弃第三位及以后的小数）
        d = d.quantize(Decimal("0.00"), rounding=ROUND_DOWN)

        # 统一转为「厘秒」（centiseconds，1/100 秒）的整数，后续全部用整数运算避免精度问题
        centis = int((d * 100).to_integral_exact(rounding=ROUND_DOWN))
        if centis <= 0:
            return "-"

        minutes = centis // (60 * 100)
        rem_centis = centis - minutes * 60 * 100
        seconds_int = rem_centis // 100
        centi = rem_centis % 100

        if minutes > 0:
            # 分钟部分存在：格式 M:SS.cc（始终两位小数）
            return f"{minutes}:{seconds_int:02d}.{centi:02d}"
        else:
            # 只有秒：格式 S.cc（始终两位小数）
            return f"{seconds_int}.{centi:02d}"
    except Exception:
        return "-"


def normalize_event_code(event: str) -> str | None:
    """标准化项目代码"""
    event = event.strip()
    if not event:
        return None
    if event in OFFICIAL_EVENT_CODES:
        return event
    return None


class APIClient:
    """API 客户端类"""

    def __init__(self, base_url: str = API_BASE_URL, timeout: int = REQUEST_TIMEOUT):
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: aiohttp.ClientSession | None = None

    async def _ensure_session(self):
        """确保 HTTP session 存在"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self.session

    async def _request(
        self,
        action: str,
        method: str = "GET",
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """发送 HTTP 请求"""
        session = await self._ensure_session()
        
        try:
            if method.upper() == "GET":
                async with session.get(
                    self.base_url, params=params or {}
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        text = await response.text()
                        return {
                            "code": response.status,
                            "message": f"请求失败，状态码：{response.status}",
                            "error": text,
                        }
            else:  # POST
                async with session.post(
                    self.base_url, json=data or {}
                ) as response:
                    if response.status == 200:
                        return await response.json()
                    else:
                        text = await response.text()
                        return {
                            "code": response.status,
                            "message": f"请求失败，状态码：{response.status}",
                            "error": text,
                        }
        except asyncio.TimeoutError:
            return {
                "code": 500,
                "message": "请求超时",
                "error": f"请求超时（{self.timeout.total}秒）",
            }
        except Exception as e:
            logger.error(f"API 请求异常: {e}")
            return {
                "code": 500,
                "message": "请求异常",
                "error": str(e),
            }

    async def best_records(
        self,
        event: str | None = None,
    ) -> dict[str, Any]:
        """Best Records - 各项目最佳记录（GR记录）"""
        params: dict[str, Any] = {
            "action": "best-records",
        }
        if event:
            params["event"] = event
        return await self._request("best-records", method="GET", params=params)

    async def bind_user(
        self,
        qq_id: str,
        nickname: str,
    ) -> dict[str, Any]:
        """绑定用户 - 通过昵称将QQ号与系统中的userId进行绑定"""
        params: dict[str, Any] = {
            "action": "bind-user",
            "qqId": qq_id,
            "nickname": nickname,
        }
        return await self._request("bind-user", method="GET", params=params)

    async def submit_record(
        self,
        qq_id: str,
        event: str,
        single_time: str | None = None,
        average_time: str | None = None,
        cube: str | None = None,
        method: str | None = None,
    ) -> dict[str, Any]:
        """提交成绩 - 通过已绑定的QQ号提交成绩"""
        params: dict[str, Any] = {
            "action": "submit-record",
            "qqId": qq_id,
            "event": event,
        }
        if single_time and single_time != "-":
            params["singleTime"] = single_time
        if average_time and average_time != "-":
            params["averageTime"] = average_time
        if cube and cube != "-":
            params["cube"] = cube
        if method and method != "-":
            params["method"] = method
        return await self._request("submit-record", method="GET", params=params)

    async def get_user_bests(
        self,
        qq_id: str,
        event: str | None = None,
    ) -> dict[str, Any]:
        """获取个人最佳成绩 - 通过绑定的QQ号获取该选手的个人最佳成绩"""
        params: dict[str, Any] = {
            "action": "get-user-bests",
            "qqId": qq_id,
        }
        if event:
            params["event"] = event
        return await self._request("get-user-bests", method="GET", params=params)

    async def fetch_meme_events(self) -> dict[str, Any]:
        """获取动态整活项目列表（从后端 API）"""
        url = "https://backend.hzcubing.club/meme-events"
        session = await self._ensure_session()
        try:
            async with session.get(url, params={"page": 1, "pageSize": 100}) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    return {
                        "code": response.status,
                        "message": f"请求失败，状态码：{response.status}",
                        "error": text,
                    }
        except Exception as e:
            logger.error(f"获取整活项目列表失败: {e}")
            return {
                "code": 500,
                "message": "请求异常",
                "error": str(e),
            }

    async def close(self):
        """关闭 session"""
        if self.session and not self.session.closed:
            await self.session.close()


class HZCubingService:
    """会枝 cubing 服务类，处理 GR、绑定、录入、个人记录等功能"""

    def __init__(self, api_client: APIClient):
        self.api_client = api_client
        self.meme_events_cache: dict[str, str] = {}  # eventName/eventCode -> eventCode
        self.meme_events_last_fetch = 0
        self.MEME_CACHE_DURATION = 300  # 缓存 5 分钟

    async def _ensure_meme_events(self):
        """确保整活项目缓存是最新的"""
        now = time.time()
        # 如果缓存未过期且有数据，直接使用
        if self.meme_events_cache and (now - self.meme_events_last_fetch < self.MEME_CACHE_DURATION):
            return

        try:
            result = await self.api_client.fetch_meme_events()
            if result.get("code") == 200:
                data = result.get("data", [])
                new_map = {}
                for item in data:
                    event_code = item.get("eventCode")
                    event_name = item.get("eventName")
                    if event_code:
                        new_map[event_code] = event_code
                        if event_name:
                            new_map[event_name] = event_code
                
                self.meme_events_cache = new_map
                self.meme_events_last_fetch = now
                logger.info(f"整活项目列表已更新，共 {len(data)} 个项目")
        except Exception as e:
            logger.error(f"更新整活项目缓存失败: {e}")
