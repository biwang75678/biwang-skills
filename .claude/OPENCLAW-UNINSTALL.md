# OpenClaw 完整卸载指南

## 1) 快速卸载（官方命令）

```bash
# 先停止 gateway
openclaw gateway stop

# 一键卸载（清理服务、数据目录、工作空间）
openclaw uninstall --all --yes --non-interactive

# 卸载 npm 全局包
npm rm -g openclaw
```

## 2) 手动卸载步骤

如果官方命令不可用，按以下步骤手动清理：

### 停止并移除 systemd 服务

```bash
openclaw gateway stop
# 或手动：
systemctl --user disable --now openclaw-gateway.service
rm -f ~/.config/systemd/user/openclaw-gateway.service
rm -f ~/.config/systemd/user/openclaw-gateway.service.bak
systemctl --user daemon-reload
```

### 卸载 CLI

```bash
npm rm -g openclaw
# 或 pnpm remove -g openclaw / bun remove -g openclaw / brew uninstall openclaw
```

### 清理目录和文件

| 路径 | 说明 |
|------|------|
| `~/.openclaw/` | 主状态目录（配置、凭证、extensions、workspace 等） |
| `~/openclaw-workspaces/` | agent 工作空间 |
| `/tmp/openclaw/` | 运行日志 |
| `~/.config/systemd/user/openclaw-gateway.service` | Linux systemd 服务文件 |

历史遗留目录（如有）：
- `~/.clawdbot`
- `~/.moltbot`
- `~/.molthub`
- `~/.config/openclaw`
- `~/.local/share/openclaw`

```bash
rm -rf ~/.openclaw /tmp/openclaw ~/openclaw-workspaces
rm -rf ~/.clawdbot ~/.moltbot ~/.molthub
rm -rf ~/.config/openclaw ~/.local/share/openclaw
```

## 3) 验证卸载

```bash
which openclaw                                      # 应无输出
ps aux | grep openclaw | grep -v grep               # 应无进程
ls ~/.openclaw 2>/dev/null                           # 应报 No such file
systemctl --user list-units | grep openclaw          # 应无结果
lsof -ti:18789 2>/dev/null                           # 默认端口应无占用
```

## 4) 撤销外部 OAuth 授权

本地卸载不会自动撤销第三方平台的授权，需手动处理：

- **GitHub**: Settings > Applications
- **飞书**: 管理后台 > 应用管理
- **Google**: myaccount.google.com/permissions
- **Slack**: slack.com/apps/manage

## 5) 清理环境变量

检查 `~/.bashrc`、`~/.zshrc` 等文件，移除以下变量（如有）：

- `OPENCLAW_CONFIG_PATH`
- `OPENCLAW_STATE_DIR`
- `OPENCLAW_PROFILE`
- `OPENCLAW_GATEWAY_PORT`

## 6) 注意事项

- 卸载前建议先执行 `openclaw backup create` 备份数据
- 如果使用了 `--profile` 参数，需额外清理 `~/.openclaw-<profile>/` 目录
- Gateway 默认端口为 18789，绑定 127.0.0.1（仅本地访问）
- 启动 gateway 时必须 `cd ~`，避免在 `/tmp/` 等临时目录下启动导致 ENOENT 崩溃
