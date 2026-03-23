# AstrBot HZCubing 插件

为 AstrBot 开发的 HZCubing 社群扩展插件，聚焦社群成绩、绑定、录入、排行榜和赛赛查询。

## 命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `/gr` | 查询 GR 记录，可附带项目 | `/gr 333` |
| `/绑定` | 绑定 QQ 与站内昵称 | `/绑定 会枝` |
| `/录入` | 录入个人成绩 | `/录入 333 12.34 15.67` |
| `/个人记录` | 查询绑定 QQ 的个人记录 | `/个人记录` |
| `/个人记录图` | 生成个人记录图片 | `/个人记录图` |
| `/排行榜` | 查询项目排行榜 | `/排行榜 333 单次` |
| `/cto` | 生成 CTO 打乱 | `/cto` |
| `/俊改` | 发送俊改图片 | `/俊改` |
| `/赛赛` | 查询魔方赛赛成绩 | `/赛赛 胡泽亮` |

## 已迁移命令

以下命令已迁移到 `astrbot_plugin_wca`，请在该插件中使用：

- `/cube帮助`
- `/one`
- `/pr`
- `/prpk`

## 目录结构

- 顶层仅保留 `main.py` 与文档/元数据文件
- `commands/`：命令处理入口
- `services/`：HZCubing 平台服务
- `utils/`：群策略、目标解析、CTO 工具等通用辅助
- `integrations/caicai/`：赛赛集成
- `assets/`：静态资源

## 更新说明

- `v1.0.3`
  - 重新整理插件目录结构，移除顶层散落的命令与工具模块
  - 代码改为按 `commands/`、`services/`、`utils/`、`integrations/`、`assets/` 分类
  - 顶层只保留 `main.py` 与文档元数据文件，便于后续维护

## 安装

在 AstrBot 插件目录安装：

```bash
cd astrbot/plugins
git clone https://github.com/huizhiLLL/astrbot_plugin_hzcubing.git
```
