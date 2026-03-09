# AstrBot 魔方插件

为 AstrBot 开发的魔方相关查询插件，支持 WCA 和 one 平台成绩查询。

## 功能

- **WCA 成绩查询** - 查询选手的 WCA 官方成绩
- **one 平台查询** - 查询 one 平台成绩
- **成绩图片生成** - 生成精美的个人纪录图片
- **PK 对比** - 支持 WCA 和双平台成绩对比
- **宿敌查询** - 查询选手的 WCA 宿敌
- **赛事查询** - 查询近期比赛信息

## 命令

| 命令 | 说明 | 示例 |
|------|------|------|
| `/cube帮助` | 显示命令帮助 | `/cube帮助` |
| `/one` | 查询 one 平台成绩 | `/one 李华` |
| `/wca` | 查询 WCA 成绩 | `/wca 2026LHUA01` |
| `/wcapic` | 生成 WCA 成绩图片 | `/wcapic 李华` |
| `/wcapk` | WCA 成绩 PK | `/wcapk 李华 张伟` |
| `/宿敌` | 查询 WCA 宿敌 | `/宿敌 李华` |
| `/pr` | 双平台 PR 查询 | `/pr 李华` |
| `/prpk` | 双平台 PR PK | `/prpk 李华1 李华2` |
| `/近期比赛` | 查询近期赛事 | `/近期比赛` |

## 安装

在 AstrBot 插件目录安装：

```bash
cd astrbot/plugins
git clone https://github.com/huizhiLLL/astrbot_plugin_hzcubing.git
```

## 配置

部分功能需要配置 API 密钥，请参考插件内配置。