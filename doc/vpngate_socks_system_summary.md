# VPNGate 节点测试与 SOCKS 出口系统功能总结

## 1. 项目目标

本系统的目标是基于 `api/get_csv.py` 获取 VPNGate 节点列表文件 `api/vpngate.csv`，批量测试其中可用的 OpenVPN 节点，并允许用户手动选择某个节点进行连接。

连接成功后，系统需要在本地暴露一个 SOCKS 代理端口，让本机其他程序可以通过 SOCKS 连接到该节点，并把该 VPN 节点作为流量出口。

系统需要提供 Web 管理端。用户先进入登录界面完成身份验证，然后通过浏览器完成节点刷新、节点测试、节点筛选、手动连接、断开连接、查看日志和查看 SOCKS 出口状态等操作。

简单来说，目标流程是：

```text
获取 VPNGate CSV -> 解析节点 -> Web 管理端展示 -> 批量测速/可用性检测 -> 手动选择节点 -> OpenVPN 连接 -> 本地 SOCKS 代理出口
```

## 2. 核心功能

### 2.1 获取节点列表

系统使用现有脚本：

```text
api/get_csv.py
```

该脚本从 VPNGate 接口获取节点列表，并保存为：

```text
api/vpngate.csv
```

CSV 中包含节点基础信息和 OpenVPN 配置数据，例如：

- `HostName`
- `IP`
- `Ping`
- `Speed`
- `CountryLong`
- `CountryShort`
- `NumVpnSessions`
- `Uptime`
- `OpenVPN_ConfigData_Base64`

其中 `OpenVPN_ConfigData_Base64` 是该节点的 OpenVPN 配置文件内容，后续需要解码成 `.ovpn` 文件供 OpenVPN 使用。

### 2.2 解析 VPNGate CSV

系统需要读取 `api/vpngate.csv`，把每一行节点转换成内部节点对象。

每个节点至少应包含：

- 节点 ID
- 主机名
- IP
- 国家/地区
- VPNGate 标称 Ping
- VPNGate 标称速度
- 当前会话数
- OpenVPN 配置 Base64
- 测试状态
- 实测延迟
- 实测连接结果
- 本地 SOCKS 端口
- 出口 IP 风控检测状态
- 出口 IP
- ASN
- ASN 所属组织
- 出口国家/地区
- 出口城市
- 欺诈评分
- 是否住宅 IP
- 是否广播地址

### 2.3 批量测试节点可用性

系统需要批量测试 CSV 中的节点，筛选出可用节点。

测试可以分为几个层级：

1. 基础 TCP 连通性测试
   - 从 `.ovpn` 配置中提取 `remote <host> <port>`。
   - 尝试连接目标 IP/端口。
   - 记录连接耗时和失败原因。

2. OpenVPN 握手测试
   - 临时生成 `.ovpn` 文件。
   - 启动 OpenVPN 进行短时间连接测试。
   - 判断是否出现 `Initialization Sequence Completed`。

3. 出口可用性测试
   - OpenVPN 连接成功后，通过该连接访问测试 URL。
   - 获取出口 IP、国家/地区、响应耗时。

4. 出口 IP 风控检测
   - OpenVPN 连接成功后，通过该节点出口访问 `https://my.ippure.com/v1/info`。
   - 获取出口 IP 的网络归属、地理位置、欺诈评分和网络类型。
   - 将检测结果保存到节点测试结果中。
   - Web 管理端需要展示具体风控信息。

第一阶段可以先实现 TCP 连通性测试，后续再增加完整 OpenVPN 连接测试。

### 2.4 手动选择节点连接

测试完成后，用户可以从可用节点列表中手动选择一个节点进行连接。

系统需要支持：

- 查看节点列表
- 按国家、速度、延迟、可用状态过滤
- 查看节点详情
- 选择指定节点连接
- 查看当前连接状态
- 主动断开连接
- 切换到另一个节点

### 2.5 本地 SOCKS 出口

OpenVPN 本身不会直接提供 SOCKS 代理端口。OpenVPN 连接后只会创建 TUN/TAP 网络接口，并修改路由。

因此，如果需要让本地程序使用类似下面的方式访问：

```text
socks5://127.0.0.1:1080
```

系统需要额外启动一个 SOCKS 服务，并保证这个 SOCKS 服务的出口流量走对应的 OpenVPN 连接。

推荐设计是在 Linux 上使用 network namespace 隔离每个 VPN 连接：

```text
主机系统
  |
  |-- 本地 SOCKS 端口 127.0.0.1:1080
  |
  |-- vpn namespace
        |
        |-- OpenVPN 进程
        |-- tun0 VPN 网卡
        |-- SOCKS 服务进程
        |-- 出口流量经过 VPN 节点
```

这样可以避免 OpenVPN 修改主机全局路由，也方便未来同时运行多个 VPN 节点。

### 2.6 Web 管理端

系统需要提供 Web 管理端，作为主要操作入口。

Web 管理端需要支持：

- 刷新 VPNGate CSV 节点列表
- 配置节点自动刷新间隔
- 显示下次自动刷新节点时间
- 配置节点连通性自动测试间隔
- 显示下次自动测试节点时间
- 展示节点列表
- 按国家/地区过滤节点
- 按延迟、速度、会话数、可用状态、欺诈评分排序
- 批量测试节点
- 查看测试进度
- 查看每个节点的测试结果
- 查看每个节点的出口 IP 风控信息
- 手动连接指定节点
- 手动断开当前连接
- 切换连接节点
- 查看当前 SOCKS5 地址和端口
- 查看当前出口 IP
- 配置当前节点失效后的自动切换策略
- 查看 OpenVPN 和 SOCKS 运行日志
- 查看系统运行状态
- 查看错误原因和失败节点

Web 管理端必须提供登录界面。即使第一版只监听本地地址，也需要先登录后才能访问管理功能。

第一版可以做成单机管理页面，只监听本地地址：

```text
http://127.0.0.1:8000
```

如果后续需要远程访问，还需要进一步增加 HTTPS、访问 IP 白名单和更严格的操作审计。

### 2.7 Web 页面规划

Web 管理端建议包含以下页面或视图：

1. 仪表盘
   - 当前连接状态
   - 当前节点
   - 当前 SOCKS5 地址
   - 当前出口 IP
   - 已加载节点数
   - 可用节点数
   - 测试任务状态
   - 节点自动刷新状态
   - 上次刷新节点时间
   - 下次刷新节点时间
   - 节点自动测试状态
   - 上次测试节点时间
   - 下次测试节点时间

2. 节点列表
   - 表格展示所有节点
   - 支持搜索、过滤、排序
   - 支持选择节点进行连接
   - 支持查看节点详情
   - 展示出口 IP
   - 展示 ASN 组织
   - 展示出口国家/地区和城市
   - 展示欺诈评分
   - 展示是否住宅 IP
   - 展示是否广播地址

3. 节点测试
   - 启动批量测试
   - 设置测试数量、国家/地区、并发数、超时时间
   - 展示测试进度
   - 展示成功、失败、超时数量
   - 展示出口 IP 风控检测进度
   - 展示欺诈评分统计

4. 当前连接
   - 当前连接节点信息
   - OpenVPN 状态
   - SOCKS 服务状态
   - namespace 状态
   - 出口 IP 检测结果
   - 出口 IP 风控信息
   - 断开连接按钮

5. 日志页面
   - OpenVPN 日志
   - SOCKS 服务日志
   - 节点测试日志
   - 系统错误日志

6. 设置页面
   - 默认 SOCKS 端口
   - 默认测试并发数
   - 默认连接超时时间
   - 节点自动刷新开关
   - 节点自动刷新间隔
   - 下次刷新节点时间
   - 节点自动测试开关
   - 节点自动测试间隔
   - 自动测试并发数
   - 自动测试超时时间
   - 下次测试节点时间
   - 当前节点失效自动切换开关
   - 自动切换目标国家/地区
   - 自动切换是否要求住宅 IP
   - 自动切换最大欺诈评分
   - 自动切换排序策略
   - OpenVPN 可执行文件路径
   - SOCKS 服务类型
   - 是否启用 network namespace

7. 登录页面
   - 用户名输入
   - 密码输入
   - 登录失败提示
   - 登录成功后跳转到仪表盘
   - 已登录用户再次访问登录页时自动跳转到仪表盘

### 2.8 Web 登录与权限

Web 管理端需要基础登录认证。

认证要求：

- 未登录用户只能访问登录页面和登录 API
- 未登录访问管理页面时自动跳转到登录页
- 登录成功后创建服务端会话或签发访问令牌
- 登录状态需要有过期时间
- 支持主动退出登录
- 登录失败需要返回明确错误，但不要泄露密码是否正确的细节
- 密码不能明文写在前端代码里
- 密码不能明文保存到配置文件中

第一版可以使用单管理员账号：

```text
admin
```

密码建议通过环境变量或本地配置文件设置。

推荐环境变量：

```bash
VPN_MANAGER_ADMIN_USER=admin
VPN_MANAGER_ADMIN_PASSWORD=<strong-password>
VPN_MANAGER_SECRET_KEY=<random-secret>
```

后续可以扩展为多用户系统，支持不同权限角色。

### 2.9 节点自动刷新

系统需要支持后台自动刷新 VPNGate 节点列表。

自动刷新逻辑：

- 用户可以在 Web 管理端设置是否启用自动刷新
- 用户可以设置自动刷新间隔
- 刷新间隔建议支持分钟级配置
- 系统根据刷新间隔定时调用 `api/get_csv.py`
- 自动刷新完成后重新加载 `api/vpngate.csv`
- 自动刷新不应中断当前已连接的 OpenVPN 节点
- 自动刷新失败时需要记录错误日志
- Web 管理端需要显示上次刷新时间和下次刷新时间

推荐配置项：

```text
auto_refresh_enabled=true
auto_refresh_interval_minutes=30
last_refresh_at=2026-06-07T15:30:00+08:00
next_refresh_at=2026-06-07T16:00:00+08:00
```

自动刷新间隔需要设置合理边界，避免过于频繁请求 VPNGate。

建议第一版限制为：

```text
最小间隔：5 分钟
默认间隔：30 分钟
最大间隔：1440 分钟
```

如果用户修改自动刷新间隔，系统应重新计算下次刷新时间。

### 2.10 节点连通性自动测试

系统需要支持后台定时测试所有节点的连通性。

该功能和“自动刷新节点”是两个独立任务：

- 自动刷新节点：定时调用 `api/get_csv.py`，更新 `api/vpngate.csv`
- 自动测试节点：定时读取当前节点列表，批量测试节点是否可连接

自动测试逻辑：

- 用户可以在 Web 管理端设置是否启用自动测试
- 用户可以设置自动测试间隔
- 用户可以设置自动测试并发数
- 用户可以设置单节点测试超时时间
- 系统根据测试间隔定时批量测试所有节点
- 如果测试到节点可以建立 OpenVPN 连接，需要顺便访问 `https://my.ippure.com/v1/info` 获取出口 IP 风控信息
- 测试结果需要保存到状态文件或数据库
- Web 管理端需要显示上次测试时间和下次测试时间
- Web 管理端需要显示正在测试、测试完成、测试失败等状态
- 自动测试不应影响当前已连接的 OpenVPN 节点
- 如果当前连接节点测试失败，系统只提示，不自动断开

推荐配置项：

```text
auto_test_enabled=true
auto_test_interval_minutes=60
auto_test_concurrency=20
auto_test_timeout_seconds=5
last_test_at=2026-06-07T15:30:00+08:00
next_test_at=2026-06-07T16:30:00+08:00
```

建议第一版限制为：

```text
最小间隔：10 分钟
默认间隔：60 分钟
最大间隔：1440 分钟
默认并发数：20
最大并发数：100
默认超时：5 秒
最大超时：30 秒
```

自动测试结果至少需要记录：

- 测试时间
- 测试状态
- 实测 TCP 延迟
- 是否连通
- 失败原因
- 使用的 remote 地址
- 使用的 remote 端口
- 出口 IP
- ASN
- ASN 所属组织
- 国家/地区
- 城市
- 时区
- 经纬度
- 邮政编码
- 欺诈评分
- 是否住宅 IP
- 是否广播地址

如果节点数量较多，自动测试需要做并发控制，避免瞬间创建过多连接。

### 2.11 出口 IP 风控信息

节点连通性测试时，如果节点已经完成 OpenVPN 连接，需要通过该节点出口访问：

```text
https://my.ippure.com/v1/info
```

该接口用于检测当前出口 IP 的网络属性和风险信息。

返回示例：

```json
{
  "ip": "43.199.45.120",
  "asn": 16509,
  "asOrganization": "Amazon.com, Inc.",
  "country": "Hong Kong SAR China",
  "countryCode": "HK",
  "city": "Hong Kong",
  "timezone": "Asia/Hong_Kong",
  "longitude": "114.17469",
  "latitude": "22.27832",
  "postalCode": "999077",
  "fraudScore": 38,
  "isResidential": false,
  "isBroadcast": true,
  "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
}
```

字段含义：

- `ip`：当前节点的出口 IP 地址
- `asn`：自治系统号，用于识别该 IP 所属的大型网络
- `asOrganization`：该 IP 所属网络组织，例如云厂商、运营商或数据中心
- `country`：国家或地区名称
- `countryCode`：国家或地区代码
- `city`：城市
- `timezone`：时区
- `longitude`：经度
- `latitude`：纬度
- `postalCode`：邮政编码
- `fraudScore`：欺诈评分，通常分数越高风险越高
- `isResidential`：是否为住宅 IP
- `isBroadcast`：是否为广播地址
- `userAgent`：接口检测到的请求 User-Agent

Web 管理端需要把这些字段展示在节点详情和节点列表中。

节点列表建议展示核心字段：

- 出口 IP
- 国家/地区
- 城市
- ASN 组织
- 欺诈评分
- 是否住宅 IP
- 是否广播地址

节点详情页展示完整字段。

欺诈评分建议用不同状态展示：

```text
0-30：低风险
31-60：中风险
61-100：高风险
```

具体阈值可以后续根据实际使用效果调整。

如果 `https://my.ippure.com/v1/info` 请求失败，需要记录失败原因，但不应把节点直接判定为 OpenVPN 不可用。因为这类失败可能是接口超时、接口不可达或临时网络问题。

### 2.12 当前连接节点失效自动切换

系统需要支持当前已连接节点失效后的自动切换策略。

典型场景：

```text
当前连接节点：日本节点
用户设置：如果当前节点失效，自动切换到日本住宅 IP 节点
结果：系统检测到当前节点失效后，从可用节点中选择符合条件的日本住宅 IP 节点并自动连接
```

自动切换逻辑：

- 用户可以在 Web 管理端开启或关闭自动切换
- 用户可以设置自动切换目标国家/地区
- 用户可以选择目标国家/地区是否跟随当前连接节点
- 用户可以设置是否必须为住宅 IP
- 用户可以设置最大欺诈评分
- 用户可以设置最小速度、最大延迟等筛选条件
- 用户可以设置候选节点排序策略
- 系统需要周期性检查当前连接节点健康状态
- 当前节点确认失效后，系统从最近测试结果中筛选候选节点
- 系统自动断开当前失效节点并连接新的候选节点
- 切换完成后，原 SOCKS 端口应继续可用
- 如果没有符合条件的候选节点，系统应保持断开状态并在 Web 管理端提示

推荐配置项：

```text
failover_enabled=true
failover_country_mode=same_as_current
failover_country_code=JP
failover_require_residential=true
failover_max_fraud_score=60
failover_sort_by=latency_then_fraud_score
failover_health_check_interval_seconds=30
failover_failure_threshold=3
```

字段说明：

- `failover_enabled`：是否启用当前节点失效自动切换
- `failover_country_mode`：目标国家策略，可选 `same_as_current` 或 `fixed`
- `failover_country_code`：固定目标国家/地区代码，例如 `JP`
- `failover_require_residential`：是否只选择住宅 IP 节点
- `failover_max_fraud_score`：允许的最大欺诈评分
- `failover_sort_by`：候选节点排序策略
- `failover_health_check_interval_seconds`：当前连接健康检查间隔
- `failover_failure_threshold`：连续失败多少次后触发自动切换

候选节点筛选条件建议包括：

- 节点必须处于可用状态
- 节点最近一次 OpenVPN 测试成功
- 节点最近一次 SOCKS 出口测试成功
- 节点国家/地区符合配置
- 如果要求住宅 IP，则 `isResidential` 必须为 `true`
- 如果设置最大欺诈评分，则 `fraudScore` 必须小于等于配置值
- 候选节点不能是当前已失效节点

候选节点排序策略建议支持：

```text
latency_then_fraud_score     # 优先低延迟，再看低欺诈评分
fraud_score_then_latency     # 优先低欺诈评分，再看低延迟
speed_then_latency           # 优先高速度，再看低延迟
latest_success               # 优先最近测试成功的节点
```

自动切换需要有防抖策略，避免频繁切换。

建议规则：

- 当前连接连续失败达到阈值后才触发切换
- 每次自动切换后进入冷却时间
- 冷却时间内不再次自动切换
- 切换失败时记录失败原因
- 多次切换失败后暂停自动切换，等待用户手动处理

自动切换成功后，Web 管理端需要显示：

- 原节点
- 新节点
- 切换原因
- 切换时间
- 新节点出口 IP
- 新节点欺诈评分
- 新节点是否住宅 IP

## 3. 推荐运行环境

目标运行环境建议为：

- Ubuntu 或 Debian
- Python 3.10+
- OpenVPN 客户端
- root 权限或 sudo 权限
- `/dev/net/tun` 可用
- 支持 Linux network namespace

需要安装的系统组件可能包括：

```bash
sudo apt update
sudo apt install openvpn iproute2 iptables curl
```

SOCKS 服务可以后续选择以下方案之一：

- `microsocks`
- `3proxy`
- `dante-server`
- 自己用 Python 实现简单 SOCKS5 服务
- Docker 容器内运行 OpenVPN + SOCKS 服务

## 4. 系统模块划分

建议拆成以下模块：

```text
api/
  get_csv.py              # 现有 CSV 获取脚本

vpn_manager/
  csv_loader.py           # 读取和解析 vpngate.csv
  node_model.py           # 节点数据结构
  ovpn.py                 # 解码 Base64，生成 .ovpn 文件，解析 remote
  tester.py               # 批量测试节点
  ippure.py               # 调用 my.ippure.com 获取出口 IP 风控信息
  openvpn_runner.py       # 启动/停止 OpenVPN
  namespace.py            # 创建/销毁 Linux network namespace
  socks_runner.py         # 启动/停止 SOCKS 服务
  state.py                # 保存节点测试结果和连接状态
  scheduler.py            # 后台定时任务，例如自动刷新节点
  settings.py             # 系统配置，例如刷新间隔、默认 SOCKS 端口
  cli.py                  # 命令行入口

web/
  app.py                  # Web 服务入口
  api.py                  # Web API 路由
  auth.py                 # 登录认证、会话校验、退出登录
  schemas.py              # 请求/响应数据结构
  templates/              # HTML 模板，如果使用服务端渲染
  static/                 # 前端 JS/CSS/图片资源
  frontend/               # 如果使用 React/Vue 等前端工程
```

Web 管理端可以先使用 FastAPI + 简单前端页面实现。后续如果交互变复杂，再升级为 React/Vue 单页应用。

## 5. 基础命令设计

初期可以同时保留命令行工具和 Web 管理端。命令行用于调试和自动化，Web 管理端用于日常操作。

示例命令：

```bash
python -m vpn_manager.cli refresh
```

作用：调用 `api/get_csv.py`，刷新 `api/vpngate.csv`。

```bash
python -m vpn_manager.cli list
```

作用：列出 CSV 中的节点。

```bash
python -m vpn_manager.cli test --limit 100 --country JP
```

作用：批量测试前 100 个日本节点。

```bash
python -m vpn_manager.cli connect <node_id> --socks-port 1080
```

作用：连接指定节点，并在本地暴露 SOCKS 端口。

```bash
python -m vpn_manager.cli status
```

作用：查看当前连接状态。

```bash
python -m vpn_manager.cli disconnect
```

作用：断开当前连接并清理相关进程、路由和 namespace。

```bash
python -m web.app
```

作用：启动 Web 管理端。

默认访问地址：

```text
http://127.0.0.1:8000
```

## 6. Web API 设计

Web 管理端通过 HTTP API 调用后端能力。

建议 API 如下：

```text
POST /api/auth/login
```

作用：提交用户名和密码，登录成功后创建会话。

请求参数示例：

```json
{
  "username": "admin",
  "password": "your-password"
}
```

```text
POST /api/auth/logout
```

作用：退出登录并清理当前会话。

```text
GET  /api/auth/me
```

作用：获取当前登录用户信息。如果未登录，返回未授权。

```text
GET  /api/status
```

作用：获取系统当前状态，包括当前连接、SOCKS 端口、测试任务状态和节点统计。需要登录。

响应中需要包含自动刷新和自动测试状态：

```json
{
  "auto_refresh_enabled": true,
  "auto_refresh_interval_minutes": 30,
  "last_refresh_at": "2026-06-07T15:30:00+08:00",
  "next_refresh_at": "2026-06-07T16:00:00+08:00",
  "auto_test_enabled": true,
  "auto_test_interval_minutes": 60,
  "auto_test_concurrency": 20,
  "auto_test_timeout_seconds": 5,
  "last_test_at": "2026-06-07T15:30:00+08:00",
  "next_test_at": "2026-06-07T16:30:00+08:00",
  "failover_enabled": true,
  "failover_country_mode": "same_as_current",
  "failover_country_code": "JP",
  "failover_require_residential": true,
  "failover_max_fraud_score": 60,
  "failover_sort_by": "latency_then_fraud_score",
  "failover_last_switch_at": null
}
```

```text
POST /api/refresh
```

作用：调用 `api/get_csv.py` 刷新 VPNGate CSV。需要登录。

手动刷新成功后，需要更新 `last_refresh_at` 和 `next_refresh_at`。

```text
GET  /api/nodes
```

作用：获取节点列表，支持国家、可用状态、排序、分页等查询参数。需要登录。

```text
GET  /api/nodes/{node_id}
```

作用：获取指定节点详情。需要登录。

节点详情需要包含最近一次 `https://my.ippure.com/v1/info` 检测结果。

```text
POST /api/test
```

作用：启动批量节点测试。需要登录。

该接口用于手动测试。手动测试和自动测试应共用同一套测试逻辑，但需要区分任务来源。

当测试方式包含 OpenVPN 连接测试时，需要顺便执行出口 IP 风控检测。

```text
GET  /api/test/status
```

作用：获取当前测试任务进度。需要登录。

进度信息需要区分：

- 手动测试任务
- 自动测试任务

```text
POST /api/connect
```

作用：连接指定节点。需要登录。

请求参数示例：

```json
{
  "node_id": "public-vpn-192",
  "socks_port": 1080,
  "failover_enabled": true,
  "failover_country_mode": "same_as_current",
  "failover_require_residential": true,
  "failover_max_fraud_score": 60
}
```

连接请求可以临时覆盖全局自动切换策略。如果不传这些字段，则使用系统设置中的默认自动切换配置。

```text
POST /api/disconnect
```

作用：断开当前连接。需要登录。

```text
GET  /api/logs
```

作用：获取系统日志、OpenVPN 日志和 SOCKS 日志。需要登录。

```text
GET  /api/egress-ip
```

作用：通过 SOCKS5 出口检测当前出口 IP。需要登录。

```text
GET  /api/egress-info
```

作用：通过当前 SOCKS5 出口访问 `https://my.ippure.com/v1/info`，获取当前连接节点的出口 IP 风控信息。需要登录。

```text
GET  /api/settings
```

作用：获取系统配置，包括默认 SOCKS 端口、默认测试并发数、节点自动刷新开关、刷新间隔、下次刷新时间等。需要登录。

```text
PUT  /api/settings
```

作用：更新系统配置。需要登录。

请求参数示例：

```json
{
  "default_socks_port": 1080,
  "default_test_concurrency": 20,
  "auto_refresh_enabled": true,
  "auto_refresh_interval_minutes": 30,
  "auto_test_enabled": true,
  "auto_test_interval_minutes": 60,
  "auto_test_concurrency": 20,
  "auto_test_timeout_seconds": 5,
  "failover_enabled": true,
  "failover_country_mode": "same_as_current",
  "failover_country_code": "JP",
  "failover_require_residential": true,
  "failover_max_fraud_score": 60,
  "failover_sort_by": "latency_then_fraud_score",
  "failover_health_check_interval_seconds": 30,
  "failover_failure_threshold": 3
}
```

更新自动刷新配置后，后端需要重新计算 `next_refresh_at`。

更新自动测试配置后，后端需要重新计算 `next_test_at`。

更新自动切换配置后，后端需要立即应用到当前连接的健康检查任务。

```text
GET  /api/failover/candidates
```

作用：根据当前自动切换配置返回候选节点列表。需要登录。

```text
POST /api/failover/switch
```

作用：手动触发一次按当前策略切换节点。需要登录。

该接口用于测试自动切换策略是否能找到合适候选节点。

## 7. Web 管理端交互流程

典型 Web 操作流程：

```text
1. 打开 http://127.0.0.1:8000
2. 进入登录页面
3. 输入管理员用户名和密码
4. 登录成功后进入仪表盘
5. 仪表盘显示上次刷新时间和下次刷新时间
6. 用户可以点击“刷新节点”立即刷新
7. 仪表盘显示上次测试时间和下次测试时间
8. 用户可以点击“测试节点”立即测试
9. 用户可以在设置页调整自动刷新间隔
10. 用户可以在设置页调整自动测试间隔、并发数和超时时间
11. 用户可以在设置页启用当前节点失效自动切换
12. 用户可以设置自动切换目标，例如“当前国家/地区 + 住宅 IP + 欺诈评分小于 60”
13. 系统按配置定时调用 api/get_csv.py 获取最新 vpngate.csv
14. 系统按配置定时批量测试所有节点连通性
15. 节点完成 OpenVPN 测试后，系统通过该节点出口访问 https://my.ippure.com/v1/info
16. 页面展示节点列表、最新测试结果和 IP 风控信息
17. 用户设置国家/数量/并发数
18. 点击“开始测试”
19. 页面实时展示测试进度和风控检测进度
20. 用户从可用节点中选择一个节点
21. 点击“连接”
22. 系统启动 OpenVPN 和 SOCKS 服务
23. 页面显示 socks5://127.0.0.1:1080
24. 用户把该 SOCKS5 地址配置到浏览器或程序中
25. 用户可以在页面中查看出口 IP、欺诈评分和日志
26. 如果当前节点失效，系统按自动切换策略选择新的候选节点
27. 自动切换成功后，SOCKS 端口保持不变，Web 页面显示新节点信息
28. 用户点击“断开”清理连接
29. 用户可以点击“退出登录”结束管理会话
```

Web 管理端需要清楚区分以下状态：

- 未登录
- 未加载节点
- 节点已加载
- 等待下次自动刷新
- 正在自动刷新节点
- 自动刷新失败
- 等待下次自动测试
- 正在自动测试节点
- 自动测试失败
- 正在检测出口 IP 风控信息
- 出口 IP 风控检测失败
- 等待当前连接健康检查
- 当前连接健康检查失败
- 正在自动切换节点
- 自动切换成功
- 自动切换失败
- 正在测试
- 测试完成
- 正在连接
- 已连接
- 连接失败
- 正在断开
- 已断开

## 8. 连接后的本地使用方式

当用户手动连接某个节点后，本地程序可以通过 SOCKS5 代理使用该节点作为出口：

```text
SOCKS5 地址：127.0.0.1
SOCKS5 端口：1080
```

示例：

```bash
curl --socks5 127.0.0.1:1080 https://api.ipify.org
```

浏览器、爬虫程序、HTTP 客户端也可以配置使用这个 SOCKS5 地址。

## 9. 关键技术约束

### 9.1 OpenVPN 不等于 SOCKS

OpenVPN 是 VPN 隧道工具，不是 SOCKS 代理。

要实现 SOCKS 出口，需要额外运行 SOCKS 服务，并让 SOCKS 服务所在环境的默认路由走 OpenVPN。

### 9.2 多节点并发需要隔离

如果未来希望同时连接多个 VPN 节点，并分别暴露多个 SOCKS 端口，例如：

```text
127.0.0.1:1080 -> 日本节点
127.0.0.1:1081 -> 韩国节点
127.0.0.1:1082 -> 美国节点
```

就不能让所有 OpenVPN 进程直接修改主机默认路由。

推荐使用：

- Linux network namespace
- Docker 容器
- 独立路由表

其中 network namespace 是更适合本项目的方案。

### 9.3 需要权限

OpenVPN 和 network namespace 通常需要 root 权限。

涉及的操作包括：

- 创建 TUN 设备
- 修改路由
- 创建 namespace
- 配置 iptables/NAT
- 启动 OpenVPN

### 9.4 节点稳定性不可控

VPNGate 节点是公开志愿节点，稳定性、速度、在线时间都不可控。

系统需要考虑：

- 节点连接失败
- 节点短时间掉线
- 节点速度很慢
- 节点出口 IP 变化
- 节点配置过期

### 9.5 自动刷新不能影响当前连接

自动刷新节点列表只更新 CSV 和节点缓存，不应直接断开当前 VPN 连接。

如果当前连接的节点在新 CSV 中消失，系统应继续保持当前连接，同时在 Web 管理端提示：

```text
当前连接节点不在最新节点列表中
```

用户可以选择继续使用当前连接，或者手动切换到新的可用节点。

### 9.6 自动测试不能影响当前连接

自动测试节点连通性只更新节点健康状态，不应直接断开当前 VPN 连接。

如果当前连接节点在自动测试中失败，系统应继续保持当前连接，同时在 Web 管理端提示：

```text
当前连接节点最近一次连通性测试失败
```

是否断开或切换节点由用户手动决定。

### 9.7 IP 风控检测不能替代连通性判断

`https://my.ippure.com/v1/info` 用于检测出口 IP 属性和风险信息。

如果该接口请求失败，不代表 OpenVPN 节点一定不可用。系统应把这类失败记录为：

```text
风控检测失败
```

而不是直接覆盖节点的 OpenVPN 连通性状态。

节点最终展示时应区分：

- OpenVPN 连通性状态
- SOCKS 出口状态
- IP 风控检测状态
- 欺诈评分

### 9.8 自动切换需要明确触发条件

当前连接节点失效自动切换属于系统级操作，会断开旧节点并连接新节点。

系统不能因为一次偶发请求失败就立即切换节点。建议满足以下条件后才触发：

- OpenVPN 进程已退出，或
- SOCKS 出口连续检测失败，或
- 当前连接连续健康检查失败达到阈值，或
- 当前节点已经无法通过 SOCKS 访问外部测试接口

自动切换时需要记录：

- 触发原因
- 原节点信息
- 候选节点筛选条件
- 候选节点列表
- 最终选择的新节点
- 切换是否成功
- 切换耗时
- 失败原因

如果用户设置“日本住宅 IP 节点”，候选节点必须同时满足：

- `countryCode = JP`
- `isResidential = true`
- 最近一次 OpenVPN 测试成功
- 最近一次 SOCKS 出口测试成功
- 欺诈评分不超过设置阈值

如果没有符合条件的候选节点，系统不应随便切换到其他国家或非住宅 IP 节点，除非用户明确开启降级策略。

### 9.9 Web 管理端安全边界

Web 管理端会触发 OpenVPN、namespace、路由、SOCKS 进程等系统级操作。

Web 管理端必须提供登录认证。第一版建议只监听本地地址：

```text
127.0.0.1
```

不要默认监听：

```text
0.0.0.0
```

如果必须远程访问，需要增加：

- 强密码
- HTTPS
- 访问 IP 白名单
- 操作审计日志
- CSRF 防护

## 10. 第一阶段实现范围

第一阶段建议实现最小可用版本：

1. 调用 `api/get_csv.py` 刷新 CSV
2. 读取并解析 `api/vpngate.csv`
3. 从 Base64 中解码 `.ovpn` 配置
4. 提取 OpenVPN `remote` 地址和端口
5. 批量 TCP 测试节点
6. 保存测试结果
7. 支持手动导出某个节点的 `.ovpn` 文件
8. 支持手动启动 OpenVPN 连接
9. 提供基础 Web 管理端
10. 提供 Web 登录页面
11. Web API 需要登录后访问
12. 支持配置节点自动刷新间隔
13. 支持显示上次刷新时间和下次刷新时间
14. 支持配置节点自动测试间隔
15. 支持显示上次测试时间和下次测试时间
16. 支持节点出口 IP 风控信息展示
17. 支持配置当前节点失效自动切换策略
18. Web 页面支持刷新、列表、测试、连接、断开

这一阶段先不强制实现 SOCKS，只验证节点解析、测试和连接链路。

## 11. 第二阶段实现范围

第二阶段实现本地 SOCKS 出口：

1. 创建 Linux network namespace
2. 在 namespace 中启动 OpenVPN
3. 在 namespace 中启动 SOCKS 服务
4. 把主机本地端口转发到 namespace 内 SOCKS 端口
5. 通过 `curl --socks5` 验证出口 IP
6. 断开时清理 OpenVPN、SOCKS、namespace、临时文件
7. Web 页面显示 SOCKS 服务状态和出口 IP
8. Web 页面显示 OpenVPN 连接日志
9. 后台自动刷新失败时在 Web 页面提示
10. 后台自动测试失败时在 Web 页面提示
11. Web 页面显示每个节点的欺诈评分、ASN、住宅 IP 等风控信息
12. 当前连接节点失效时按策略自动切换候选节点
13. 自动切换后保持原 SOCKS 端口继续可用

## 12. 第三阶段实现范围

第三阶段可以增强体验：

1. 节点搜索和过滤增强
2. 实时连接日志
3. 多节点同时连接
4. 每个节点对应独立 SOCKS 端口
5. 自动重连
6. 节点健康检查
7. 出口 IP 检测增强
8. IP 风控历史记录
9. 连接历史记录
10. 自动切换历史记录
11. 自动切换降级策略
12. 多用户和角色权限
13. WebSocket 实时状态推送

## 13. 最终效果

最终系统希望达到的效果是：

```text
1. 自动获取 VPNGate 节点
2. 自动筛选出可用节点
3. Web 管理端展示可用节点
4. 用户登录 Web 管理端
5. 用户手动选择一个节点
6. 系统自动连接 OpenVPN
7. 本地生成 SOCKS5 端口
8. Web 管理端显示连接状态、出口 IP 和欺诈评分
9. 当前节点失效时，系统按配置自动切换到指定类型节点
10. 其他程序通过 SOCKS5 端口使用该 VPN 节点作为出口
```

典型使用方式：

```bash
python -m vpn_manager.cli refresh
python -m vpn_manager.cli test --limit 100
python -m vpn_manager.cli list --available
python -m vpn_manager.cli connect public-vpn-192 --socks-port 1080
curl --socks5 127.0.0.1:1080 https://api.ipify.org
python -m vpn_manager.cli disconnect
```

Web 使用方式：

```bash
python -m web.app
```

然后访问：

```text
http://127.0.0.1:8000
```
