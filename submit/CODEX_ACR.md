# Codex ACR 并行构建方案

目标：在不影响 Cursor 当前 `release-v0.1-<track>` 发布体系的前提下，为 Codex 建立独立 ACR 仓库和独立触发 tag。

## 结论

不建议把 Codex 代码放到 GitHub 子目录作为 ACR 构建入口。现有 Dockerfile、`submit/main.py`、`Project/`、`submit/tracks/` 都以仓库根目录为构建上下文。

推荐：

```text
同一个 GitHub 仓库: new8341/danbaizhi
同一个目录结构: /
Cursor 使用 release-v0.1-<track>
Codex 使用 codex-v0.1-<track>
Cursor ACR 仓库: <track>:0.1
Codex ACR 仓库: codex-<track>:0.1
```

## 阿里云 ACR 仓库配置

公共配置：

| 项 | 值 |
|---|---|
| 地域 | 华东2（上海） |
| 命名空间 | `ai4s-lee` |
| 仓库类型 | 私有 |
| 代码仓库 | `https://github.com/new8341/danbaizhi` |
| 构建上下文目录 | `/` |
| 代码变更自动构建镜像 | 开启 |
| 海外机器构建 | 开启 |
| 不使用缓存 | 关闭 |

四个 Codex 仓库：

| 赛道 | ACR 仓库名 | Branch/Tag | Dockerfile 文件名 | 镜像版本 |
|---|---|---|---|---|
| DrugClip | `codex-drugclip` | `codex-v0.1-drugclip` | `Dockerfile.drugclip` | `0.1` |
| 靶向分子 | `codex-baxiangfenzi` | `codex-v0.1-baxiangfenzi` | `Dockerfile.baxiangfenzi` | `0.1` |
| 蛋白质构象 | `codex-danbaizhi` | `codex-v0.1-danbaizhi` | `Dockerfile` | `0.1` |
| 神经算子 | `codex-shenjingsuanzi` | `codex-v0.1-shenjingsuanzi` | `Dockerfile.shenjingsuanzi` | `0.1` |

注意：

- Dockerfile 文件名只填文件名，不填 `submit/...`。
- 构建上下文目录保持 `/`。
- Codex tag 不覆盖 Cursor tag。
- Cursor 原仓库和原镜像不变。

## 天池提交镜像地址

```text
crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/codex-drugclip:0.1
crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/codex-baxiangfenzi:0.1
crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/codex-danbaizhi:0.1
crpi-i14uo4x5tmwyoptf.cn-shanghai.personal.cr.aliyuncs.com/ai4s-lee/codex-shenjingsuanzi:0.1
```

用户名仍使用 ACR 用户名。密码为 ACR 固定密码，不得写入仓库。

## Codex tag 发布

只触发 Codex ACR，不改 `submit/track_pins.json`：

```powershell
.\submit\publish_codex_track.ps1 -Track shenjingsuanzi
```

指定 commit：

```powershell
.\submit\publish_codex_track.ps1 -Track shenjingsuanzi -Commit <commit>
```

跳过本地验证：

```powershell
.\submit\publish_codex_track.ps1 -Track shenjingsuanzi -SkipValidation
```

## 与 Cursor 的边界

| 项 | Cursor | Codex |
|---|---|---|
| ACR 仓库 | `<track>` | `codex-<track>` |
| tag | `release-v0.1-<track>` | `codex-v0.1-<track>` |
| 镜像 | `<track>:0.1` | `codex-<track>:0.1` |
| pin 文件 | 修改 `track_pins.json` | 不修改 `track_pins.json` |
| 大赛提交 | 用户手动选择镜像 | 用户手动选择镜像 |

