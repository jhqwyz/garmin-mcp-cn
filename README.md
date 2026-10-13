# Garmin MCP China — ChatGPT 网页端与桌面端

本项目基于 [BorisBW/garmin-mcp-cn](https://github.com/BorisBW/garmin-mcp-cn)，原始上游为 [Taxuspt/garmin_mcp](https://github.com/Taxuspt/garmin_mcp)。保留 MIT 许可证。

此版本面向个人健康与运动数据分析，默认只开放 79 个经过审阅的读取工具。写入、删除、上传、安排训练和重新加载数据的工具不对 MCP 客户端开放。

## 本次更新

- 升级到 `garminconnect==0.3.17`，使用其原生认证，完全移除 Garth。
- 首次登录和凭证复用都明确选择中国区；默认中国区凭证目录是 `~/.garminconnect-cn`。
- 登录凭证采用 `garmin_tokens.json`。旧 `oauth1_token.json` / `oauth2_token.json` 无法转换，需要重新登录。
- 使用 MCP SDK 1.x 的 Streamable HTTP 支持；保留 STDIO。HTTP 仅绑定本机回环地址。
- 支持 OpenAI 官方 Secure MCP Tunnel，让 ChatGPT 网页端调用本机服务。
- 修正压力汇总丢弃有效 0 值的问题；睡眠阶段缺失时保留其余有效指标。
- 更新 Garmin Coach 训练详情查询，消除对旧 `garmin.garth` 接口的调用。

## ChatGPT 网页端推荐路径

ChatGPT → OpenAI Secure MCP Tunnel → 本机 tunnel-client → 本机 Garmin MCP → 佳明中国。

需要三个独立条件：

1. 佳明中国账号在本机完成一次认证；可能需要输入验证码。
2. OpenAI Platform 中创建关联当前 ChatGPT 工作区的 MCP Tunnel，并有运行它的 API key。运行密钥需要 Tunnels Read + Use 权限；管理隧道需要 Read + Manage。
3. ChatGPT 当前账号允许添加自定义 MCP 服务。在 Plugins 页面选择 Add custom MCP server，Connection 选择 Tunnel，并安装产生的私有插件。

参考：[OpenAI Secure MCP Tunnel 官方说明](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)、[ChatGPT 自定义 MCP 接入说明](https://developers.openai.com/plugins/deploy/connect-chatgpt)。

运行服务的电脑需要保持开机联网，隧道进程需要持续运行。本项目不会自动导入全部历史数据，也不包含定时报告。

### Mac 安装

需要 Git；安装脚本会在缺少 uv 时从其官方来源安装 uv，并由 uv 准备 Python 3.12。

```bash
git clone https://github.com/jhqwyz/garmin-mcp-cn.git
cd garmin-mcp-cn
bash install_mac.command
```

安装程序会：安装锁定的依赖 → 下载并校验 OpenAI 官方 tunnel-client → 在终端完成佳明中国认证 → 接收 Tunnel ID → 隐藏输入 OpenAI 运行密钥 → 检查并运行隧道。

佳明密码和验证码不保存到项目配置，不发给 ChatGPT。OpenAI 运行密钥只通过子进程环境传递，不写入启动参数、项目文件或隧道配置。需要分析的佳明查询结果会经隧道发送到 OpenAI。

创建隧道与运行密钥：

- [Platform 隧道管理](https://platform.openai.com/settings/organization/tunnels)
- [Platform 运行 API key](https://platform.openai.com/settings/organization/api-keys)

隧道创建后，确保它关联当前 ChatGPT 工作区。保持安装终端运行，在 [ChatGPT Plugins](https://chatgpt.com/plugins) 中添加自定义 MCP，选择 Tunnel，填入同一个 Tunnel ID，然后创建并安装插件。

之后重新启动已配置的隧道：

```bash
bash start_web.command
```

每次启动时可在终端隐藏输入运行密钥。密钥不会持久保存。

### 分步安装 / Linux

```bash
uv sync --locked --no-dev
uv run --no-dev python scripts/install_tunnel_client.py
uv run --no-dev garmin-mcp-auth --china
uv run --no-dev garmin-mcp-web setup --china --tunnel-id YOUR_TUNNEL_ID --tunnel-client "$PWD/.bin/tunnel-client"
```

单独检查已配置的隧道：

```bash
uv run --no-dev garmin-mcp-web doctor --china --tunnel-client "$PWD/.bin/tunnel-client"
```

官方安装器按当前操作系统与架构选择 `openai/tunnel-client` 的最新正式发行，校验 GitHub 提供的 SHA-256 后，只解压该二进制文件。

## 本地 MCP 客户端

先认证，再把以下命令配置为 STDIO 服务：

```bash
uv run --locked --no-dev garmin-mcp-auth --china
uv run --locked --no-dev garmin-mcp --china
```

本地 Streamable HTTP 测试：

```bash
uv run --locked --no-dev garmin-mcp --china --transport streamable-http --port 8000
```

地址是 `http://127.0.0.1:8000/mcp`。该地址仅在本机可访问。ChatGPT 网页端使用隧道连接，不直接连接 localhost。

## 认证与凭证

- 全球区：`garmin-mcp-auth --global` 和 `garmin-mcp --global`；全球区默认凭证目录为 `~/.garminconnect`。
- 自定义凭证目录：使用 `--token-path` 或 `GARMINTOKENS`。
- 验证现有凭证：`garmin-mcp-auth --china --verify`。
- 重新认证：`garmin-mcp-auth --china --force-reauth`。新认证失败时保留原凭证。
- 新版上游会自动刷新令牌。只有刷新凭证到期或被撤销等情况才需要重新登录。
- 不要把凭证文件提交到 Git。凭证文件权限由上游限定为仅当前用户可读写。

兼容 `GARMIN_EMAIL` / `GARMIN_PASSWORD` 及对应 `_FILE` 输入，但日常使用建议在终端完成交互认证，服务端仅复用凭证。

## 数据与分析边界

可读取活动、睡眠、心率、HRV、压力、身体电量、体重、训练状态等已有记录。哪些指标可用取决于设备与账号。

缺失数据和请求失败均表示不可用，不能作为零值。分析睡眠时间时优先使用 GMT 字段，再转换到 Asia/Shanghai，避免部分中国区账号本地时间字段重复偏移的问题。

## 验证

默认验证不需要真实账号，也不修改佳明数据：

```bash
uv sync --locked
uv run --locked pytest tests/unit tests/integration -q
```

测试覆盖中国区凭证复用、重新认证失败时保留原凭证、只读工具实际拒绝写入、压力 0 值统计、STDIO / Streamable HTTP 协议以及隧道密钥处理。

真实账号验证需要用户在本机完成：首次认证、读取睡眠、重启服务复用凭证、后续自动刷新。不将模拟测试描述为真实账号连通性验证。
