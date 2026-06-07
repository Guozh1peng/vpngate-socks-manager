# VPNGate SOCKS 出口系统技术选型

## 1. 总体结论

本项目建议采用：

```text
Python + FastAPI + SQLite
```

这是当前需求下比较合适的组合。

原因：

- 项目主要是本机或单服务器运行，不需要一开始上复杂数据库
- Python 适合做 CSV 解析、OpenVPN 进程管理、后台任务、HTTP API
- SQLite 部署简单，无需额外数据库服务
- Web 管理端可以先做轻量后台页面，避免前后端工程过重
- 后续如果节点数量、任务量、用户量变大，可以迁移到 PostgreSQL

## 2. 推荐技术栈

### 2.1 后端语言

选择：

```text
Python 3.11+
```

推荐优先使用 Python 3.11 或 3.12。

用途：

- 调用 `api/get_csv.py` 获取 VPNGate CSV
- 解析 `api/vpngate.csv`
- 解码 OpenVPN Base64 配置
- 批量测试节点连通性
- 管理 OpenVPN 进程
- 管理 SOCKS 服务进程
- 调用 `https://my.ippure.com/v1/info`
- 执行后台定时刷新、定时测试、自动切换任务

### 2.2 Web 框架

选择：

```text
FastAPI
```

原因：

- 适合写 Web API
- 支持异步任务
- 和 Pydantic 配合好，便于定义请求/响应结构
- 后续可以接 WebSocket 推送日志和任务进度
- 部署简单，可以用 Uvicorn 运行

配套：

```text
uvicorn
pydantic
python-multipart
jinja2
```

### 2.3 数据库

选择：

```text
SQLite
```

建议开启：

```sql
PRAGMA journal_mode=WAL;
PRAGMA busy_timeout=5000;
```

SQLite 负责保存：

- 节点信息
- 节点测试结果
- 出口 IP 风控信息
- 当前连接状态
- Web 设置项
- 自动刷新配置
- 自动测试配置
- 自动切换配置
- 操作日志
- 连接历史
- 自动切换历史

### 2.4 ORM / 数据访问

选择：

```text
SQLAlchemy 2.x
```

原因：

- 后续从 SQLite 迁移 PostgreSQL 成本低
- 适合管理多张表和查询条件
- 比直接写大量 SQL 更容易维护

迁移工具：

```text
Alembic
```

如果第一版想更轻，也可以先不用 Alembic，但建议从一开始保留迁移能力。

### 2.5 Web 前端

第一版建议选择：

```text
Jinja2 + HTMX + 少量原生 JavaScript
```

原因：

- 不需要单独 Node.js 前端工程
- 适合后台管理端
- 表格、筛选、按钮操作、局部刷新都能覆盖
- 开发和部署简单

后续如果页面交互复杂，再升级为：

```text
React / Vue
```

但第一版不建议一开始上完整 SPA。

### 2.6 登录认证

第一版选择：

```text
服务端 Session + Cookie
```

建议：

- 管理端默认只监听 `127.0.0.1`
- 登录成功后写入服务端 session
- Cookie 设置 `HttpOnly`
- 密码使用哈希保存
- 管理员账号从环境变量或配置文件初始化

密码哈希：

```text
passlib[bcrypt]
```

后续如果需要开放远程访问，再增加 HTTPS、CSRF、防爆破、IP 白名单。

### 2.7 后台定时任务

选择：

```text
APScheduler
```

负责：

- 定时刷新 VPNGate CSV
- 定时测试所有节点连通性
- 定时检测当前连接健康状态
- 当前连接失效后触发自动切换

为什么不用 Celery：

- 当前系统是单机管理工具
- Celery 需要 Redis/RabbitMQ，部署复杂度更高
- APScheduler 足够覆盖当前需求

### 2.8 并发测试

选择：

```text
asyncio
```

用于：

- 批量 TCP 连接测试
- 控制并发数
- 处理超时

建议实现：

- 使用 `asyncio.open_connection()` 做 TCP 连通性测试
- 使用 `asyncio.Semaphore` 限制并发
- 测试结果写入 SQLite

OpenVPN 完整连接测试不建议无限并发，需要严格限制并发数量。

### 2.9 HTTP 客户端

选择：

```text
httpx
```

用途：

- 访问 `https://my.ippure.com/v1/info`
- 检测当前 SOCKS 出口 IP 风控信息

如果需要通过 SOCKS 访问，可以使用：

```text
httpx[socks]
```

或者直接调用：

```bash
curl --socks5 127.0.0.1:1080 https://my.ippure.com/v1/info
```

第一版可以先用 `curl` 子进程验证，后续再统一为 Python HTTP 客户端。

### 2.10 OpenVPN 管理

选择：

```text
openvpn 命令行客户端 + Python subprocess
```

系统生成临时 `.ovpn` 文件后，通过 Python 启动 OpenVPN：

```bash
openvpn --config <node>.ovpn
```

Python 负责：

- 启动进程
- 读取日志
- 判断连接成功
- 断开进程
- 清理临时文件
- 记录退出原因

连接成功判断：

```text
Initialization Sequence Completed
```

### 2.11 Linux 隔离方案

选择：

```text
Linux network namespace
```

用途：

- 隔离 OpenVPN 路由
- 避免 OpenVPN 修改主机默认路由
- 支持未来多个节点同时运行
- 让不同 SOCKS 端口对应不同 VPN 出口

依赖：

```text
iproute2
iptables 或 nftables
/dev/net/tun
```

第一版可以先实现单连接，第二阶段再完整实现 namespace。

### 2.12 SOCKS 服务

优先选择：

```text
microsocks
```

原因：

- 简单
- 轻量
- 适合作为本机 SOCKS5 出口

备选：

```text
3proxy
dante-server
```

建议第一版先支持一种 SOCKS 服务，避免过度抽象。

### 2.13 日志

选择：

```text
Python logging + SQLite 操作日志表
```

日志分两类：

- 文件日志：方便排查 OpenVPN、SOCKS、后台任务问题
- 数据库日志：方便 Web 管理端展示操作历史和错误信息

建议目录：

```text
runtime/logs/
```

## 3. 数据库表设计方向

建议 SQLite 至少包含以下表：

```text
nodes
node_tests
ip_risk_results
connections
settings
jobs
operation_logs
failover_events
```

### 3.1 nodes

保存 VPNGate CSV 中解析出的节点基础信息。

核心字段：

- `id`
- `hostname`
- `ip`
- `country`
- `country_code`
- `vpngate_ping`
- `vpngate_speed`
- `sessions`
- `uptime`
- `ovpn_base64`
- `remote_host`
- `remote_port`
- `created_at`
- `updated_at`

### 3.2 node_tests

保存节点连通性测试结果。

核心字段：

- `node_id`
- `test_type`
- `status`
- `tcp_latency_ms`
- `openvpn_success`
- `socks_success`
- `error_message`
- `tested_at`

### 3.3 ip_risk_results

保存 `https://my.ippure.com/v1/info` 返回的 IP 风控信息。

核心字段：

- `node_id`
- `ip`
- `asn`
- `as_organization`
- `country`
- `country_code`
- `city`
- `timezone`
- `longitude`
- `latitude`
- `postal_code`
- `fraud_score`
- `is_residential`
- `is_broadcast`
- `user_agent`
- `checked_at`

### 3.4 connections

保存当前连接和连接历史。

核心字段：

- `node_id`
- `status`
- `socks_port`
- `openvpn_pid`
- `socks_pid`
- `namespace_name`
- `connected_at`
- `disconnected_at`
- `disconnect_reason`

### 3.5 settings

保存系统设置。

配置项包括：

- 自动刷新开关
- 自动刷新间隔
- 自动测试开关
- 自动测试间隔
- 默认 SOCKS 端口
- 自动切换开关
- 自动切换目标国家/地区
- 是否要求住宅 IP
- 最大欺诈评分
- 自动切换排序策略

### 3.6 failover_events

保存自动切换历史。

核心字段：

- `old_node_id`
- `new_node_id`
- `reason`
- `strategy`
- `candidate_count`
- `success`
- `error_message`
- `created_at`

## 4. 推荐项目结构

```text
api/
  get_csv.py
  vpngate.csv

vpn_manager/
  __init__.py
  csv_loader.py
  node_model.py
  ovpn.py
  tester.py
  ippure.py
  openvpn_runner.py
  namespace.py
  socks_runner.py
  scheduler.py
  settings.py
  database.py
  repositories.py
  services.py
  cli.py

web/
  __init__.py
  app.py
  api.py
  auth.py
  schemas.py
  templates/
  static/

runtime/
  ovpn/
  logs/
  pids/

data/
  vpn_manager.sqlite3
```

## 5. 部署方式

第一版建议使用 systemd 管理：

```text
vpn-manager.service
```

运行：

```bash
python -m web.app
```

Web 默认监听：

```text
127.0.0.1:8000
```

如果需要远程访问，建议通过 Nginx 反向代理，并开启 HTTPS。

## 6. 阶段建议

### 第一阶段

技术目标：

- Python 解析 CSV
- SQLite 存节点
- FastAPI 登录和管理页面
- TCP 连通性测试
- 节点列表展示
- 自动刷新配置
- 自动测试配置

### 第二阶段

技术目标：

- OpenVPN 连接管理
- SOCKS 出口
- `ippure` 风控检测
- 当前连接状态展示
- 日志展示

### 第三阶段

技术目标：

- network namespace 隔离
- 当前连接健康检查
- 节点失效自动切换
- 日本住宅 IP 等条件筛选
- 自动切换历史记录

## 7. 不建议第一版使用的技术

第一版不建议使用：

- PostgreSQL：当前单机系统 SQLite 足够
- Celery：需要 Redis/RabbitMQ，部署复杂
- React/Vue SPA：后台管理端第一版没必要上重前端
- Kubernetes：项目体量不需要
- 多用户权限系统：先做单管理员即可

这些技术后续可以根据规模再引入。

## 8. 最终技术选型摘要

```text
语言：Python 3.11+
Web：FastAPI
前端：Jinja2 + HTMX + 原生 JS
数据库：SQLite
ORM：SQLAlchemy 2.x
迁移：Alembic
后台任务：APScheduler
并发测试：asyncio
HTTP 客户端：httpx
VPN：OpenVPN CLI
隔离：Linux network namespace
SOCKS：microsocks
部署：systemd
```

