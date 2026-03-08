import asyncio
import json
from urllib.parse import quote
from typing import Any

import aiohttp
from astrbot.api import logger

# 个人记录API配置
PERSONAL_RECORD_API_BASE = "https://ss.sxmfxh.com"
REQUEST_TIMEOUT = 10  # 请求超时时间（秒）

def format_time_ms(time_ms: int | None) -> str:
    """格式化时间（毫秒格式转换为秒格式）
    
    注意：仅适用于 one 平台接口返回的「整数毫秒」数据。
    示例：
    - 15230 -> 1:52.30
    - 1245  -> 12.45
    - 999999 或 <=0 -> 视为 DNF
    """
    if not time_ms or time_ms == 999999:
        return "DNF"
    
    try:
        time_ms_int = int(time_ms)
        if time_ms_int <= 0 or time_ms_int == 999999:
            return "DNF"
        
        time_str = str(time_ms_int).zfill(6)
        minutes = int(time_str[:2])
        seconds_str = time_str[2:4]  # 保持为字符串，确保两位数格式
        milliseconds = time_str[4:6]
        
        if minutes > 0:
            return f"{minutes}:{seconds_str}.{milliseconds}"
        else:
            return f"{int(seconds_str)}.{milliseconds}"  # 秒数部分不需要补0
    except (ValueError, TypeError):
        return "DNF"


# 项目ID到项目代码的映射表
EVENT_ID_TO_CODE = {
    1: "333",       # 三阶
    2: "222",       # 二阶
    3: "444",       # 四阶
    4: "555",       # 五阶
    5: "666",       # 六阶
    6: "777",       # 七阶
    7: "333oh",     # 三阶单手
    8: "py",        # 金字塔（与 WCA 对齐）
    9: "sk",        # 斜转（与 WCA 对齐）
    10: "minx",     # 五魔方
    11: "333bf",    # 三阶盲拧
    12: "444bf",    # 四阶盲拧
    13: "555bf",    # 五阶盲拧
    14: "333mbf",   # 三阶多盲（与 WCA 对齐）
    15: "sq1",      # SQ1
    16: "333fm",    # 最少步
    17: "clock",    # 魔表
    18: "maple",   # 枫叶
    19: "FTO",      # FTO
    20: "mirror",   # 镜面
    41: "smart333", # 智能三阶
    42: "smart3oh", # 智能三单
    43: "smart222", # 智能二阶
    61: "333oneface", # 三阶单面
    90: "package", # 参赛包
    91: "fun1", # 趣味1
    92: "fun2", # 趣味2
    93: "fun3", # 趣味3
    94: "fun4", # 趣味4
    95: "fun5", # 趣味5
    99: "funproject", # 趣味项目
    101: "stackingcups", # 竞技叠杯
    106: "threekingdoms", # 三国华容道
    114: "fourkingdoms", # 四阶华容道
}


class PersonalRecordAPIClient:
    """个人记录查询API客户端类"""

    def __init__(self, base_url: str = PERSONAL_RECORD_API_BASE, timeout: int = REQUEST_TIMEOUT):
        self.base_url = base_url
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.session: aiohttp.ClientSession | None = None

    async def _ensure_session(self):
        """确保 HTTP session 存在"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(timeout=self.timeout)
        return self.session

    async def search_user(self, search_input: str, page: int = 1, size: int = 5) -> dict[str, Any]:
        """搜索用户信息
        
        Args:
            search_input: 搜索关键词（姓名或ID）
            page: 页码，默认1
            size: 每页数量，默认5
        """
        session = await self._ensure_session()
        
        query_params = {
            "searchInput": search_input,
            "page": page,
            "size": size,
        }
        query_json = json.dumps(query_params, ensure_ascii=False)
        url = f"{self.base_url}/users/getUsers?query={quote(query_json)}"
        
        try:
            async with session.post(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    return {
                        "code": response.status,
                        "err": f"请求失败，状态码：{response.status}",
                        "error": text,
                    }
        except asyncio.TimeoutError:
            return {
                "code": 500,
                "err": "请求超时",
                "error": f"请求超时（{self.timeout.total}秒）",
            }
        except Exception as e:
            logger.error(f"搜索用户API请求异常: {e}")
            return {
                "code": 500,
                "err": "请求异常",
                "error": str(e),
            }

    async def get_personal_records(self, u_id: int) -> dict[str, Any]:
        """获取用户个人记录
        
        Args:
            u_id: 用户ID
        """
        session = await self._ensure_session()
        
        query_params = {"u_id": u_id}
        query_json = json.dumps(query_params)
        url = f"{self.base_url}/grades/getGradesAndRank?query={quote(query_json)}"
        
        try:
            async with session.post(url) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    text = await response.text()
                    return {
                        "code": response.status,
                        "err": f"请求失败，状态码：{response.status}",
                        "error": text,
                    }
        except asyncio.TimeoutError:
            return {
                "code": 500,
                "err": "请求超时",
                "error": f"请求超时（{self.timeout.total}秒）",
            }
        except Exception as e:
            logger.error(f"获取个人记录API请求异常: {e}")
            return {
                "code": 500,
                "err": "请求异常",
                "error": str(e),
            }

    async def close(self):
        """关闭 session"""
        if self.session and not self.session.closed:
            await self.session.close()


class OneRecordHandler:
    """个人记录查询"""
    
    def __init__(self, personal_record_client: PersonalRecordAPIClient, format_time_ms_func):
        """
        Args:
            personal_record_client: 个人记录API客户端
            format_time_ms_func: 格式化时间的函数
        """
        self.personal_record_client = personal_record_client
        self.format_time_ms = format_time_ms_func

    async def _resolve_user(self, search_input: str) -> tuple[int | None, str | None, str | None]:
        """解析用户（通过姓名或ID）
        
        返回: (u_id, user_name, error_message)
        如果error_message不为None，表示解析失败
        """
        search_input = search_input.strip()
        
        if search_input.isdigit():
            return int(search_input), None, None
        
        search_result = await self.personal_record_client.search_user(
            search_input, page=1, size=5
        )
        
        if search_result.get("code") != 10000:
            error_msg = search_result.get("err", "未知错误")
            return None, None, f"哎呀，搜索用户失败了呢... \n错误：{error_msg} 啦"
        
        users = search_result.get("data", [])
        if not users:
            return None, None, f"找不到这个用户呢：{search_input} 啦"
        
        exact_matches = [
            user for user in users
            if user.get("u_name") == search_input
        ]
        
        if not exact_matches:
            return None, None, (
                f"没找到完全匹配的用户「{search_input}」呢~\n"
                f"提示：姓名查询要完全匹配哦，快检查一下输入对不对啦！\n"
            )
        
        if len(exact_matches) > 1:
            lines = [f"哎呀，有好几个叫「{search_input}」的呢，请用 ID 查询哦：\n"]
            for i, user in enumerate(exact_matches, 1):
                u_id_item = user.get("u_id")
                u_name_item = user.get("u_name")
                lines.append(f"{i}. {u_name_item}（ID: {u_id_item}）")
            lines.append(f"\n使用方法: 使用ID进行查询")
            return None, None, "\n".join(lines)
        
        u_id = exact_matches[0].get("u_id")
        user_name = exact_matches[0].get("u_name")
        return u_id, user_name, None
