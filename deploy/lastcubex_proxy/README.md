# LastCubeX Proxy

用于给 `astrbot_plugin_hzcubing` 提供稳定的 LastCubeX 中转接口。

## 暴露接口

- `GET /health`
- `GET /api/lastcubex/current-competition`
- `GET /api/lastcubex/current-ranking?event=333&limit=10`
- `POST /api/lastcubex/users/resolve`
- `GET /api/lastcubex/all-ranking?event=333&limit=10`
- `POST /api/lastcubex/all-ranking`

## 本地运行

```bash
docker build -t lastcubex-proxy .
docker run -d --name lastcubex-proxy -p 18081:8000 lastcubex-proxy
```

或使用 Compose：

```bash
docker compose up -d --build
```

## 说明

- 服务端负责调用 LastCubeX 上游接口并做项目映射
- `all-ranking` 响应已补齐昵称，AstrBot 插件无需再请求上游用户接口
- 内置 180 秒内存缓存，降低高频重复查询对上游的影响

## GitHub Actions 自动部署

如果仓库启用了 GitHub Actions，可以在仓库 Secrets 中配置以下变量，让 `deploy/lastcubex_proxy/` 目录变更后自动 SSH 到服务器执行更新：

- `LASTCUBEX_PROXY_HOST`
- `LASTCUBEX_PROXY_USER`
- `LASTCUBEX_PROXY_SSH_PRIVATE_KEY`
- `LASTCUBEX_PROXY_PORT`
- `LASTCUBEX_PROXY_DEPLOY_PATH`

其中 `LASTCUBEX_PROXY_DEPLOY_PATH` 应该指向服务器上的中转服务部署目录，例如 `/opt/lastcubex-proxy`。workflow 会把 `deploy/lastcubex_proxy/` 子目录内容上传到这个目录，再执行 `docker compose up -d --build`。
