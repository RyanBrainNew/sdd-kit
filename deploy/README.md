# 共享 MCP 部署

本目录只适用于**服务端工作区/共享工作区模式**。  
如果每个人本地 clone，用 `python -m sdd.mcp.server --root . --transport stdio`，不需要部署这里。

本目录提供三种部署方式，按公司环境选一种即可：

- `docker-compose.yml`：最快试点；
- `sdd-mcp.service`：直接跑在 Linux 主机；
- `nginx.conf`：前面加 HTTPS/SSO 网关。

先复制配置：

```bash
cp deploy/registry.example.json deploy/registry.json
mkdir -p workspaces
```

把要纳管的仓库放到 `workspaces/`，或修改 `registry.json` 的绝对路径。

启动：

```bash
docker compose -f deploy/docker-compose.yml up -d --build
python sdd/mcp/smoke_client.py http://127.0.0.1:8765/mcp
```

升级：

```bash
docker compose -f deploy/docker-compose.yml build --pull
docker compose -f deploy/docker-compose.yml up -d
```

如果同事各自使用本地 clone，不要让远端 server 直接操作他们的工作区。  
见 `sdd/mcp/README.md` 的“共享部署的关键边界”。

生产环境至少要做：

- 只挂载需要的工作区，不要挂载整个 home；
- 用 SSO/API Gateway/Nginx 做认证；
- `registry.json` 只允许 SDD owner 修改；
- 升级前先看 `sdd_health` 的版本号；
- 保留 Git 里的审计证据，不要把 server 日志当唯一证据。
